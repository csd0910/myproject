"""
サイボウズ DOM調査スクリプト v3
- ログイン後、ユーザーがメール一覧画面を開くのを待つ
- メール画面を検知したら自動でDOM調査・ページ送り構造を記録
- 結果を dom_report.txt に書き出す
"""

from selenium import webdriver
from selenium.webdriver.edge.options import Options
import time
import os
from datetime import datetime

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "dom_report.txt")
LOGIN_URL = "https://forestway.cybozu.com/login"

def log(f, msg):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line)
    f.write(line + "\n")
    f.flush()

def wait_for_mail_page(driver, timeout=180):
    """
    ログイン＆メール一覧画面への到達を待つ。
    URLに 'page=Mail' が含まれる、またはフォルダセレクトが存在する状態になったら
    ベースURL（?より前）を返す。
    """
    print(f"\n>>> ブラウザが開きました。")
    print(f">>> 手順1: サイボウズにログインしてください")
    print(f">>> 手順2: ログイン後、左メニューの「メール」をクリックしてメール一覧画面を開いてください")
    print(f">>> （URLに 'page=Mail' が含まれる画面になると自動で調査を開始します）")

    start = time.time()
    while time.time() - start < timeout:
        try:
            url = driver.current_url
            # メール画面のURLパターンを検知
            if "page=Mail" in url or "page=mail" in url:
                print(f"\n>>> メール画面を検知しました！ URL: {url}")
                time.sleep(2)
                return url.split('?')[0]
            # フォールバック: フォルダセレクトボックスの存在チェック
            try:
                opts = driver.execute_script("""
                    var sel = document.querySelector('select');
                    if(!sel) return 0;
                    var opts = sel.querySelectorAll('option');
                    // メール用セレクトは'受信'や'inbox'を含む
                    var hasMailOpt = Array.from(opts).some(function(o){
                        return o.value === '1' || o.value === 'inbox' || o.textContent.includes('受信');
                    });
                    return hasMailOpt ? opts.length : 0;
                """)
                if opts > 0:
                    print(f"\n>>> メールフォルダセレクトを検知しました！ URL: {url}")
                    time.sleep(2)
                    return url.split('?')[0]
            except:
                pass
        except:
            pass
        time.sleep(1)
    return None

def analyze_page(driver):
    """現在のページのメール一覧DOM構造を詳細解析"""
    return driver.execute_script("""
        var r = {};

        // --- テーブル検索（クラス名問わず全tableを調査）---
        var tables = document.querySelectorAll('table');
        var mailTable = null;
        tables.forEach(function(t){
            // メールリンクを含むテーブルを探す
            if(t.querySelector('a[href*="Mail"]') || t.querySelector('a[href*="mail"]')){
                if(!mailTable || t.rows.length > mailTable.rows.length) mailTable = t;
            }
        });
        r.table_found = !!mailTable;
        r.table_class = mailTable ? mailTable.className : 'N/A';
        r.table_id = mailTable ? mailTable.id : 'N/A';

        // --- 全行の解析 ---
        var rows = [];
        if(mailTable){
            Array.from(mailTable.querySelectorAll('tr')).forEach(function(tr, i){
                var imgs = Array.from(tr.querySelectorAll('img')).map(function(img){
                    return img.src.split('/').pop();
                });
                var links = Array.from(tr.querySelectorAll('a[href]')).map(function(a){
                    return a.getAttribute('href');
                });
                var mailLink = links.find(function(h){
                    return h && (h.includes('Mail') || h.includes('mail')) && !h.includes('Command=');
                });
                var idMatch = mailLink ? mailLink.match(/(?:EID|mEID|id|did|mDID|mailId|snum|EID)=(\\d+)/i) : null;

                rows.push({
                    i: i,
                    isHeader: !!tr.querySelector('th'),
                    isHidden: tr.style.display === 'none',
                    imgs: imgs,
                    mailId: idMatch ? idMatch[1] : null,
                    mailLink: mailLink ? mailLink.substring(0,150) : null,
                    text: tr.innerText.substring(0,80).replace(/\\n/g,' ')
                });
            });
        }
        r.rows = rows;
        r.total_tr = rows.length;
        r.valid_ids = rows.filter(function(row){ return row.mailId; }).length;
        r.hidden_rows = rows.filter(function(row){ return row.isHidden; }).length;
        r.star_flag_rows = rows.filter(function(row){
            return row.imgs.some(function(s){ return s.includes('star')||s.includes('flag'); });
        }).length;

        // --- 件数テキスト（ページャー）---
        var allText = document.body.innerText;
        var countM = allText.match(/(\\d+)\\s*件[中の\\s]*(\\d+)?/g);
        r.count_texts = countM ? countM.slice(0,8) : [];

        // --- ページャーHTML ---
        var pagerCandidates = [];
        document.querySelectorAll('*').forEach(function(el){
            var t = el.innerText || '';
            if(t.match(/\\d+件/) && el.children.length < 10 && el.tagName !== 'BODY' && el.tagName !== 'HTML'){
                pagerCandidates.push(el.outerHTML.substring(0,400));
            }
        });
        r.pager_candidates = pagerCandidates.slice(0,5);

        // --- 「次へ」リンク ---
        var nextLinks = [];
        Array.from(document.querySelectorAll('a')).forEach(function(a){
            var t = (a.innerText||'').trim();
            var h = a.getAttribute('href')||'';
            if(t === '次へ' || t === '>>' || t === '次' || t === 'Next'
               || (h.includes('start=') && !h.includes('Command=') && !h.includes('Delete'))){
                nextLinks.push({text: t, href: h.substring(0,200)});
            }
        });
        r.next_links = nextLinks.slice(0,15);

        // --- 現在のstartパラメータ ---
        var currentStart = window.location.href.match(/start=(\\d+)/);
        r.current_start = currentStart ? parseInt(currentStart[1]) : 0;
        r.current_url = window.location.href.substring(0,200);

        return r;
    """)

