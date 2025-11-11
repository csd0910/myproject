import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import csv
import os

# --- 設定とクローリングロジック ---

def get_session(url):
    """
    requests.Sessionを作成し、ベースURLへのアクセスを試みる (認証は省略/必要に応じて拡張)
    """
    session = requests.Session()
    try:
        # 認証が必要な場合は、ここでログインPOSTリクエストを実装する
        session.get(url, timeout=5)
        return session
    except requests.RequestException:
        return None

def analyze_structure(base_url):
    """
    ベースURLから主要なナビゲーションリンク（分類）を抽出し、リストを返す
    """
    try:
        session = get_session(base_url)
        if not session:
            raise Exception("ベースURLへの接続に失敗しました。")

        response = session.get(base_url, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # サイトの主要なナビゲーション領域を指定 (対象サイトに合わせて調整が必要)
        # 例: <nav>タグ内のリンク、id="sidebar"内のリンク、class="main-menu"内のリンク
        nav_elements = soup.select('nav a[href], #sidebar a[href], .main-menu a[href], .navbar a[href]')

        major_paths = set()
        base_netloc = urlparse(base_url).netloc

        for link in nav_elements:
            href = link.get('href')
            full_url = urljoin(base_url, href)
            parsed_url = urlparse(full_url)

            # 1. 同じホストであること
            # 2. ログイン/ログアウトページではないこと
            # 3. 拡張子を持つファイル（画像、PDFなど）ではないこと
            if (parsed_url.netloc == base_netloc and
                not parsed_url.path.lower().startswith(('/login', '/logout', '/signout')) and
                not parsed_url.path.split('/')[-1].count('.')):

                path = parsed_url.path.rstrip('/')

                if path and path != urlparse(base_url).path.rstrip('/'):
                    # パスのルートにスラッシュを追加して、一貫性を持たせる
                    major_paths.add(path if path.startswith('/') else '/' + path)

        return sorted(list(major_paths))

    except Exception as e:
        raise Exception(f"構造分析エラー: {e}")

def analyze_and_crawl(session, base_url, target_classification_path):
    """
    指定された分類パス以下のページを巡回し、データと次のリンクを抽出する
    """
    start_url = urljoin(base_url, target_classification_path)
    crawl_queue = [start_url]
    visited_urls = {start_url}
    pages_data = []

    while crawl_queue and len(pages_data) < 100: # 念のため最大100ページに制限
        current_url = crawl_queue.pop(0)

        try:
            response = session.get(current_url, timeout=10)
            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            page_title = soup.title.string.strip() if soup.title else 'No Title'

            # --- 💡 データ取得のコアロジック（フォームや設定値など） ---
            # 簡潔にするため、ここではタイトルと主要な見出しを抽出

            # 主要見出し (H1) からテキストを取得
            h1 = soup.find('h1')
            main_heading = h1.get_text(strip=True)[:50] if h1 else 'N/A'

            # 取得したデータをリストに追加
            pages_data.append({
                'URL': current_url,
                'Title': page_title,
                'Main_Heading': main_heading,
                'Status': response.status_code,
            })
            # --------------------------------------------------------

            # リンクの抽出とフィルタリング (ツリー構造の分析)
            base_netloc = urlparse(base_url).netloc
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(current_url, href)
                parsed_url = urlparse(full_url)

                # 1. 巡回済みでないこと
                # 2. ベースURLと同じホストであること
                # 3. 指定された「分類」パスで始まること
                if (full_url not in visited_urls and
                    parsed_url.netloc == base_netloc and
                    parsed_url.path.startswith(target_classification_path)):

                    visited_urls.add(full_url)
                    crawl_queue.append(full_url)

        except requests.RequestException:
            continue

    return pages_data

# --- GUIクラス ---

class WebCrawlerApp:
    def __init__(self, master):
        self.master = master
        master.title("ウェブ管理画面データ抽出ツール")

        # UI要素の配置

        # 1. URL入力
        tk.Label(master, text="ベースURL:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.url_entry = tk.Entry(master, width=50)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5)
        self.url_entry.insert(0, "https://example.com/admin")

        # 2. 構造分析ボタン
        self.analyze_button = tk.Button(master, text="サイト構造を分析 (分類リスト取得)", command=self.start_analysis, bg='#ADD8E6')
        self.analyze_button.grid(row=1, column=0, columnspan=2, pady=10)

        # 3. 分類選択 (Combobox)
        tk.Label(master, text="分類を選択:").grid(row=2, column=0, sticky='w', padx=5, pady=5)
        self.path_combobox = ttk.Combobox(master, state="readonly", width=48)
        self.path_combobox.grid(row=2, column=1, padx=5, pady=5)

        # 4. 実行ボタン
        self.crawl_button = tk.Button(master, text="データ取得とCSV出力", command=self.start_crawl, bg='#90EE90', state=tk.DISABLED)
        self.crawl_button.grid(row=3, column=0, columnspan=2, pady=10)

        # 5. ステータス表示
        self.status_label = tk.Label(master, text="待機中...")
        self.status_label.grid(row=4, column=0, columnspan=2, pady=5)

        # ウィンドウを中央に配置
        self.center_window()

    def center_window(self):
        self.master.update_idletasks()
        width = self.master.winfo_width()
        height = self.master.winfo_height()
        x = (self.master.winfo_screenwidth() // 2) - (width // 2)
        y = (self.master.winfo_screenheight() // 2) - (height // 2)
        self.master.geometry(f'{width}x{height}+{x}+{y}')

    def start_analysis(self):
        """構造分析フェーズを実行し、分類リストをComboboxに設定する"""
        base_url = self.url_entry.get().strip().rstrip('/')
        if not base_url:
            messagebox.showwarning("入力エラー", "ベースURLを入力してください。")
            return

        self.status_label.config(text="処理中... サイト構造を分析しています。")
        self.master.update()

        try:
            # 構造分析関数を呼び出し
            major_paths = analyze_structure(base_url)

            if major_paths:
                self.path_combobox['values'] = major_paths
                self.path_combobox.set(major_paths[0])
                self.crawl_button.config(state=tk.NORMAL)
                self.status_label.config(text=f"分析完了。{len(major_paths)}個の分類が見つかりました。選択して実行してください。")
            else:
                self.path_combobox['values'] = []
                self.path_combobox.set("")
                self.crawl_button.config(state=tk.DISABLED)
                self.status_label.config(text="分析完了 (分類パスが見つかりませんでした。URLが正しいか確認してください)")

        except Exception as e:
            messagebox.showerror("分析エラー", str(e))
            self.status_label.config(text="エラーが発生しました。")

    def start_crawl(self):
        """ユーザーが選択した分類パスで巡回を開始し、CSVに出力する"""
        base_url = self.url_entry.get().strip().rstrip('/')
        selected_path = self.path_combobox.get().strip()

        if not selected_path:
            messagebox.showwarning("選択エラー", "分類パスを選択してください。")
            return

        self.status_label.config(text=f"処理中... {selected_path}以下のデータを取得しています。")
        self.master.update()

        # ログインセッションを確立
        session = get_session(base_url)
        if not session:
            messagebox.showerror("接続エラー", "セッション確立/接続に失敗しました。")
            self.status_label.config(text="エラーが発生しました。")
            return

        try:
            # クローリング開始
            data_results = analyze_and_crawl(session, base_url, selected_path)

            if data_results:
                self.save_to_csv(data_results, selected_path)
            else:
                messagebox.showinfo("結果", "指定された分類パスでデータが見つかりませんでした。")
                self.status_label.config(text="完了 (データなし)")

        except Exception as e:
            messagebox.showerror("致命的なエラー", f"予期せぬエラーが発生しました: {e}")
            self.status_label.config(text="エラーが発生しました。")

    def save_to_csv(self, data, path_name):
        """取得したデータをCSVファイルとして保存する"""
        # ファイル保存ダイアログを開く
        clean_path = path_name.strip('/').replace('/', '_')
        default_filename = f"crawl_data_{clean_path}.csv"

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=default_filename,
            filetypes=[("CSV files", "*.csv")]
        )

        if not filepath:
            self.status_label.config(text="CSV保存をキャンセルしました。")
            return

        try:
            fieldnames = list(data[0].keys())
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile: # utf-8-sigでExcelでの文字化け防止
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)

            messagebox.showinfo("完了", f"データを以下のファイルに保存しました:\n{filepath}")
            self.status_label.config(text=f"完了 ({len(data)}件のデータを保存)")

        except Exception as e:
            messagebox.showerror("CSVエラー", f"CSVファイルの書き込み中にエラーが発生しました。\nエラー: {e}")
            self.status_label.config(text="エラーが発生しました。")

# --- メイン処理 ---
if __name__ == '__main__':
    root = tk.Tk()
    app = WebCrawlerApp(root)
    root.mainloop()