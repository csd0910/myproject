import pandas as pd

def main():
    excel_path = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\20260427_ログ表示結果-20260416175217 - コピー.xlsx"
    csv_path = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\成川_ログ検索結果-20260404.csv"

    print("実データの読み込みを開始します...")

    try:
        df_master = pd.read_excel(excel_path, sheet_name='管理部提出用')
        # 成川社員のデータを抽出
        df_target_master = df_master[df_master['氏名'].str.contains('成川', na=False)].copy()
    except Exception as e:
        print(f"Excel読み込みエラー: {e}")
        return

    try:
        df_log = pd.read_csv(csv_path, encoding='shift_jis')
    except Exception as e:
        print(f"CSV読み込みエラー: {e}")
        return

    # --- 1. ログデータから「日付ごとの最初と最後の時間」を抽出 ---
    df_log['日時'] = pd.to_datetime(df_log['日時'])
    df_log['日付_log'] = df_log['日時'].dt.normalize() # 時刻を切り捨てて日付だけにする
    
    # 日ごとの PC電源ON(最小日時) と PC電源OFF(最大日時) を取得
    daily_log = df_log.groupby('日付_log').agg(
        PC電源ON=('日時', 'min'),
        PC電源OFF=('日時', 'max')
    ).reset_index()

    # --- 2. マスタデータ(Excel)とログを結合 ---
    df_target_master['日付_master'] = pd.to_datetime(df_target_master['日付'])
    merged_df = pd.merge(df_target_master, daily_log, left_on='日付_master', right_on='日付_log', how='left')

    print("\n========== 異常検知エンジン 判定結果 ==========")
    
    for index, row in merged_df.iterrows():
        date_str = row['日付_master'].strftime('%Y/%m/%d')
        
        # AA列相当：勤務日種別や事由（公休日、有休、テレワークなど）
        status = str(row.get('勤務日種別', ''))
        jiyu = str(row.get('事由', ''))
        shift_info = f"{status} {jiyu}".strip().replace('nan', '')
        
        # ログが存在するか
        has_log = not pd.isna(row['PC電源ON'])
        flags = []
        
        # ---------------------------------------------------------
        # 【検知ロジック1】サービス休日返上 / 有休中の稼働 (AA列の判定)
        # ---------------------------------------------------------
        if ('休' in shift_info) and has_log:
            flags.append(f"🚨【サービス休日稼働】シフトは「{shift_info}」ですがPCが稼働しています！")
            
        # ---------------------------------------------------------
        # 【検知ロジック2】テレワークなどの特殊勤務 (AA列の判定)
        # ---------------------------------------------------------
        if 'テレワーク' in shift_info and has_log:
            flags.append(f"ℹ️【テレワーク検知】社外からの稼働です。念のためログのIPアドレス等と突合を推奨します。")

        # ---------------------------------------------------------
        # 【検知ロジック3】サービス早出 ＆ サービス残業 (O列・L列との比較)
        # ---------------------------------------------------------
        if ('休' not in shift_info) and has_log:
            try:
                # O列相当(打刻・出勤) と L列相当(打刻・退勤)
                start_str = str(row.get('打刻・出勤', ''))
                end_str = str(row.get('打刻・退勤', ''))
                
                # 早出の判定 (O列 より G列(PC電源ON) が異常に早い場合)
                if start_str and start_str != 'nan' and start_str != 'NaT':
                    work_start = pd.to_datetime(f"{date_str} {start_str}")
                    # 10分以上早ければフラグを立てる (マージンは調整可能)
                    if row['PC電源ON'] < work_start - pd.Timedelta(minutes=10):
                        diff_m = int((work_start - row['PC電源ON']).total_seconds() / 60)
                        flags.append(f"⚠️【サービス早出】出勤打刻より {diff_m}分早く PCが起動({row['PC電源ON'].strftime('%H:%M')}) しています。")

                # サビ残の判定 (L列 より G列(PC電源OFF) が遅い場合)
                if end_str and end_str != 'nan' and end_str != 'NaT':
                    work_end = pd.to_datetime(f"{date_str} {end_str}")
                    if row['PC電源OFF'] > work_end + pd.Timedelta(minutes=10):
                        diff_m = int((row['PC電源OFF'] - work_end).total_seconds() / 60)
                        flags.append(f"⚠️【サビ残疑い】退勤打刻より {diff_m}分遅くまで PCが稼働({row['PC電源OFF'].strftime('%H:%M')}) しています。")
            except Exception as e:
                pass # 時刻が入っていない場合などはスキップ

        # 結果の出力
        print(f"\n[{date_str}] シフト: {shift_info}")
        if not flags and has_log:
            print("  ✅ 問題なし（適正な稼働と判定）")
        elif not has_log:
            print("  ➖ ログ記録なし")
        else:
            for f in flags:
                print(f"  {f}")

if __name__ == "__main__":
    main()