def main():
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        log(f, "=== サイボウズ DOM調査レポート v3 ===")
        log(f, f"調査開始: {datetime.now()}")

        options = Options()
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        driver = webdriver.Edge(options=options)
        driver.get(LOGIN_URL)

        # メール画面の到達を待機
        base_url = wait_for_mail_page(driver)
        if not base_url:
            log(f, "!! タイムアウト")
            driver.quit(); return

        log(f, f"\n検知したベースURL: {base_url}")
        log(f, f"現在URL: {driver.current_url}")

        # --- フォルダ構造の取得 ---
        log(f, "\n--- [調査1] フォルダ構造（セレクトボックス）---")
        folders = driver.execute_script("""
            var results = [];
            document.querySelectorAll('select option').forEach(function(opt){
                if(opt.value && opt.value !== 'sep'){
                    var txt = opt.textContent;
                    var m = txt.match(/^(\\u00a0| |　)+/);
                    results.push({ name: txt.trim(), fid: opt.value, depth: m ? m[0].length : 0 });
                }
            });
            return results;
        """) or []
        log(f, f"フォルダ総数: {len(folders)}")
        for fo in folders:
            indent = "  " * (fo['depth'] // 2)
            log(f, f"{indent}[fid={fo['fid']}] {fo['name']}")

        # --- 現在のページ（受信箱等）のDOM解析 ---
        log(f, "\n--- [調査2] 現在のメール一覧DOM解析 ---")
        r = analyze_page(driver)
        log(f, f"現在URL: {r.get('current_url')}")
        log(f, f"テーブル検出: {r.get('table_found')} / class={r.get('table_class')} / id={r.get('table_id')}")
        log(f, f"総TR行数: {r.get('total_tr')}")
        log(f, f"有効メールID数: {r.get('valid_ids')}")
        log(f, f"非表示行数: {r.get('hidden_rows')}")
        log(f, f"スター/フラグ画像で弾かれる行数: {r.get('star_flag_rows')}")
        log(f, f"現在のstartパラメータ: {r.get('current_start')}")
        log(f, f"件数テキスト候補: {r.get('count_texts')}")

        log(f, "\n-- ページャー候補HTML --")
        for pc in r.get('pager_candidates', []):
            log(f, pc)
            log(f, "---")

        log(f, "\n-- 次ページリンク --")
        for nl in r.get('next_links', []):
            log(f, f"  text='{nl['text']}' href='{nl['href']}'")

        log(f, "\n-- 各行の詳細（先頭15行）--")
        for row in r.get('rows', [])[:15]:
            log(f, f"  [{row['i']}] id={row.get('mailId')} hidden={row.get('isHidden')} imgs={row.get('imgs')} | {row.get('text','')[:70]}")

        log(f, "\n-- 各行の詳細（末尾5行）--")
        for row in r.get('rows', [])[-5:]:
            log(f, f"  [{row['i']}] id={row.get('mailId')} hidden={row.get('isHidden')} imgs={row.get('imgs')} | {row.get('text','')[:70]}")

        # --- 2ページ目の調査（次へリンクがあれば）---
        next_links = r.get('next_links', [])
        start_links = [nl for nl in next_links if 'start=' in nl.get('href', '')]
        if start_links:
            log(f, f"\n--- [調査3] 2ページ目のDOM解析 ---")
            nl = start_links[0]
            href = nl['href']
            next_url = href if href.startswith('http') else base_url + '?' + href.lstrip('/?')
            log(f, f"遷移先: {next_url}")
            driver.get(next_url)
            time.sleep(3)
            r2 = analyze_page(driver)
            log(f, f"2ページ目 有効ID数: {r2.get('valid_ids')}")
            log(f, f"2ページ目 startパラメータ: {r2.get('current_start')}")
            log(f, f"2ページ目 件数テキスト: {r2.get('count_texts')}")
            log(f, f"2ページ目 次リンク: {r2.get('next_links')}")

            # 最終ページも確認（次リンクがなければ最終ページ）
            r2_next = [nl for nl in r2.get('next_links', []) if 'start=' in nl.get('href', '')]
            if not r2_next:
                log(f, ">>> 2ページ目が最終ページです（次リンクなし）")
            else:
                log(f, f">>> さらに次のページがあります: {r2_next[0]}")

        log(f, "\n=== 調査完了 ===")

    print(f"\n>>> 完了！レポート: {OUTPUT_FILE}")
    input("Enterキーを押すとブラウザを閉じます...")
    driver.quit()

if __name__ == "__main__":
    main()
