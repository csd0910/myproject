import os
import re
import zipfile
import datetime
from pathlib import Path

def get_conversations_dir():
    user_profile = os.environ.get("USERPROFILE", "")
    return Path(user_profile) / ".gemini" / "antigravity-ide" / "conversations"

def extract_text_from_pb(file_path):
    with open(file_path, 'rb') as f:
        data = f.read()
    
    # 不正なバイト列を置換文字()に変換しつつUTF-8として読み込む
    text = data.decode('utf-8', errors='replace')
    
    # Protobufのバイナリ制御文字や置換文字を区切り文字としてテキストを分割
    # (\n, \t, \r は改行やインデントとして残す)
    chunks = re.split(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]+', text)
    
    valid_chunks = []
    for chunk in chunks:
        chunk = chunk.strip()
        # 意味のある長さのテキスト（10文字以上）のみを抽出
        if len(chunk) >= 10:
            valid_chunks.append(chunk)
            
    return "\n\n" + ("-" * 40) + "\n\n".join(valid_chunks)

def main():
    print("="*60)
    print("Legacy .pb Chat Log Extractor (過去ログ救出ツール)")
    print("="*60)
    
    conv_dir = get_conversations_dir()
    if not conv_dir.exists():
        print(f"エラー: フォルダが見つかりません ({conv_dir})")
        return
        
    script_dir = Path(__file__).parent
    out_dir = script_dir / "Legacy_Chat_Backups"
    
    if not out_dir.exists():
        out_dir.mkdir()
        
    pb_files = list(conv_dir.glob("*.pb"))
    if not pb_files:
        print("抽出できる .pb ファイルが見つかりませんでした。")
        return
        
    print(f"{len(pb_files)} 件のレガシーチャット履歴をテキスト化します...")
    
    for i, pb_file in enumerate(pb_files):
        print(f"  [{i+1}/{len(pb_files)}] 抽出中: {pb_file.name} ...")
        extracted_text = extract_text_from_pb(pb_file)
        
        mtime = pb_file.stat().st_mtime
        dt_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y%m%d_%H%M%S')
        
        out_filename = f"chat_{dt_str}_{pb_file.stem[:8]}.md"
        out_filepath = out_dir / out_filename
        
        with open(out_filepath, 'w', encoding='utf-8') as f:
            f.write(f"# レガシーチャット抽出データ\n")
            f.write(f"- オリジナルUUID: {pb_file.stem}\n")
            f.write(f"- 最終更新日時: {dt_str}\n\n")
            f.write(extracted_text)
            
    print(f"\n抽出完了！")
    print(f"抽出したテキストファイルは {out_dir} に保存されました。")
    
    zip_path = script_dir / "Legacy_Chat_Backups.zip"
    print(f"持ち運び用にZIP形式に圧縮しています... ({zip_path.name})")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for md_file in out_dir.glob("*.md"):
            zf.write(md_file, md_file.name)
            
    print("ZIPファイルの作成が完了しました！")

if __name__ == '__main__':
    main()
