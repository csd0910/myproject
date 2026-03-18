import os
import sys
import time
import datetime
import csv
import poplib
import email
from email.header import decode_header
import re
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from pywinauto import Desktop
from pywinauto.keyboard import send_keys as pywinauto_send_keys
import tkinter as tk
import pyperclip

# ==========================================
# 定数・設定値
# ==========================================
# Webログイン情報
WEB_URL = "https://a832-y.sharestage.com/"
WEB_ID = "t_ito"
WEB_PASS = "Forest0720!"

# テスト動作用パラメータ
UPLOAD_FILE_PATH = r"C:\Users\FMV\Desktop\Bizストレージテスト送信ファイル\TEST送信用ファイル.xlsx"
DEST_EMAIL = "t_ito@forest.co.jp"
SENDER_NAME = "伊藤健人"
MAIL_SUBJECT_PREFIX = "[Biz遅延計測自動テスト]"

# POP3（メール受信）設定
POP_SERVER = "c300ls1v.mwprem.net"
POP_PORT = 995
POP_USER = "t_ito"
POP_PASS = "P55GB@q#"

# 動作・ログ設定
LOG_FOLDER_NAME = "BizStorage_Log"
LOG_FILE_NAME = "evidence_log.csv"
LOOP_INTERVAL_MINUTES = 15
START_HOUR = 8
END_HOUR = 19
HISTORY_DELETE_HOURS = 2

# ==========================================
# ユーティリティ関数
# ==========================================
def get_desktop_dir():
    """実行環境のデスクトップパスを取得"""
    return os.path.join(os.path.expanduser("~"), "Desktop")

def get_log_dir():
    """ログおよびダンプ・スクリーンショットの保存先ディレクトリを取得"""
    log_dir = os.path.join(get_desktop_dir(), LOG_FOLDER_NAME)
    os.makedirs(log_dir, exist_ok=True)
    return log_dir

def init_csv_log():
    """CSVログファイルの初期化（存在しなければヘッダー作成）"""
    log_dir = get_log_dir()
    log_path = os.path.join(log_dir, LOG_FILE_NAME)

    if not os.path.exists(log_path):
        with open(log_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["実行日", "送信時刻(T1)", "ヘッダー時刻(T_Hdr)", "受信検知時刻(T2)", "遅延秒数", "結果"])
    return log_path

