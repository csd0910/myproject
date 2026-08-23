import csv
import re
import time
import random
import tkinter as tk
from playwright.sync_api import sync_playwright

# --- 設定値 ---
LOGIN_URL = "https://bizmw-login.com/c300ls1v/login"
OUTPUT_CSV_FILE = "ocn_mail_settings.csv"

def wait_for_user_start():
    root = tk.Tk()
    root.title("OCNスクレイピング操作パネル")
    root.geometry("450x180")
    root.attributes("-topmost", True)
    
    label = tk.Label(root, text="【1】手動ログインし、メールアドレス一覧へ進んでください。\n（1ページ目にいることを確認してください）\n\n【2】準備ができたら下のボタンを押してください。", justify="center")
    label.pack(pady=15)
    
    def on_click():
        root.quit()
        root.destroy()
        
    btn = tk.Button(root, text="▶ 全件スクレイピングを開始する", command=on_click, bg="#d9534f", fg="white", font=("", 12, "bold"))
    btn.pack(pady=10)
    
    root.mainloop()

def scrape_ocn_mail():
    with sync_playwright() as p:
        # 他のPCでも初期設定なしで動くよう、Windowsに標準搭載されている「Edge」を使用する
        browser = p.chromium.launch(headless=False, channel="msedge")
        context = browser.new_context()
        page = context.new_page()

        print(f"ブラウザを起動し、{LOGIN_URL} を開きます...")
        try:
            page.goto(LOGIN_URL)
        except Exception as e:
            print(f"URL展開エラー: {e}")

        # パネルを表示して待機
        wait_for_user_start()

        print("自動抽出を開始しました。")
        print(f"※途中で止めたい場合は、ターミナルで Ctrl + C を押してください。そこまでのデータは保存されます。")

        # --- 表示件数の最大化（ページ遷移を減らして高速化） ---
        try:
            print("★表示件数を最大（50件）に変更し、効率化を図ります...")
            page.locator("select[name='List_Ul_length']").first.select_option("50")
            time.sleep(2.0)  # 切り替え完了まで少し待つ
        except Exception:
            pass # 失敗した場合はそのまま進める

        PAGE_SIZE = 50

        # --- 【重要】全件数の取得と目標設定 ---
        try:
            page.locator("#List_Ul_info").first.wait_for(state="visible", timeout=10000)
            info_text = page.locator("#List_Ul_info").first.inner_text()
            # 実際のテキスト例: "1 - 10 件目を表示　　全数: 342"
            m_total = re.search(r'全数[:：]\s*(\d+)', info_text)
            if not m_total:
                print("全件数が取得できませんでした。処理を終了します。")
                browser.close()
                return
            total_count = int(m_total.group(1))
            print(f"★全件数: {total_count} 件を確認しました。この件数を目標に進めます。")
        except Exception as e:
            print(f"情報取得エラー: {e}")
            browser.close()
            return

        # ファイルを開きっぱなしにして追記していく
        with open(OUTPUT_CSV_FILE, mode="w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["メールアドレス", "受信者（改行区切り）"])
            writer.writeheader()

            processed_count = 0

            # 処理した件数が全件数に達するまでループ
            while processed_count < total_count:
                # 一覧画面が表示されるのを待機
                try:
                    page.locator("a.btn.tdButtons.edit").first.wait_for(state="visible", timeout=10000)
                except Exception:
                    pass

                # --- 現在のページ位置を確認し、目的のページまで自動復帰する ---
                while True:
                    try:
                        info_text = page.locator("#List_Ul_info").first.inner_text(timeout=5000)
                        # 実際のテキスト例: "11 - 20 件目を表示"
                        m_current = re.search(r'^\s*(\d+)\s*-', info_text)
                        if not m_current:
                            break
                        current_start = int(m_current.group(1))
                        
                        # 目的のスタート位置（0件目なら1、50件目なら51）
                        target_start = (processed_count // PAGE_SIZE) * PAGE_SIZE + 1
                        
                        if current_start < target_start:
                            # 目的のページに達していない場合は「次へ」を押す
                            next_li = page.locator("li.next").first
                            if next_li.count() > 0 and not next_li.evaluate("el => el.classList.contains('disabled')"):
                                print(f"    ※画面がリセットされているため、目標ページ（{target_start}件目〜）まで自動で進めます...")
                                page.locator("li.next > a").first.click()
                                
                                # 次のページが表示されるまで待つ
                                next_start = current_start + PAGE_SIZE
                                page.locator(f"#List_Ul_info:has-text('{next_start} -')").first.wait_for(state="visible", timeout=5000)
                            else:
                                break
                        else:
                            # 目的のページに到達している
                            break
                    except Exception as e:
                        break

                # --- データの取得処理 ---
                index_on_page = processed_count % PAGE_SIZE
                print(f"  {processed_count + 1} / {total_count} 件目を取得中...")
                
                settings_buttons = page.locator("a.btn.tdButtons.edit")
                if settings_buttons.count() <= index_on_page:
                    print(f"エラー: {processed_count+1}件目の設定ボタンが見つかりません。")
                    break

                # 詳細画面へ遷移
                settings_buttons.nth(index_on_page).click()
                
                try:
                    # キャンセルボタンの出現で画面読み込み完了を判定
                    page.locator("button.cancel").first.wait_for(state="visible", timeout=5000)
                    time.sleep(random.uniform(0.05, 0.15))  # 極限まで短縮した待機時間
                    
                    mail_locator = page.locator("input[name='mailaddress']").first
                    mail_address = mail_locator.get_attribute("value") if mail_locator.count() > 0 else "自動取得失敗"

                    textarea_locator = page.locator("textarea#custom_delivery").first
                    if textarea_locator.count() > 0:
                        receivers = textarea_locator.input_value().replace(",", "\n")
                    else:
                        receivers = ""
                        
                except Exception as e:
                    print(f"    エラー: {e}")
                    mail_address = "エラー"
                    receivers = ""

                # 1件ごとにCSVへ書き込み
                writer.writerow({"メールアドレス": mail_address, "受信者（改行区切り）": receivers})
                f.flush()

                # 一覧に戻る
                cancel_button = page.locator("button.cancel").first
                if cancel_button.count() > 0:
                    cancel_button.click()
                else:
                    page.go_back()
                    
                # 連続アクセスのスパム判定回避（短め）
                time.sleep(random.uniform(0.1, 0.3))
                    
                processed_count += 1

        print(f"★すべての処理（全 {total_count} 件）が完了しました。")
        print(f"データは {OUTPUT_CSV_FILE} に保存されています。")
        browser.close()

if __name__ == "__main__":
    scrape_ocn_mail()
