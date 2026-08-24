import os
import sys
import zipfile
import shutil
from pathlib import Path
import logging

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def get_ide_dir():
    user_profile = os.environ.get("USERPROFILE", "")
    return Path(user_profile) / ".gemini" / "antigravity-ide"

def do_backup(zip_path, ide_dir):
    logger.info("バックアップ処理を開始します...")
    
    brain_dir = ide_dir / "brain"
    conv_dir = ide_dir / "conversations"
    
    if not brain_dir.exists() or not conv_dir.exists():
        logger.error("必要なディレクトリ (brain または conversations) が見つかりません。")
        return

    # 既存のZIPがあれば削除
    if zip_path.exists():
        try:
            zip_path.unlink()
        except Exception as e:
            logger.error(f"古いバックアップを削除できませんでした: {e}")
            return

    # バックアップ対象のUUIDを収集
    target_uuids = set()
    for d in brain_dir.iterdir():
        if d.is_dir() and len(d.name) == 36 and d.name.count('-') == 4:
            target_uuids.add(d.name)
            
    if not target_uuids:
        logger.warning("バックアップするチャット履歴が見つかりません。")
        return

    logger.info(f"{len(target_uuids)} 件のチャット履歴を圧縮中... (少々お待ちください)")
    
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for uuid in target_uuids:
                # 1. brain フォルダ (アーティファクト・ログ) の保存
                b_dir = brain_dir / uuid
                if b_dir.exists():
                    for filepath in b_dir.rglob('*'):
                        if filepath.is_file():
                            arcname = Path("brain") / filepath.relative_to(brain_dir)
                            zf.write(filepath, arcname)
                
                # 2. conversations フォルダ (チャットDB本体) の保存
                for ext in ['.db', '.pb']:
                    c_file = conv_dir / f"{uuid}{ext}"
                    if c_file.exists():
                        arcname = Path("conversations") / c_file.name
                        zf.write(c_file, arcname)
                        
        logger.info(f"バックアップ完了！保存先: {zip_path.name}")
        logger.info("※忘れずに移行先PCへ移動してください。")
    except Exception as e:
        logger.error(f"バックアップ中にエラーが発生しました: {e}")

def do_restore(zip_path, ide_dir):
    logger.info("復元処理を開始します...")
    
    if not zip_path.exists():
        logger.error(f"バックアップZIPが見つかりません: {zip_path.name}")
        return
        
    print("\n⚠️ 【最終確認】 復元を開始します。")
    print("※実行前に必ず Antigravity IDE を完全に終了させておいてください。")
    ans = input("実行しますか？ (y/n): ")
    if ans.lower() != 'y':
        logger.info("処理を中止しました。")
        return
        
    logger.info("バックアップを展開中... (既存データは上書きされます)")
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            # 古いバグのあるZIP形式（brain や conversations フォルダの階層がない）を弾く安全装置
            valid_format = any(info.filename.startswith("brain/") or info.filename.startswith("conversations/") for info in z.infolist())
            if not valid_format:
                logger.error("【重大なエラー】このZIPファイルは古い仕様で作成されており、チャット本体(DB)が含まれていません！")
                logger.error("元のPCで『最新の chat_sync_tool.py』を実行し、再度バックアップを取り直してください。")
                return
                
            # 展開先は ide_dir (.gemini/antigravity-ide)
            z.extractall(ide_dir)
            
        logger.info("展開が完了しました。")
        
        # ユーザー名書き換え処理 (パスの自動調整)
        current_user = os.environ.get("USERNAME", "user")
        brain_dir = ide_dir / "brain"
        
        logger.info("パス設定の最適化（ユーザー名の調整）を行っています...")
        if brain_dir.exists():
            for filepath in brain_dir.rglob('*'):
                if filepath.is_file() and filepath.suffix in ['.jsonl', '.md', '.json', '.txt']:
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        if "フォーレスト026" in content and current_user != "フォーレスト026":
                            content = content.replace("フォーレスト026", current_user)
                            with open(filepath, 'w', encoding='utf-8') as f:
                                f.write(content)
                    except Exception:
                        continue
                    
        logger.info("🎉 復旧完了！IDEを起動し、過去のチャットが表示されるか確認してください。")
    except Exception as e:
        logger.error(f"復元中にエラーが発生しました: {e}")

def main():
    print("="*60)
    print("🔄 Antigravity Chat Sync Tool (バックアップ＆復元ツール) - 厳格改修版")
    print("="*60)
    
    script_dir = Path(__file__).parent
    zip_path = script_dir / "Antigravity_ChatHistory_Backup.zip"
    ide_dir = get_ide_dir()
    
    print("\nどちらの操作を行いますか？")
    print("  [1] ⬆️ 現在のチャット履歴をすべてZIPにバックアップする")
    print("  [2] ⬇️ ZIPから履歴を復元する (UUID維持)")
    print("  [0] キャンセル")
    
    choice = input("\n番号を選択してください (1/2/0): ")
    
    if choice == '1':
        do_backup(zip_path, ide_dir)
    elif choice == '2':
        do_restore(zip_path, ide_dir)
    else:
        logger.info("キャンセルしました。")

if __name__ == '__main__':
    main()