def write_log(t1, t_hdr, t2, delay_sec, result="SUCCESS"):
    """ログファイルへの追記"""
    log_path = init_csv_log()
    today_str = datetime.date.today().strftime("%Y/%m/%d")
    t1_str = t1.strftime("%H:%M:%S") if t1 else ""
    t_hdr_str = t_hdr.strftime("%H:%M:%S") if t_hdr else ""
    t2_str = t2.strftime("%H:%M:%S") if t2 else ""

    with open(log_path, 'a', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([today_str, t1_str, t_hdr_str, t2_str, delay_sec, result])
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ログを記録しました: {result} (遅延: {delay_sec}秒)")

def print_timestamp(msg):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")

def safe_click(driver, by, value, timeout=10):
    """要素がクリック可能になるまで待ち、クリックする"""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
        element.click()
        return element
    except TimeoutException:
        raise Exception(f"Timeout: クリック待機エラー ({by}={value}) が見つからない・押せる状態になりませんでした")

def safe_send_keys(driver, by, value, text, timeout=10):
    """要素が操作可能になるまで待ち、テキストを入力する"""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        element.clear()
        element.send_keys(text)
        return element
    except TimeoutException:
        raise Exception(f"Timeout: 入力待機エラー ({by}={value}) が見つかりませんでした")

# ==========================================
# メイン処理モジュール
# ==========================================
def execute_web_transmission():
    """SeleniumによるWebブラウザ操作から送信完了時刻を返す"""
    options = Options()
    # 動作を可視化する場合はheadless指定を外す（テスト時は画面表示があったほうが安全）
    # options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    # セキュリティソフト干渉回避のため、いくつかオプションを追加
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])

    driver = webdriver.Edge(options=options)
    t1_time = None
    subject_text = f"{MAIL_SUBJECT_PREFIX} {datetime.datetime.now().strftime('%m%d_%H%M%S')}"

    try:
        # 1. ログイン処理
        print_timestamp("Webサイト(URL)へアクセス中...")
        driver.get(WEB_URL)
        time.sleep(2) # 画面の描画を待機

        print_timestamp("ログインID入力中...")
        safe_send_keys(driver, By.ID, "textfieldLoginId", WEB_ID)

        print_timestamp("パスワード入力中...")
        safe_send_keys(driver, By.XPATH, "/html/body/form[1]/div[1]/div/div[3]/div[1]/table[2]/tbody/tr/td[2]/input", WEB_PASS)

        print_timestamp("ログインボタンクリック...")
        safe_click(driver, By.XPATH, "/html/body/form[1]/div[1]/div/div[3]/div[2]/span/input")

        # ログイン後、エラーメッセージ（ログイン回数上限等）が出ていないかチェック
        time.sleep(3)
        try:
            error_elems = driver.find_elements(By.CLASS_NAME, "UA001_message")
            for elem in error_elems:
                if elem.is_displayed() and elem.text.strip():
                    raise Exception(f"ログインエラーまたは制限: {elem.text.strip()}")
        except Exception as e:
            if "ログインエラーまたは制限" in str(e):
                raise

        # 2. メニュー遷移 (ShareDisk -> ファイル送信)
        print_timestamp("ログイン成功。送信メニューへ移動...")
        time.sleep(2) # 画面遷移の安定化のため適度なスリープ
        safe_click(driver, By.XPATH, "/html/body/form/div[1]/div[1]/div[3]/div[3]/div/ul/li[2]/a") # ShareDisk
        time.sleep(1)
        safe_click(driver, By.XPATH, "/html/body/form/div[2]/div/div[2]/div[1]/div/div/ul/li[1]/a") # ファイル送信

        # 3. ファイル送信フォーム入力
        # ファイル選択（「ファイル選択」ボタンをクリックし、Windowsのキーボード操作を即座にシミュレート）
        print_timestamp("ファイル選択ボタンをクリック...")
        safe_click(driver, By.ID, "uploadFiles")

        # エクスプローラのダイアログが確実に開ききるのを待つ
        time.sleep(3)
        print_timestamp("ファイルアップロードダイアログにパスを貼り付け(ペースト)で確実に入力中...")
        try:
            # クリップボードにパスをコピー
            pyperclip.copy(UPLOAD_FILE_PATH)
            time.sleep(1)

            # Ctrl+V で貼り付け
            pywinauto_send_keys('^v')
            time.sleep(1)

            # Enter を押して確定
            pywinauto_send_keys('{ENTER}')
            time.sleep(3) # 入力ダイアログが閉じてファイルがロードされるのを待機

        except Exception as win_e:
            print_timestamp(f"ファイル選択ダイアログの操作に失敗しました: {win_e}")
            raise Exception("File Upload Dialog Error")


        # 宛先メアドなどの入力フォームはインラインフレーム(iframe)内にあるため切り替える
        driver.switch_to.frame("SEND_CONTENT")

        # 宛先メアド、氏名等
        print_timestamp("宛先等の情報入力中...")
        time.sleep(1.5)
        safe_send_keys(driver, By.NAME, "USER_MAIL", DEST_EMAIL)
        time.sleep(1.5)
        safe_send_keys(driver, By.NAME, "USER_NAME", SENDER_NAME)
        time.sleep(1.5)

        # 「リストへ追加」ボタン
        safe_click(driver, By.XPATH, "//input[@name='Submit2' and not(@id='contentComfirm')]")
        time.sleep(2.5) # リスト追加のJS反映を待機

        # 件名入力
        print_timestamp("件名・本文・パスワード入力中...")
        safe_send_keys(driver, By.NAME, "SD_SUBJECT", subject_text)
        time.sleep(1.5)

        # コメント（本文）入力
        try:
            safe_send_keys(driver, By.XPATH, "//textarea", "遅延計測用の自動送信テストです。", timeout=3)
        except:
            pass
        time.sleep(1.5)

        # パスワード設定 (自動生成ではなく固定パスワードを指定)
        try:
            safe_send_keys(driver, By.NAME, "DL_PASS1", "Test1234@", timeout=3)
        except:
            pass
        time.sleep(2.0)

        # 送信実行 (送信確認 -> 送信実行)
        print_timestamp("送信確認ボタンをクリック...")
        safe_click(driver, By.ID, "contentComfirm")

        # ▼ここから追加・修正：クリック後、画面が切り替わる（またはDOMが再描画される）のを待つ
        print_timestamp("送信確認画面へ遷移中...")
        time.sleep(5.0) # 画面遷移の猶予を少し長めに取る

        # 画面がリロードされた場合、iframeのコンテキストが外れることがあるため再度入り直す
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame("SEND_CONTENT")
        except:
            pass # すでにフレーム内にいるか、フレーム構造が変わっている場合はスキップ

        print_timestamp("最終送信を実行します...")
        time.sleep(1.5)
        try:
            # 汎用的に「送信」または「実行」を含むボタン(idがcontentComfirmではないもの)をクリック
            safe_click(driver, By.XPATH, "//input[contains(@value, '送信') or contains(@value, '実行')][not(@id='contentComfirm')]", timeout=10)
        except Exception as e:
            # それでも見つからない場合の最後のフォールバック(ダンプから推測される一般的なSubmitボタン)
            print_timestamp(f"汎用ロケータで失敗したためフォールバックを使用します: {e}")
            safe_click(driver, By.XPATH, "//input[@type='submit' or @type='button'][not(@id='reset') and not(@id='contentComfirm') and not(@name='setTemplate')]", timeout=5)

        # クリック後、処理が完了するまで待機
        time.sleep(4.0)


        # 送信完了時点をT1とする
        t1_time = datetime.datetime.now()
        print_timestamp("ファイルのWeb送信が完了しました (T1記録)")

    except Exception as e:
        print_timestamp(f"Web操作中にエラー発生: {e}")
        try:
            err_img = os.path.join(get_log_dir(), f"Error_Send_{datetime.datetime.now().strftime('%H%M%S')}.png")
            driver.save_screenshot(err_img)
            print_timestamp(f"エラー画面のスクリーンショットを保存しました: {err_img}")
        except:
            print_timestamp("スクリーンショットの保存に失敗しました")

        # [解析用] 画面上の操作可能な要素の情報をダンプする
        try:
            dom_info = driver.execute_script("""
                var res = [];
                var frames = document.querySelectorAll('iframe, frame');
                res.push('--- FRAMES ---');
                for(var j=0; j<frames.length; j++) {
                    res.push('<' + frames[j].tagName.toLowerCase() + '> id=\\'' + frames[j].id + '\\' name=\\'' + frames[j].name + '\\' src=\\'' + frames[j].src + '\\'');
                }
                res.push('--- ELEMENTS ---');
                var elements = document.querySelectorAll('input, textarea, button, select');
                for(var i=0; i<elements.length; i++) {
                    var el = elements[i];
                    var isVis = (el.offsetWidth > 0 && el.offsetHeight > 0) ? "表示" : "隠し";
                    var text = (el.value || el.innerText || '').replace(/\\n/g, ' ').substring(0, 30);
                    res.push("[" + isVis + "] <" + el.tagName.toLowerCase() + "> id='" + el.id + "', name='" + el.name + "', type='" + el.type + "', class='" + el.className + "', text='" + text + "'");
                }
                return res.join('\\n');
            """)
            dump_path = os.path.join(get_log_dir(), f"FormElements_Dump_{datetime.datetime.now().strftime('%H%M%S')}.txt")
            with open(dump_path, "w", encoding="utf-8") as f:
                f.write(dom_info)
            print_timestamp(f"画面上の要素一覧を解析用ダンプとして出力しました: {dump_path}")
        except Exception as dump_e:
            print_timestamp(f"要素ダンプに失敗: {dump_e}")

        # [解析用] 画面全体のHTMLソースをダンプする
        try:
            page_src = driver.page_source
            dump_html_path = os.path.join(get_log_dir(), f"PageSource_Dump_{datetime.datetime.now().strftime('%H%M%S')}.html")
            with open(dump_html_path, "w", encoding="utf-8") as f:
                f.write(page_src)
            print_timestamp(f"画面全体のHTMLソースをダンプしました: {dump_html_path}")
        except Exception as html_e:
            print_timestamp(f"HTMLダンプに失敗: {html_e}")

        t1_time = None
    finally:
        # クリーンアップ（ブラウザを閉じる）
        try:
            driver.quit()
        except:
            pass

    return t1_time, subject_text

