# PCメーカー別初期設定差分の網羅抽出および自動設定ツール化 計画書

## 1. プロジェクトの目的（Executive Summary）
社内PCリプレイス（HP、富士通、Dell等）において、メーカーごとにプリインストールされている初期設定、独自サービス、電源プランの差異に起因するキッティングの手戻りを解消する。
各社の初期レジストリの差分を「軽量分割抽出スクリプト」によって完全に可視化（エビデンス化）し、それをもとに1つのスクリプトで全メーカーを自動判定・社内標準設定へコンバートする自動設定ツールを開発・実装する。

## 2. 原因と解決策の構造化（Why & How）
*   **【原因】** メーカー各社がWindowsの標準レジストリ（SOFTWARE / SYSTEM / Services）に、独自の初期値やバックグラウンド制御サービス、ハードウェア制御シグネチャを個別に埋め込んでいるため。
*   **【解決策】** 本環境上にデータ収集および判定ロジックを集約。クレンジング処理を挟んだカテゴリ別スクリプトにより「純粋な設定値」のみを抽出し、差分ベースの自動切り替えツールを構築する。

**フェーズ進行**
*   **【Phase 1: 基礎データ（エビデンス）収集】**：各社実機ログ取得・軽量化保存
*   **【Phase 2: 差分分析・ロジック構築】**：メーカー差分の特定・社内標準ポリシーとの整合性チェック
*   **【Phase 3: 自動設定ツールの実装・検証】**：判定・適用コード一元化、テスト端末での適用検証

## 3. 網羅すべき調査対象領域（100点のためのエビデンス資産）
大容量化を防ぐフィルタリングを施した上で、以下の8領域からエビデンスを取得します。

| ファイル名 | レジストリ階層（スコープ）等 | 調査・制御の目的 |
| :--- | :--- | :--- |
| `00_PC_Info.txt` | `Win32_ComputerSystem` | ツールの分岐トリガーとなるメーカー・モデル名の取得 |
| `01_CU_ControlPanel.txt` | `HKCU:\Control Panel` | マウス、キーボード、ディスプレイ等のユーザー基本環境 |
| `02_CU_Windows_Core.txt` | `HKCU:\Software\Microsoft\Windows` | ユーザープロファイル依存のWindowsコア挙動 |
| `03_CU_Policies.txt` | `HKCU:\SOFTWARE\Policies` | グループポリシー（ユーザー構成）の適用状況確認 |
| `04_LM_Policies.txt` | `HKLM:\SOFTWARE\Policies` | グループポリシー（コンピューター構成）、セキュリティ設定 |
| `05_LM_Startup_Run.txt` | `HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run` 等 | 起動時に常駐するメーカー製不要ユーティリティのあぶり出し |
| `06_LM_System_Control.txt` | `HKLM:\SYSTEM\CurrentControlSet\Control` | 電源プラン、高速スタートアップ、デバイス制御（最重要） |
| `07_LM_Services.txt` | `HKLM:\SYSTEM\CurrentControlSet\Services` | メーカー固有のバックグラウンドサービスの稼働状況 |
| `08_LM_Manufacturer_Apps.txt` | `HKLM:\SOFTWARE` (※Microsoft/Classes除外) | HP、富士通、Dell等が独自に埋め込む制御設定 |

## 4. 隠れた3つのリスクと対策（Risk Management）
*   **OS破損・BSoD（起動不可）リスク**：自動設定ツール側での処理は「値の追加」または「変更」に限定し、強制削除は原則行わない。
*   **Windows Updateによる先祖返りリスク**：コードを「メーカー判定」と「設定適用」に分離したモジュール型で記述し保守性を高める。
*   **ハードウェア（BIOS）レベルでの強制制御の罠**：レジストリ制御不可な場合はBIOS値変更手順を標準マニュアルに逆流させる。

## 5. 前提条件の検証（超堅牢システムアーキテクチャ）
GPOで代替可能な設定項目に関しては、直接レジストリを叩くのではなく、LGPO.exe等の公式ツールと連携させ、定義ファイルを流し込むハイブリッド構成を採用する。

## 6. 自動キッティングツールのプロトタイプ設計
```powershell
# ====================================================================
# AntiGravity Deployment Target: Set-CorporateStandardEnvironment.ps1
# ====================================================================

# [1] プラットフォームの環境（メーカー）判定
$Manufacturer = (Get-CimInstance Win32_ComputerSystem).Manufacturer
Write-Output "Detecting Manufacturer: $Manufacturer"

# [2] 全社共通ポリシーの流し込み（GPO/共通レジストリ）
function Set-CommonPolicy {
    Write-Output "Applying Global Corporate Policies..."
    # 例: UACの強制、Windows Updateの最適化等
}

# [3] メーカー別の差分吸収処理（Switch分岐）
function Set-ManufacturerSpecificPolicy {
    switch -wildcard ($Manufacturer) {
        "*HP*" { Write-Output "Optimizing HP ProDesk Environment..." }
        "*Fujitsu*" { Write-Output "Optimizing Fujitsu FMV Environment..." }
        "*Dell*" { Write-Output "Optimizing Dell OptiPlex Environment..." }
        Default { Write-Warning "Unknown Manufacturer." }
    }
}

Set-CommonPolicy
Set-ManufacturerSpecificPolicy
```

## 7. 新規PC（別機種）導入時のレジストリチューニング手順
今後、新しいメーカーや異なる機種のPCを導入した際、既存の自動キッティングスクリプトに「その機種専用の最適な設定（チューニング）」を吸収させるための標準運用手順です。

### Step 1: 初期状態（Before）のレジストリ取得
1. 新機種PCの初期セットアップ（OOBE）を完了させ、デスクトップを表示する。
2. 何も設定を変更せずに `Get-PCRegistryEvidence.ps1` （レジストリ抽出スクリプト）を実行し、初期状態のレジストリ群（`Before_XXXX`）をエクスポートする。

### Step 2: 手動での理想環境の構築
1. 実際に利用するユーザー（または `SysAdmin` 等）でログインする。
2. Windowsの「設定」やコントロールパネルから、マウス速度、電源オプション、視覚効果、タスクバー設定などを手動で**理想の状態（社内標準設定）**へ変更する。
3. （※メーカー独自の不要な常駐ソフトやスタートアップがあれば、この時点で停止・無効化しておく）

### Step 3: 設定変更後（After）のレジストリ取得
1. 手動でのチューニングがすべて完了した状態で、再度 `Get-PCRegistryEvidence.ps1` を実行し、変更後のレジストリ群（`After_XXXX`）をエクスポートする。

### Step 4: 差分解析とスクリプトへの組み込み（AIとの連携）
1. 取得した「Before」と「After」のデータ（または比較ツール `diff_reg.ps1` で出力した差分結果）を、AIアシスタント（本チャット等）へ共有・提示する。
2. その際、「どの設定が手動で直した箇所か」「どの設定が前回のスクリプトで効かなかったか」を伝達する。
3. AI側で差分データを解析し、そのメーカー・機種特有の特殊なレジストリキー（例：高精度タッチパッドの独自キー、OEMの電源管理機構など）をピンポイントで特定する。
4. マスターツール（`Set-CorporateStandardEnvironment.ps1`）のメーカー判定ロジック（`$Manufacturer` 分岐）にその機種専用のチューニングコードとして追記・アップデートさせる。
