import time
import pyperclip
import threading
import sys
import json
try:
    import win32api
    import win32con
except ImportError:
    pass

from utils.window_api import get_active_window
from storage.db_client import enqueue_data
from config import settings

def start_micro_tracking(log_callback=None):
    last_clipboard = ""
    last_stats_time = time.time()
    last_slow_check = time.time()
    
    key_count = 0
    click_count = 0
    scroll_count = 0
    mouse_distance = 0
    window_switch_count = 0
    right_click_count = 0
    shortcut_count = 0
    shortcut_details = {}
    
    kvm_mode = False
    hotkey_history = []
    
    def check_hotkey(key_code):
        nonlocal kvm_mode, hotkey_history
        now = time.time()
        hotkey_history.append((key_code, now))
        hotkey_history = [k for k in hotkey_history if now - k[1] <= 3.0]
        keys = [k[0] for k in hotkey_history]
        if len(keys) >= 2:
            if keys[-2:] == [win32con.VK_LCONTROL, win32con.VK_LCONTROL] or \
               keys[-2:] == [win32con.VK_RCONTROL, win32con.VK_RCONTROL] or \
               keys[-2:] == [17, 17] or \
               keys[-2:] == [win32con.VK_SCROLL, win32con.VK_SCROLL]:
                kvm_mode = True
                hotkey_history = []
    
    last_app_title = ("", "")
    
    # マウスホイールのスクロールを高精度に検知 (1ロール=1回)
    try:
        from pynput import mouse
        def on_scroll(x, y, dx, dy):
            nonlocal scroll_count
            if dy != 0:
                # dyは通常1または-1 (1クリック分)
                scroll_count += abs(int(dy))
                
        scroll_listener = mouse.Listener(on_scroll=on_scroll)
        scroll_listener.daemon = True
        scroll_listener.start()
        if log_callback:
            log_callback("高精度マウススクロール検知を開始しました")
    except Exception as e:
        if log_callback:
            log_callback(f"スクロール検知の初期化に失敗: {e}")
    # 状態のトラッキング (1〜254キー)
    last_key_states = [False] * 256
    
    try:
        last_mouse_pos = win32api.GetCursorPos()
    except Exception:
        last_mouse_pos = (0, 0)
        
    while True:
        try:
            current_time = time.time()
            
            # --- 50msごとに高速ポーリング (RemoteDesktop環境でも入力を検知するため win32api を使用) ---
            try:
                if 'win32api' in sys.modules:
                    # マウス移動距離の計算
                    current_pos = win32api.GetCursorPos()
                    if current_pos != last_mouse_pos:
                        dx = current_pos[0] - last_mouse_pos[0]
                        dy = current_pos[1] - last_mouse_pos[1]
                        dist = (dx**2 + dy**2) ** 0.5
                        mouse_distance += dist
                        last_mouse_pos = current_pos
                        if dist > 5 and kvm_mode:
                            kvm_mode = False
                    
                    # キー・クリック状態の取得
                    for i in range(1, 255):
                        state = win32api.GetAsyncKeyState(i)
                        is_down = (state & 0x8000) != 0
                        if is_down and not last_key_states[i]:
                            if kvm_mode and i not in (17, 162, 163, 145, 13):
                                kvm_mode = False
                            check_hotkey(i)
                            
                            # 新規に押された瞬間
                            if i == win32con.VK_RBUTTON:
                                right_click_count += 1
                                click_count += 1
                                if kvm_mode: kvm_mode = False
                            elif i in (win32con.VK_LBUTTON, win32con.VK_MBUTTON):
                                click_count += 1
                                if kvm_mode: kvm_mode = False
                            elif i in (win32con.VK_UP, win32con.VK_DOWN, win32con.VK_PRIOR, win32con.VK_NEXT):
                                scroll_count += 1
                            else:
                                key_count += 1
                                ctrl_pressed = (win32api.GetAsyncKeyState(win32con.VK_CONTROL) & 0x8000) != 0
                                if ctrl_pressed and i not in (win32con.VK_CONTROL, win32con.VK_LCONTROL, win32con.VK_RCONTROL):
                                    shortcut_count += 1
                                    key_char = chr(i) if 65 <= i <= 90 else str(i)
                                    name = f"Ctrl+{key_char}"
                                    shortcut_details[name] = shortcut_details.get(name, 0) + 1
                                elif 0x70 <= i <= 0x7B:  # F1 ~ F12
                                    shortcut_count += 1
                                    name = f"F{i - 0x6F}"
                                    shortcut_details[name] = shortcut_details.get(name, 0) + 1
                        last_key_states[i] = is_down
            except Exception:
                pass
                
            # --- 1秒ごとに少し重い処理 (ウィンドウタイトル、クリップボード等) ---
            if current_time - last_slow_check >= 1.0:
                app_name, title = get_active_window()
                
                # アプリ・タブ切り替えの計算
                current_app_title = (app_name, title)
                if last_app_title != ("", "") and current_app_title != last_app_title:
                    window_switch_count += 1
                last_app_title = current_app_title
                
                # クリップボード転記トラッキング
                try:
                    current_clipboard = pyperclip.paste()
                    if current_clipboard != last_clipboard:
                        last_clipboard = current_clipboard
                        snippet = current_clipboard[:100].replace('\n', ' ').replace('\r', ' ')
                        if snippet:
                            payload = {
                                "type": "micro_event",
                                "event": "COPY_PASTE",
                                "app_name": app_name,
                                "file_name": title,
                                "snippet": snippet,
                                "copy_paste_count": 1,
                                "timestamp": current_time
                            }
                            enqueue_data(payload)
                            if log_callback:
                                log_callback(payload)
                except Exception:
                    pass

                # --- 10秒ごとにキー入力・クリック・スクロール数・マウス距離を集計して送信 ---
                if current_time - last_stats_time >= 10.0:
                    if kvm_mode:
                        payload = {
                            "type": "micro_event",
                            "event": "INPUT_STATS",
                            "app_name": "基幹システム(KVM)",
                            "file_name": "基幹PC操作中",
                            "operation_type": "基幹PC操作",
                            "manual_typing_count": 0,
                            "click_count": 1,
                            "scroll_count": 0,
                            "mouse_distance": 0,
                            "window_switch_count": 0,
                            "duration_seconds": 10,
                            "timestamp": current_time
                        }
                        enqueue_data(payload)
                        if log_callback: log_callback(payload)
                    elif key_count > 0 or click_count > 0 or scroll_count > 0 or mouse_distance > 0 or window_switch_count > 0:
                        payload = {
                            "type": "micro_event",
                            "event": "INPUT_STATS",
                            "app_name": app_name,
                            "file_name": title,
                            "manual_typing_count": key_count,
                            "click_count": click_count,
                            "scroll_count": scroll_count,
                            "mouse_distance": int(mouse_distance),
                            "window_switch_count": window_switch_count,
                            "right_click_count": right_click_count,
                            "shortcut_key_count": shortcut_count,
                            "shortcut_details": json.dumps(shortcut_details),
                            "duration_seconds": 10,
                            "timestamp": current_time
                        }
                        enqueue_data(payload)
                        if log_callback:
                            log_callback(payload)
                    
                    # カウンターをリセット
                    key_count = 0
                    click_count = 0
                    scroll_count = 0
                    mouse_distance = 0
                    window_switch_count = 0
                    right_click_count = 0
                    shortcut_count = 0
                    shortcut_details = {}
                    last_stats_time = current_time

                last_slow_check = current_time
                
        except Exception:
            pass
            
        # 50ミリ秒スリープ（負荷をかけずにキーの押し離しを検知）
        time.sleep(0.05)