def parse_header_date(date_str):
    """Dateヘッダー文字列をdatetimeに変換"""
    try:
        # RFC2822形式のパース
        parsed = email.utils.parsedate_tz(date_str)
        if parsed:
            timestamp = email.utils.mktime_tz(parsed)
            return datetime.datetime.fromtimestamp(timestamp)
    except:
        pass
    return None

def monitor_pop_mail(expected_subject, timeout_minutes=15):
    """指定された件名のメールが届くかをPOP3で監視し、T_Hdr と T2 を返す"""
    start_wait = datetime.datetime.now()
    deadline = start_wait + datetime.timedelta(minutes=timeout_minutes)

    print_timestamp(f"POP3でのメール着信監視を開始します (ターゲット: '{expected_subject}')")

    while datetime.datetime.now() < deadline:
        try:
            # POP3 サーバー接続 (SSL)
            pop = poplib.POP3_SSL(POP_SERVER, POP_PORT)
            pop.user(POP_USER)
            pop.pass_(POP_PASS)

            # メール件数とサイズ取得
            num_messages = len(pop.list()[1])

            for i in range(num_messages, 0, -1):
                # サーバーの負荷を下げるため、最新の数件だけチェックする方針でもOK
                # (ここでは後ろから最新のメールを確認)
                raw_email = pop.retr(i)[1]
                msg_data = b'\r\n'.join(raw_email)
                msg_obj = email.message_from_bytes(msg_data)

                # 件名デコード
                subject, encoding = decode_header(msg_obj.get("Subject", ""))[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8", errors="replace")

                if expected_subject in subject:
                    # 対象メール発見
                    t2_time = datetime.datetime.now()

                    # ヘッダー内のT_Hdr取得
                    date_header = msg_obj.get("Date", "")
                    t_hdr = parse_header_date(date_header)

                    # サーバーにはThunderbird等のメーラーでも受信できるよう残しておく
                    pop.quit()

                    print_timestamp("ターゲットメールを受信・検知しました（サーバーには残します）")
                    return t_hdr, t2_time

            pop.quit()
        except Exception as e:
            print_timestamp(f"POP3監視中に通信エラー (リトライします): {e}")

        # 30秒間隔でポーリング
        time.sleep(30)

    print_timestamp(f"タイムアウト: {timeout_minutes}分待機しましたが受信できませんでした。")
    return None, None

def clean_old_history():
    """Webの送信履歴から2時間以上前のレコードを削除する"""
    options = Options()
    # options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])

    driver = webdriver.Edge(options=options)

    try:
        print_timestamp("履歴クリーンアップ開始...")
        driver.get(WEB_URL)
        safe_send_keys(driver, By.ID, "textfieldLoginId", WEB_ID)
        safe_send_keys(driver, By.XPATH, "/html/body/form[1]/div[1]/div/div[3]/div[1]/table[2]/tbody/tr/td[2]/input", WEB_PASS)
        safe_click(driver, By.XPATH, "/html/body/form[1]/div[1]/div/div[3]/div[2]/span/input") # ログイン
        time.sleep(2)

        safe_click(driver, By.XPATH, "/html/body/form/div[1]/div[1]/div[3]/div[3]/div/ul/li[2]/a") # ShareDisk
        time.sleep(1)
        # 履歴画面への遷移 (実際のXPath要確認、ここでは送信履歴ボタンと想定)
        safe_click(driver, By.XPATH, "//a[contains(text(), '送信履歴') or contains(text(), '履歴')]")
        time.sleep(2)

        # 本来は行のリストを取得し、送信日時をパースして2時間を超えるものにチェックを入れる処理
        # (DOM仕様に激しく依存するため、概念的な実装を提供)
        rows = driver.find_elements(By.XPATH, "//tr[contains(@class, 'history-row') or contains(@class, 'data-row')]")
        now = datetime.datetime.now()
        deleted_count = 0

        for row in rows:
            try:
                date_str = row.find_element(By.XPATH, ".//td[contains(@class, 'date')]").text
                # 例: 2026/02/20 12:34:56 の形を想定
                row_time = datetime.datetime.strptime(date_str, "%Y/%m/%d %H:%M:%S")
                if (now - row_time).total_seconds() > HISTORY_DELETE_HOURS * 3600:
                    checkbox = row.find_element(By.XPATH, ".//input[@type='checkbox']")
                    if not checkbox.is_selected():
                        checkbox.click()
                        deleted_count += 1
            except:
                pass

        if deleted_count > 0:
            safe_click(driver, By.XPATH, "//a[contains(text(), '削除')]")
            # 確認ダイアログ対策
            try:
                WebDriverWait(driver, 3).until(EC.alert_is_present()).accept()
            except:
                pass
            print_timestamp(f"{deleted_count}件の古い履歴を削除しました。")
        else:
            print_timestamp("削除対象の古い履歴はありませんでした。")

    except Exception as e:
        print_timestamp(f"履歴クリーンアップ処理中にエラー発生: {e}")
        try:
            err_img = os.path.join(get_log_dir(), f"Error_Clean_{datetime.datetime.now().strftime('%H%M%S')}.png")
            driver.save_screenshot(err_img)
            print_timestamp(f"エラー画面のスクリーンショットを保存しました: {err_img}")
        except:
            pass
    finally:
        try:
            driver.quit()
        except:
            pass

# ==========================================
# メインループ
# ==========================================
def wait_interval():
    """指定されたインターバル（分）だけ待機する"""
    wait_sec = LOOP_INTERVAL_MINUTES * 60
    print_timestamp(f"次回の実行まで待機中... ({wait_sec}秒)")
    time.sleep(wait_sec)

def main_job():
    """1回分の処理サイクル(送信 -> 検知 -> 記録 -> クリーンアップ)"""
    print_timestamp("--- 処理サイクル開始 ---")

    # 1. 履歴掃除（送信処理の安定稼働まで一時的に無効化）
    # clean_old_history()

    # 2. Web送信処理 (最大3回リトライ)
    t1, expected_subject = None, None
    for attempt in range(3):
        t1, expected_subject = execute_web_transmission()
        if t1:
            break
        print_timestamp(f"Web送信処理が失敗したためリトライします ({attempt+1}/3)")
        time.sleep(10) # リトライ前に少し待機

    if t1:
        # 3. POP3監視処理
        t_hdr, t2 = monitor_pop_mail(expected_subject)

        # 4. ログ書き込み
        if t2:
            delay = int((t2 - t1).total_seconds())
            write_log(t1, t_hdr, t2, delay, "SUCCESS")
        else:
            write_log(t1, None, None, "", "TIMEOUT_NO_MAIL")
    else:
        write_log(None, None, None, "", "ERROR_WEB_TRANSMIT")

    print_timestamp("--- 処理サイクル終了 ---")

if __name__ == "__main__":
    init_csv_log()
    print_timestamp(f"遅延計測ツール 起動 (稼働時間: {START_HOUR:02d}:00 - {END_HOUR:02d}:00)")

    while True:
        now = datetime.datetime.now()

        # 稼働時間帯の判定
        if now.hour >= START_HOUR and now.hour < END_HOUR:
            try:
                main_job()
            except Exception as e:
                print_timestamp(f"システムエラーでプロセスが中断しました（次回リトライします）: {e}")
        else:
            print_timestamp("稼働時間外のためスキップします。")

        # 実行完了後、次回まで待機
        wait_interval()
