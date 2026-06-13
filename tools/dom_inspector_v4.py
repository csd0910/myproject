import time
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.edge.options import Options

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "dom_report_v4.txt")

def log(f, msg):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line)
    f.write(line + "\n")
    f.flush()

def main():
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        log(f, "=== サイボウズ DOM徹底調査スクリプト (次へボタン特化) ===")
        options = Options()
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        driver = webdriver.Edge(options=options)
        driver.get("https://forestway.cybozu.com/login")

        print("\n>>> サイボウズにログインし、メールの「受信箱」を開いてください")
        print(">>> (メールが50件以上あり、「次へ」ボタンがある状態にしてください)")
        
        while True:
            if "MailIndex" in driver.current_url:
                try:
                    # テーブルがあるか確認
                    if driver.execute_script("return document.querySelectorAll('table.dataListSummary').length > 0"):
                        break
                except: pass
            time.sleep(1)

        log(f, ">>> 受信箱を検知しました。調査を開始します。")
        time.sleep(2)

        # 1. 現在のメール一覧のID取得（比較用）
        def get_ids():
            return driver.execute_script("""
                var ids = [];
                document.querySelectorAll('.dataListSummary tbody tr').forEach(tr => {
                    var a = tr.querySelector('a[href*="MailView"]');
                    if(a){
                        var m = a.getAttribute('href').match(/=(\\d+)/);
                        if(m) ids.push(m[1]);
                    }
                });
                return ids;
            """)
        
        ids_page1 = get_ids()
        log(f, f"【ページ1】取得ID数: {len(ids_page1)}")
        if ids_page1: log(f, f"【ページ1】最初のID: {ids_page1[0]}")

        # 2. ページャー全体のOuterHTMLを取得
        pager_html = driver.execute_script("""
            var p = document.querySelector('.pager, [class*="pager"], .mailCount');
            return p ? p.outerHTML : 'N/A';
        """)
        log(f, f"【ページャー全体のOuterHTML】:\n{pager_html}\n")

        # 3. 「次へ」リンクの徹底調査
        next_btn_info = driver.execute_script("""
            var info = [];
            // テキストで「次」を含むaタグを探す
            var links = document.querySelectorAll('a');
            for(var i=0; i<links.length; i++) {
                var a = links[i];
                var t = (a.innerText || '').trim();
                if(t.includes('次') || t.includes('>>')) {
                    // XPath計算関数
                    var getXPath = function(element) {
                        if (element.id !== '') return 'id("' + element.id + '")';
                        if (element === document.body) return element.tagName;
                        var ix = 0;
                        var siblings = element.parentNode.childNodes;
                        for (var j = 0; j < siblings.length; j++) {
                            var sibling = siblings[j];
                            if (sibling === element) return getXPath(element.parentNode) + '/' + element.tagName + '[' + (ix + 1) + ']';
                            if (sibling.nodeType === 1 && sibling.tagName === element.tagName) ix++;
                        }
                    };
                    info.push({
                        text: t,
                        href: a.getAttribute('href'),
                        outerHTML: a.outerHTML,
                        xpath: getXPath(a)
                    });
                }
            }
            return info;
        """)

        log(f, f"【「次へ」ボタンの調査結果（{len(next_btn_info)}件）】")
        for i, info in enumerate(next_btn_info):
            log(f, f"--- 候補 {i+1} ---")
            log(f, f"Text: {info['text']}")
            log(f, f"Href: {info['href']}")
            log(f, f"XPath: {info['xpath']}")
            log(f, f"OuterHTML: {info['outerHTML']}\n")

        # 4. 「次へ」を実際にクリックしてみる
        if next_btn_info:
            log(f, f">>> 最初の候補をJavaScriptでクリックします...")
            driver.execute_script("""
                var links = document.querySelectorAll('a');
                for(var i=0; i<links.length; i++) {
                    if((links[i].innerText || '').includes('次')) {
                        links[i].click();
                        break;
                    }
                }
            """)
            
            # 変化を待つ
            wait_start = time.time()
            page_changed = False
            while time.time() - wait_start < 10:
                time.sleep(1)
                ids_page2 = get_ids()
                if ids_page2 and ids_page1 and ids_page2[0] != ids_page1[0]:
                    page_changed = True
                    log(f, f">>> ページの変化を検知しました！")
                    log(f, f"【ページ2】取得ID数: {len(ids_page2)}")
                    log(f, f"【ページ2】最初のID: {ids_page2[0]}")
                    break
            
            if not page_changed:
                log(f, f"!! 10秒待機しましたがページが変化しませんでした。")

        log(f, f"\n=== 調査終了 ===")
        print(f"\n>>> 完了しました！レポートを確認します。")
        input("Enterキーを押すとブラウザを閉じます...")
        driver.quit()

if __name__ == "__main__":
    main()
