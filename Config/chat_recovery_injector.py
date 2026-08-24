import os
import sys
import zipfile
import shutil
from pathlib import Path

def main():
    print("="*50)
    print("🤖 Antigravity Chat Recovery Injector (全自動インジェクタ)")
    print("="*50)
    
    # Paths
    user_profile = os.environ.get("USERPROFILE", "")
    brain_dir = Path(user_profile) / ".gemini" / "antigravity-ide" / "brain"
    
    script_dir = Path(__file__).parent
    zip_path = script_dir / "Antigravity_ChatHistory_Backup.zip"
    
    if not zip_path.exists():
        print(f"❌ エラー: バックアップZIPが見つかりません: {zip_path.name}")
        return
        
    if not brain_dir.exists():
        print(f"❌ エラー: Antigravityのbrainフォルダが見つかりません: {brain_dir}")
        return

    print(f"📦 バックアップZIPを解析中...")
    
    # Get UUID folders in the zip
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
            
    # 新しい順にソート (作成日時)
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
        
        # 既存のダミーデータを削除してバックアップを流し込む
        shutil.rmtree(target_dir)
        shutil.copytree(source_dir, target_dir)
        
    print("🧹 一時ファイルをクリーンアップ中...")
    shutil.rmtree(temp_extract_dir)
    
    print("\n🎉 【復旧完了！】")
    print("Antigravity IDEを起動してください。サイドバーの「新しいチャット」の中に")
    print("過去のチャット履歴が完全に復元されているはずです！")

if __name__ == '__main__':
    main()
