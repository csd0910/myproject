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
    backup_uuids = set()
    with zipfile.ZipFile(zip_path, 'r') as z:
        for info in z.infolist():
            parts = Path(info.filename).parts
            if len(parts) > 0 and len(parts[0]) == 36 and parts[0].count('-') == 4:
                backup_uuids.add(parts[0])
                    
    backup_uuids = list(backup_uuids)
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
    
    if len(local_chats) < num_backups:
        print(f"\n⚠️ 【準備不足】バックアップが {num_backups} 件ありますが、IDE上のチャット数が足りません。")
        print(f"👉 Antigravity IDEを開き、「New Chat」をあと【 {num_backups - len(local_chats)} 回 】連続で作成してください。")
        print("👉 その後、IDEを完全に閉じてから、このスクリプトを再度実行してください。")
        return
        
    dummies = local_chats[:num_backups]
    
    print(f"\n🎯 以下の通り、バックアップを空のダミーチャットに注入します:")
    for i in range(min(3, num_backups)):
        print(f"  [{backup_uuids[i]}] -> ダミースロット [{dummies[i][0].name}]")
    if num_backups > 3:
        print(f"  ...他 {num_backups - 3} 件")
        
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
        
    for i in range(num_backups):
        source_dir = temp_extract_dir / backup_uuids[i]
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
