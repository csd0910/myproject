import sys
with open('Bounce_Detailed_Analyzer_V2_API.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_func = """def analyze_bounce_emails(
    input_path: str,
    output_path: str = None,
    start_date: datetime.datetime = None,
    end_date: datetime.datetime = None,
) -> str:
    if not output_path:
        base_dir = (
            os.path.dirname(sys.executable)
            if getattr(sys, "frozen", False)
            else os.path.dirname(os.path.abspath(__file__))
        )
        output_path = os.path.join(base_dir, "Detailed_Bounce_Analysis_V2.xlsx")

    # ── ヘッダー表示 ─────────────────────────────────────────
    print("\\n" + "=" * 62)
    print("  バウンスメール解析スクリプト  完全統合版 v2 (API連携・Pandas版)")
    print("=" * 62)
    print(f"  入力 : {input_path}")
    print(f"  出力 : {output_path}")
    if start_date:
        end_label = end_date.strftime("%Y-%m-%d") if end_date else "（上限なし）"
        print(f"  期間 : {start_date.strftime('%Y-%m-%d')} ～ {end_label}")
    print("-" * 62)

    print("  [1/4] メール件数を確認中...", end="", flush=True)
    total_count = _count_messages(input_path)
    print(f" {total_count:,} 件")

    all_rows = []
    total = analyzed = skipped_period = skipped_nobounce = errors = 0

    print("  [2/4] 正規表現・RFC解析中 (Pandas利用)...", flush=True)
    bar_fmt = "  {l_bar}{bar}| {n_fmt}/{total_fmt} 通 [経過:{elapsed} 残:{remaining} 速度:{rate_fmt}]"
    
    with tqdm(_load_messages(input_path), total=total_count or None, unit="通", bar_format=bar_fmt, ncols=80, colour="cyan", dynamic_ncols=True) as pbar:
        for message in pbar:
            total += 1
            try:
                row_data = analyze_single_message(message)
                if row_data is None:
                    skipped_nobounce += 1
                    continue
                    
                dt_obj = row_data.get("_dt_obj")
                if dt_obj:
                    if dt_obj.tzinfo is None:
                        dt_obj = dt_obj.replace(tzinfo=datetime.timezone.utc)
                    if start_date and dt_obj < start_date:
                        skipped_period += 1
                        continue
                    if end_date and dt_obj > end_date:
                        skipped_period += 1
                        continue

                all_rows.append(row_data)
                analyzed += 1
                
                addr_disp = (row_data.get("バウンス先(宛先)") or "?")[:28]
                pbar.set_postfix_str(f"✓{analyzed}件 | {addr_disp}", refresh=False)
            except Exception as e:
                errors += 1
                if errors <= 5:
                    tqdm.write(f"  [Warning] 解析エラー: {e}")

    if not all_rows:
        print("\\nバウンスメールが見つかりませんでした。")
        return ""

    df = pd.DataFrame(all_rows)

    print("\\n  [3/4] AI 判定プロセス (Otherカテゴリ抽出・ユニーク化)...", flush=True)
    df["_raw_reason"] = df["詳細診断コード (Diagnostic-Code)"].replace("", pd.NA)
    df["_raw_reason"] = df["_raw_reason"].fillna(df["本文抜粋(一部)"].str[:200])
    df["_raw_reason"] = df["_raw_reason"].astype(str).fillna("").str.strip()
    
    unique_reasons = df[df["ブロック分類"] == "Other"]["_raw_reason"].unique()
    unique_reasons = [r for r in unique_reasons if r]
    
    ai_results = {}
    if len(unique_reasons) > 0:
        ai_results = analyze_with_gemini(unique_reasons)
    else:
        print("  [AI] Otherカテゴリのエラーなし。API実行をスキップします。")

    def _map_cause(row):
        cat = row["ブロック分類"]
        if cat == "Other":
            return ai_results.get(row["_raw_reason"], {}).get("cause", "")
        return ErrorClassifier.EXPLANATIONS.get(cat, {}).get("desc", "")

    def _map_action(row):
        cat = row["ブロック分類"]
        if cat == "Other":
            return ai_results.get(row["_raw_reason"], {}).get("action", "")
        return ErrorClassifier.EXPLANATIONS.get(cat, {}).get("action", "")

    df["AI推定原因"] = df.apply(_map_cause, axis=1)
    df["推奨対応(AI/定型)"] = df.apply(_map_action, axis=1)

    print("\\n  [4/4] 3シート構成のExcelファイルを作成中...", flush=True)
    out_cols = [c for c in HEADERS if c in df.columns]
    df_out = df[out_cols]
    
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df_out.to_excel(writer, index=False, sheet_name="All_Data")
        ws = writer.sheets["All_Data"]
        
        _apply_header_style(ws)
        for i, w in enumerate(COL_WIDTHS, 1):
            if i <= ws.max_column:
                ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w

        for row_idx, data_dict in enumerate(all_rows, start=2):
            merged_dict = {
                **data_dict,
                "AI推定原因": df.iloc[row_idx-2]["AI推定原因"],
                "推奨対応(AI/定型)": df.iloc[row_idx-2]["推奨対応(AI/定型)"]
            }
            _apply_cell_style(ws, row_idx, merged_dict)

        ws_sum = writer.book.create_sheet("Summary")
        ws_sum.append(["カテゴリー", "件数", "届かなかった理由の説明(定型)", "推奨される対応(定型)"])
        for cell in ws_sum[1]:
            cell.font = HEADER_FONT
            cell.fill = HEADER_FILL
            
        cat_counts = df["ブロック分類"].value_counts().to_dict()
        for cat, cnt in sorted(cat_counts.items(), key=lambda x: -x[1]):
            info = ErrorClassifier.EXPLANATIONS.get(cat, {"desc": "-", "action": "-"})
            ws_sum.append([cat, cnt, info["desc"], info["action"]])
            fill = COLORS.get(cat)
            if fill:
                for cell in ws_sum[ws_sum.max_row]:
                    cell.fill = fill
                    
        ws_sum.column_dimensions["A"].width = 25
        ws_sum.column_dimensions["C"].width = 50
        ws_sum.column_dimensions["D"].width = 50

        ws_ai = writer.book.create_sheet("AI_Other_Report")
        ws_ai.append(["原文(Raw_Reason)", "AI推定原因", "推奨アクション"])
        for cell in ws_ai[1]:
            cell.font = HEADER_FONT
            cell.fill = HEADER_FILL

        if ai_results:
            for reason, detail in ai_results.items():
                ws_ai.append([reason, detail.get("cause", ""), detail.get("action", "")])
            
        ws_ai.column_dimensions["A"].width = 60
        ws_ai.column_dimensions["B"].width = 40
        ws_ai.column_dimensions["C"].width = 50

    print("\\n" + "=" * 62)
    print("  ▼ 解析完了サマリー")
    print("-" * 62)
    print(f"  処理したメール総数  : {total:>6,} 通")
    print(f"  バウンス検出数      : {analyzed:>6,} 件  ← Excelに出力")
    print(f"  期間外スキップ      : {skipped_period:>6,} 件")
    print(f"  非バウンススキップ  : {skipped_nobounce:>6,} 件")
    print(f"  解析エラー          : {errors:>6,} 件")
    print("-" * 62)
    print("  ▼ カテゴリ別集計")
    for cat, cnt in sorted(cat_counts.items(), key=lambda x: -x[1]):
        if cnt > 0:
            bar_len = min(30, int(cnt / max(analyzed, 1) * 30))
            bar_str = "█" * bar_len + "░" * (30 - bar_len)
            pct     = cnt / analyzed * 100 if analyzed else 0
            print(f"  {cat:<25s} {cnt:>4,} 件 ({pct:5.1f}%) |{bar_str}|")
    print("=" * 62)
    print(f"  出力ファイル: {output_path}")
    print("=" * 62 + "\\n")
    return output_path
"""

# replace lines 942-1104
new_lines = new_func.splitlines(True)
if not new_lines[-1].endswith('\\n'):
    new_lines[-1] += '\\n'

lines = lines[:942] + new_lines + lines[1105:]

with open('Bounce_Detailed_Analyzer_V2_API.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Patching successful")
