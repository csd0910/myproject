import os
import tkinter as tk
from tkinter import messagebox
from PIL import ImageGrab, Image, ImageOps
from img2table.document import Image as Img2TableImage
from img2table.ocr import TesseractOCR

import tempfile

import pytesseract
from pytesseract import Output

def convert_clipboard_to_excel():
    # クリップボードから画像を取得
    img = ImageGrab.grabclipboard()
    if img is None:
        messagebox.showwarning("エラー", "クリップボードに画像がありません。表の画像をコピーしてから実行してください。")
        return

    try:
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            img = img.convert('RGB')
            
        # 【画質改善】Tesseractの認識精度を上げるための前処理
        from PIL import Image
        img = img.convert('L') # グレースケール（白黒）化して背景色の影響を減らす
        img = img.resize((img.width * 2, img.height * 2), Image.Resampling.LANCZOS) # 2倍に拡大して文字をクッキリさせる
            
        tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if not os.path.exists(tesseract_cmd):
            messagebox.showerror("エラー", f"Tesseractが見つかりません。\n{tesseract_cmd}")
            return
            
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        
        # Windows環境用の文字コード対策
        os.environ["LC_ALL"] = "C"
        os.environ["LANG"] = "C"
        
        # 辞書データの指定
        tessdata_path = r"C:\OCR_Temp\tessdata"
        os.environ["TESSDATA_PREFIX"] = tessdata_path
        custom_config = r'--psm 6'

        # 画像から文字と位置情報を抽出
        d = pytesseract.image_to_data(img, lang="jpn", output_type=Output.DICT, config=custom_config)
        
        # 行ごとに文字と座標をグループ化する
        lines = {}
        for i in range(len(d['text'])):
            text = d['text'][i].strip()
            if not text:
                continue
            
            # ブロック、段落、行の番号で同じ行をまとめる
            line_key = (d['block_num'][i], d['par_num'][i], d['line_num'][i])
            if line_key not in lines:
                lines[line_key] = []
            
            # (文字, 左端のX座標, 右端のX座標) を保存
            lines[line_key].append({
                'text': text,
                'left': d['left'][i],
                'right': d['left'][i] + d['width'][i]
            })

        # X座標の距離を計算して、離れている場合だけタブ区切り（別セル）にする
        output_text = ""
        for key in sorted(lines.keys()):
            row_items = lines[key]
            row_items.sort(key=lambda x: x['left']) # X座標順に並び替え
            
            row_str = ""
            for j in range(len(row_items)):
                if j == 0:
                    row_str += row_items[j]['text']
                else:
                    prev_right = row_items[j-1]['right']
                    curr_left = row_items[j]['left']
                    
                    # 前の文字との隙間が 20ピクセル 以上空いていれば別セルとみなす
                    if curr_left - prev_right > 20:
                        row_str += "\t" + row_items[j]['text']
                    else:
                        row_str += row_items[j]['text']
                        
            output_text += row_str + "\n"
            
        if not output_text.strip():
            messagebox.showwarning("警告", "文字が読み取れませんでした。")
            return

        # クリップボードに結果をコピー
        root.clipboard_clear()
        root.clipboard_append(output_text)
        root.update() # クリップボードに反映
        
        messagebox.showinfo("完了", "読み取り完了しました！\nExcelのセルを選択して「貼り付け（Ctrl+V）」を行ってください。")
        
    except Exception as e:
        messagebox.showerror("エラー", f"変換中にエラーが発生しました:\n{str(e)}")

# UI（画面）の設定
root = tk.Tk()
root.title("表画像 → Excel変換ツール")
root.geometry("320x150")

# ウィンドウを最前面に表示
root.attributes('-topmost', True)

label = tk.Label(root, text="表の画像をコピー（Ctrl+C）した状態で\n下のボタンを押してください", pady=10)
label.pack()

btn = tk.Button(root, text="クリップボードから変換", command=convert_clipboard_to_excel, bg="#4CAF50", fg="white", font=("", 11, "bold"), pady=8)
btn.pack(pady=5)

root.mainloop()
