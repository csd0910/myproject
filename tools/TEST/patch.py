import os

code = open('process_46_47_48.py', encoding='utf-8').read()

new_logic = '''        am_an_ao_text = f"{an_text} {ao_text}"

        low_voltage_cable_kws = ["usbケーブル", "usb ケーブル", "スマホケーブル", "リールケーブル", "充電ケーブル", "通信ケーブル", "変換ケーブル", "lanケーブル", "hdmiケーブル", "光ケーブル", "オーディオケーブル", "同軸ケーブル", "アンテナケーブル"]
        for kw in low_voltage_cable_kws:
            if kw in full_text:
                if any(x in full_text for x in ["電源ケーブル", "acケーブル", "電源コード", "acコード"]):
                    continue
                device_kws = ["ac式充電器", "ac充電器", "acアダプタ", "usb充電器", "コンセント充電器", "電源タップ", "oaタップ", "モバイルバッテリー", "リチウムイオン蓄電池"]
                if any(x in cat_text + " " + name_text for x in device_kws):
                    continue
                return pd.Series(["PSE対象外", "", "", "", f"低電圧・通信用ケーブルのため除外: {kw}", kw, 0])

        pse_exclude_kws = ["pse対象外", "pse 対象外", "認証不要", "認証が必要ない", "pse非対象", "非対象"]
        for kw in pse_exclude_kws:
            if kw in am_an_ao_text:
                return pd.Series(["PSE対象外", "", "", "", f"明記による除外: {kw}", kw, 0])

        if ("psマーク" in am_an_ao_text or "pseマーク" in am_an_ao_text) and "pse" in am_an_ao_text:
            return pd.Series(["PSE対象", "明記により確定", "", "", "明記による対象: PSマークの種類：PSE等", "PSマーク_PSE", 0])

        if "pse" in am_an_ao_text and "適合" in am_an_ao_text:
            return pd.Series(["PSE対象", "明記により確定", "", "", "明記による対象: PSE適合関連（記述/技術基準適合等）", "pse_適合", 0])

        pse_include_kws = ["pse対応", "pse認証取得", "pseマーク取得", "pseマーク付", "pse取得", "pse適合", "pseマーク"]
        for kw in pse_include_kws:
            if kw in am_an_ao_text:
                return pd.Series(["PSE対象", "明記により確定", "", "", f"明記による対象: {kw}", kw, 0])
'''

if 'low_voltage_cable_kws' not in code:
    code = code.replace('        ao_exclude_kws = ["医療機器",', new_logic + '\n        ao_exclude_kws = ["医療機器",')

old_dc = 'return pd.Series(["PSE対象外", "", "", "", f"品目「{m[\'pse_item_name\']}」だがDC駆動", kw, 1])'
new_dc = '''if any(k in str(m['pse_item_name']) for k in ["リチウムイオン蓄電池", "モバイルバッテリー"]):
                            return pd.Series(["PSE対象", m["pse_type"], m["pse_category"], m["pse_item_name"], f"対象品目「{m['pse_item_name']}」に一致（リチウムイオン蓄電池はDC駆動でも対象）", kw, 1])
                        return pd.Series(["PSE対象外", "", "", "", f"品目一致「{m['pse_item_name']}」だがDC駆動のため対象外", kw, 1])'''
if 'リチウムイオン蓄電池' not in code and old_dc in code:
    code = code.replace(old_dc, new_dc)

with open('process_46_47_48.py', 'w', encoding='utf-8') as f:
    f.write(code)
print('Patched process_46_47_48.py')
