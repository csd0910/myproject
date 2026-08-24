import os
import sys
import zipfile
import shutil
from pathlib import Path

def get_brain_dir():
    user_profile = os.environ.get("USERPROFILE", "")
    return Path(user_profile) / ".gemini" / "antigravity-ide" / "brain"

def do_backup(zip_path, brain_dir):
    print("\n📦 バックアップ処理を開始します...")
    
    if not brain_dir.exists():
        print(f"❌ エラー: brainフォルダが見つかりません: {brain_dir}")
        return

    # 既存のZIPがあれば削除
    if zip_path.exists():
        try:
            zip_path.unlink()
        except Exception as e:
            print(f"❌ エラー: 古いバックアップを削除できませんでした ({e})")
            return

    # UUID形式のフォルダのみを収集
    target_dirs = []
    for d in brain_dir.iterdir():
        if d.is_dir() and len(d.name) == 36 and d.name.count('-') == 4:
            target_dirs.append(d)
            
    if not target_dirs:
        print("❌ バックアップするチャット履歴が見つかりません。")
        return

    print(f"🔍 {len(target_dirs)} 件のチャット履歴を圧縮中... (少々お待ちください)")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for folder in target_dirs:
            for filepath in folder.rglob('*'):
                if filepath.is_file():
                    arcname = filepath.relative_to(brain_dir)
                    zf.write(filepath, arcname)
                    
    print(f"🎉 バックアップ完了！")
    print(f"保存先: {zip_path.name}")
    print("※忘れずに Git へ Push してクラウドに同期してください。")

def do_restore(zip_path, brain_dir, script_dir):
    print("\n🚀 復元（インジェクション）処理を開始します...")
    
    if not zip_path.exists():
        print(f"❌ エラー: バックアップZIPが見つかりません: {zip_path.name}")
        return
        
    print(f"📦 バックアップZIPを解析中...")
    backup_last_modified = {}
    with zipfile.ZipFile(zip_path, 'r') as z:
        for info in z.infolist():
            parts = Path(info.filename).parts
            if len(parts) > 0 and len(parts[0]) == 36 and parts[0].count('-') == 4:
                uuid = parts[0]
                # Keep track of the most recent file date in each UUID folder
                dt = info.date_time # tuple (year, month, day, hour, min, sec)
                if uuid not in backup_last_modified or dt > backup_last_modified[uuid]:
                    backup_last_modified[uuid] = dt
                    
    # Sort UUIDs by most recent first
    backup_uuids = sorted(list(backup_last_modified.keys()), key=lambda x: backup_last_modified[x], reverse=True)
    num_backups = len(backup_uuids)
    
    if num_backups == 0:
        print("❌ エラー: ZIP内に有効なチャットデータが見つかりませんでした。")
        return
        
    print(f"✅ {num_backups} 件のチャットバックアップを検出しました。")
    
    print(f"🔍 ローカルのIDE状態をチェック中...")
    local_chats = []
    for d in brain_dir.iterdir():
        if d.is_dir() and len(d.name) == 36 and d.name.count('-') == 4:
            local_chats.append((d, d.stat().st_ctime))
            
    local_chats.sort(key=lambda x: x[1], reverse=True)
    
    # If there are fewer local chats (dummies) than backups, we only restore what we can fit!
    restorable_count = min(len(local_chats), num_backups)
    
    if len(local_chats) < num_backups:
        print(f"\n⚠️ 【お知らせ】バックアップは {num_backups} 件ありますが、IDE上のチャット（空箱）が {len(local_chats)} 個しかありません。")
        print(f"👉 今回は「最近使ったチャット 最新 {restorable_count} 件」だけを優先して復元します！")
        print("（もしもっと古い履歴も見たい場合は、後でIDEで「新しいチャット」を追加作成してから再度実行すればOKです）")
        
    dummies = local_chats[:restorable_count]
    backup_uuids_to_restore = backup_uuids[:restorable_count]
    
    print(f"\n🎯 以下の通り、バックアップを空のダミーチャットに注入します:")
    for i in range(min(3, restorable_count)):
        print(f"  [{backup_uuids_to_restore[i]}] (最新) -> ダミースロット [{dummies[i][0].name}]")
    if restorable_count > 3:
        print(f"  ...他 {restorable_count - 3} 件")
        
    print("\n⚠️ 【最終確認】 上記の最新のダミーチャットを上書きしてよろしいですか？")
    print("※実行前に必ず Antigravity IDE を完全に終了させておいてください。")
    ans = input("実行しますか？ (y/n): ")
    if ans.lower() != 'y':
        print("処理を中止しました。")
        return
        
    print("\n🚀 バックアップを注入中... (数分かかる場合があります)")
    
    temp_extract_dir = script_dir / "temp_extract_recovery"
    if temp_extract_dir.exists():
        shutil.rmtree(temp_extract_dir)
    temp_extract_dir.mkdir()
    
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(temp_extract_dir)
        
    for i in range(restorable_count):
        source_dir = temp_extract_dir / backup_uuids_to_restore[i]
        target_dir = dummies[i][0]
        shutil.rmtree(target_dir)
        shutil.copytree(source_dir, target_dir)
        
    print("🧹 一時ファイルをクリーンアップ中...")
    shutil.rmtree(temp_extract_dir)
    
    print("\n🎉 【復旧完了！】")
    print("Antigravity IDEを起動してください。サイドバーの「新しいチャット」の中に")
    print("過去のチャット履歴が完全に復元されているはずです！")

def main():
    print("="*60)
    print("🔄 Antigravity Chat Sync Tool (バックアップ＆復元ツール)")
    print("="*60)
    
    script_dir = Path(__file__).parent
    zip_path = script_dir / "Antigravity_ChatHistory_Backup.zip"
    brain_dir = get_brain_dir()
    
    print("\nどちらの操作を行いますか？")
    print("  [1] ⬆️ 現在のチャット履歴をすべてZIPにバックアップする (PC移行・退社前)")
    print("  [2] ⬇️ ZIPからダミーチャットに履歴を復元する (別PC・出社時)")
    print("  [0] キャンセル")
    
    choice = input("\n番号を選択してください (1/2/0): ")
    
    if choice == '1':
        do_backup(zip_path, brain_dir)
    elif choice == '2':
        do_restore(zip_path, brain_dir, script_dir)
    else:
        print("キャンセルしました。")

if __name__ == '__main__':
    main()
