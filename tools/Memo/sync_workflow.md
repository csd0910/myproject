# 環境同期の手順（複数PC開発用）

別のPCで開発を続けたり、新しいライブラリを追加したりする際の標準的な流れをまとめます。

## 1. ライブラリを追加・更新したとき（現在のPCで実行）

新しいライブラリをインストール（例: `pip install pandas`）した後は、必ず以下の作業を行って設定ファイルを更新します。

1.  **ライブラリリストの更新**:
    ```powershell
    pip freeze > requirements.txt
    ```
2.  **Gitへのプッシュ**:
    `requirements.txt` を含めてコミットし、プッシュします。
    ```powershell
    git add requirements.txt
    git commit -m "Update libraries"
    git push origin main
    ```

## 2. 別のPCでそれを受け取るとき

別のPCで作業を開始する前に、最新の状態を反映させます。

1.  **最新コードの取得**:
    ```powershell
    git pull origin main
    ```
2.  **ライブラリの同期（インストール）**:
    仮想環境（.venv）が有効な状態で実行します。
    ```powershell
    pip install -r requirements.txt
    ```

---

## 開発の鉄則
-   **コード（.py）を書いたらプッシュする**
-   **ライブラリを入れたら `requirements.txt` もプッシュする**

この2つをセットで行うことで、どのPCでも「全く同じ環境」で開発を再開できます。
