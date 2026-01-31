# Solana Token Validator 開発ウォークスルー

このドキュメントでは、`docs/solana token validator spec sheet.md` に基づいたアプリケーションの開発およびデプロイの手順を分かりやすく解説します。

## 1. プロジェクトの構造
最終的なファイル構成は以下のようになります。

```text
solana-token-validator/
├── app.py              # アプリケーションのメインロジック
├── requirements.txt    # 必要なライブラリの一覧
└── docs/               # 仕様書およびドキュメント
    ├── solana token validator spec sheet.md
    └── walkthrough.md
```

## 2. 実装のポイント

### CAの自動抽出 (`extract_ca`)
ユーザーがDEXScreenerのURL（例: `https://dexscreener.com/solana/4vM6f...`）を入力しても、正規表現を使ってコントラクトアドレス（CA）だけを抽出します。これにより、ユーザーはURLをコピー＆ペーストするだけで済みます。

### 最大流動性ペアの選択
DEXScreener APIでは、1つのトークンに対して複数のDEX（Raydium, Orca等）のペアが返されることがあります。本アプリでは、その中から最も流動性（Liquidity）が高いものを自動的に選んで表示することで、より正確な市場価格と安全性を判定します。

### 安全性スコアリングロジック
GoPlus Security APIを利用し、以下の3つの致命的なリスクをチェックします。
1. **ハニーポット:** 購入できても売却できない、最も危険な詐欺。
2. **Mint権限:** 開発者が後から無限にトークンを発行できるリスク。
3. **Freeze権限:** 開発者が特定のユーザー、または全ユーザーの取引を止めるリスク。

これらに加え、流動性が $50,000 未満の場合も警告を出し、「S/B/F」の3ランクで投資判断を支援します。

## 3. セットアップ手順

### ローカルでの実行
1. Pythonをインストールします。
2. ターミナルで以下のコマンドを実行してライブラリをインストールします。
   ```bash
   pip install streamlit requests pandas
   ```
3. アプリを起動します。
   ```bash
   streamlit run app.py
   ```

### Webへの公開 (Streamlit Community Cloud)
1. GitHubに新しいリポジトリを作成します。
2. `app.py` と `requirements.txt` をアップロードします。
3. [Streamlit Community Cloud](https://share.streamlit.io/) にログインし、GitHubリポジトリを選択して「Deploy」をクリックします。
4. 数分で `https://xxx.streamlit.app` のようなURLでアプリが公開されます。

## 4. 今後の拡張アイデア
- **ホルダー分布の可視化:** 上位ホルダーが何％のシェアを持っているかを表示。
- **LP Lock確認:** 流動性がロックされている期間を表示。
- **履歴機能:** 過去に調べたトークンの履歴をブラウザに保存。
