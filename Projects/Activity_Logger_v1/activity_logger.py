import ctypes
import ctypes.wintypes
import time
import datetime
import csv
import os
import threading
from PIL import ImageGrab
from google import genai

# ==========================================
# 設定項目
# ==========================================
# Gemini APIキー（環境変数 GEMINI_API_KEY から読み込む）
API_KEY = os.environ.get("GEMINI_API_KEY", "")

# 現行の軽量・高速モデルを指定
GEMINI_MODEL = "gemini-2.5-flash"
# ==========================================

# スレッド停止用のイベント（UI連携用）
stop_event = threading.Event()

# Gemini クライアントの初期化
client = genai.Client(api_key=API_KEY)

# Windows APIの設定
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

def get_active_window_info():
    """現在アクティブなウィンドウのプロセス名とタイトルを取得する"""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None, None

    # ウィンドウタイトルの取得
    length = user32.GetWindowTextLengthW(hwnd)
    buff = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buff, length + 1)
    window_title = buff.value

    # プロセスIDの取得
    pid = ctypes.wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

    # プロセス名（exeファイル名）の取得
    process_name = "Unknown"
    try:
        process = kernel32.OpenProcess(0x1000, False, pid.value)
        if process:
            exe_name = ctypes.create_unicode_buffer(260)
            size = ctypes.wintypes.DWORD(260)
            if kernel32.QueryFullProcessImageNameW(process, 0, exe_name, ctypes.byref(size)):
                process_name = os.path.basename(exe_name.value)
            kernel32.CloseHandle(process)
    except Exception:
        pass

    return process_name, window_title

def get_idle_time():
    """最後の入力（マウス・キーボード）からの経過時間（秒）を取得する"""
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.wintypes.UINT),
                    ("dwTime", ctypes.wintypes.DWORD)]
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if user32.GetLastInputInfo(ctypes.byref(lii)):
        millis = kernel32.GetTickCount() - lii.dwTime
        return millis / 1000.0
    return 0.0

def capture_and_analyze(proc_name, window_title):
    """スクリーンショットを取得してGemini APIで解析し、画像を破棄してテキスト解析結果を返す"""
    temp_path = "temp_capture_event.png"
    analysis_text = "解析なし（離席または取得失敗）"

    try:
        # 1. キャプチャ取得
        screenshot = ImageGrab.grab()
        screenshot.save(temp_path)

        # 2. PILで画像を開いてGemini APIへ送信
        image = ImageGrab.Image.open(temp_path)
        prompt = (
            f"アプリ「{proc_name}」（タイトル: 「{window_title}」）が操作されています。\n"
            "添付されたスクリーンショットを分析し、ユーザーが『具体的にどんな作業を行っていたか』を40文字程度の日本語で簡潔に要約してください。\n"
            "※もし、Excel関数で悩んでいる、単純なコピペを繰り返しているなど「非効率な手作業」に見える場合は、要約の先頭に【非効率疑い】と付けてください。"
        )

        # gemini-3.1-flash で高速解析
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[image, prompt]
        )
        analysis_text = response.text.strip()

    except Exception as e:
        analysis_text = f"AI解析エラー: {e}"

    finally:
        # 3. 【容量節約】解析終了後に画像を即時破棄
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return analysis_text

def main(base_dir=None):
    print("【DX推進 AIロガー】起動しました。")
    print("（※終了するには Ctrl+C を押してください）")

    # ログ保存先ディレクトリの作成
    if base_dir:
        log_dir = base_dir
    else:
        log_dir = os.path.join(os.path.dirname(__file__), "activity_logs")
    os.makedirs(log_dir, exist_ok=True)

    print(f"【業務分析用ログ記録ツール (AI解析機能付き)】")
    print(f"使用モデル: {GEMINI_MODEL}")
    print(f"ウィンドウ切り替え時に画面を解析し、滞在時間と作業内容を記録します。")
    print(f"保存先: {log_dir}")
    print("※終了する場合は Ctrl + C を押してください。\n")

    current_status = None
    current_proc = None
    current_title = None
    start_time = datetime.datetime.now()

    pending_logs = []

    while not stop_event.is_set():
        try:
            # 離席判定（300秒 = 5分以上操作がなければ離席とする）
            idle_sec = get_idle_time()
            if idle_sec > 300:
                status = "離席中"
                proc, title = "", ""
            else:
                status = "作業中"
                proc, title = get_active_window_info()
                if proc is None:
                    proc, title = "Unknown", "Unknown"

            # ウィンドウや状態が切り替わったか判定
            if current_status != status or current_proc != proc or current_title != title:
                now = datetime.datetime.now()

                # 初回ループ以外なら、一つ前の状態の滞在時間とAI解析結果を記録
                if current_status is not None:
                    duration = int((now - start_time).total_seconds())

                    # 1秒未満の瞬間的な切り替えはノイズとして無視
                    if duration >= 1:
                        # 作業中の場合のみスクリーンショットを取得してAI解析
                        if current_status == "作業中" and current_proc:
                            print(f"[{now.strftime('%H:%M:%S')}] 画面切り替え検知 ➔ AI解析中 ({current_proc})...")
                            ai_analysis = capture_and_analyze(current_proc, current_title)
                        else:
                            ai_analysis = "離席のため解析なし"

                        log_data = {
                            "date_str": start_time.strftime("%Y%m%d"),
                            "row": [
                                start_time.strftime("%Y/%m/%d %H:%M:%S"),
                                now.strftime("%Y/%m/%d %H:%M:%S"),
                                f"{duration}秒",
                                current_status,
                                current_proc,
                                current_title,
                                ai_analysis
                            ]
                        }
                        pending_logs.append(log_data)
                        print(f" └ [{start_time.strftime('%H:%M:%S')} - {now.strftime('%H:%M:%S')}] {current_proc} ({duration}秒) | AI要約: {ai_analysis}")

                # 現在の状態を更新
                current_status = status
                current_proc = proc
                current_title = title
                start_time = now

            # 未書き込みのログがあれば書き込みを試行する
            if pending_logs:
                new_pending = []
                logs_by_date = {}
                for log in pending_logs:
                    d = log["date_str"]
                    if d not in logs_by_date:
                        logs_by_date[d] = []
                    logs_by_date[d].append(log["row"])

                # CSVに追記
                for d, rows in logs_by_date.items():
                    log_file = os.path.join(log_dir, f"activity_log_{d}.csv")
                    file_exists = os.path.exists(log_file)

                    try:
                        with open(log_file, "a", encoding="utf-8-sig", newline="") as f:
                            writer = csv.writer(f)
                            if not file_exists:
                                writer.writerow(["開始日時", "終了日時", "滞在時間", "状態", "アプリケーション名", "ウィンドウタイトル", "AI作業解析内容"])
                            writer.writerows(rows)
                    except PermissionError:
                        for log in pending_logs:
                            if log["date_str"] == d:
                                new_pending.append(log)

                if len(new_pending) > 0 and len(new_pending) != len(pending_logs):
                    print(f"※CSVファイルが開かれているため、{len(new_pending)}件の書き込みを保留しています...")

                pending_logs = new_pending

            stop_event.wait(1)

        except KeyboardInterrupt:
            print("\n記録を終了しました。")
            break
        except Exception as e:
            print(f"エラーが発生しました: {e}")
            stop_event.wait(5)

if __name__ == "__main__":
    main()