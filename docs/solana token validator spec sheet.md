
## 1. 要件定義書 (Requirements Definition)

### **【目的】**

Solana上のMemeコインのコントラクトアドレス（CA）を入力するだけで、市場の厚み（流動性・時価総額）と安全性（権限設定・詐欺リスク）を即座に判定し、投資判断をサポートする。

### **【機能要件】**

1. **CA/URL検索機能:** ユーザーがSolanaのCA、またはDEXScreener等のURLを入力し、解析を開始する。URLからのCA自動抽出機能を含む。
    
2. **市場データ解析:** 時価総額(MC/FDV)、流動性(Liquidity)、SNS情報を表示。複数のペアが存在する場合、最も流動性の高いペアを優先して表示する。
    
3. **セキュリティ診断:** ハニーポット判定、Mint権限（追加発行）、Freeze権限（取引停止）の有無、LPのBurn状況を判定。
    
4. **コミュニティリンク抽出:** 公式X(Twitter)、公式サイト、Telegramへのリンクを表示。
    
5. **総合判定（ランク付け）:** セキュリティと市場流動性を加味したスコアリングに基づき、「S・B・F」の3段階で評価。
    

### **【非機能要件】**

- **レスポンス速度:** 検索から3秒以内に結果を表示。
    
- **保守性:** スクレイピングを避け、公式API（DEXScreener, GoPlus）を最優先で利用する。
    

---

## 2. 開発仕様書 (Development Specification)

### **【技術スタック】**

- **言語:** Python 3.10+
    
- **UIフレームワーク:** Streamlit (データダッシュボードに最適)
    
- **使用API:**
    
    - **DEXScreener API:** トークン価格、時価総額、流動性、SNS情報。
        - Endpoint: `https://api.dexscreener.com/latest/dex/tokens/{ca}`
        
    - **GoPlus Security API:** Solanaトークンの安全性チェック。
        - Chain ID: `1399811149` (Solana)
        - Endpoint: `https://api.gopluslabs.io/api/v1/solana/token_security?contract_addresses={ca}`
        

### **【判定アルゴリズム】**

投資リスクを最小化するための判定基準。

|**項目**|**加点/減点条件**|**リスク内容**|
|---|---|---|
|**Honeypot**|検出時 -100点 (即座にF判定)|売却不可能な詐欺プログラム|
|**Mint Authority**|`mintable['status'] == '1'` 時 -50点|トークンの無限増殖による暴落リスク|
|**Freeze Authority**|`freezable['status'] == '1'` 時 -40点|運営による取引凍結リスク|
|**Liquidity**|$50,000未満時 -20点|流動性不足による売却難（スリップページ）|
|**LP Burned**|`burn_percent > 95%` (加点要素)|運営による流動性引き抜き（Rugpull）の防止|

---

## 3. 開発手順書 (Development Steps)

### **Step 1: 環境構築**

1. Pythonをインストール。
    
2. 必要なライブラリをインストール。
    
    ```bash
    pip install streamlit requests pandas
    ```
    

### **Step 2: API連携とロジックの実装**

1. CA抽出用の正規表現ロジックの実装。
2. DEXScreener APIから最大流動性ペアを取得する関数の作成。
3. GoPlus API (`/v1/solana/token_security`) からセキュリティ情報を取得し、スコアリングする関数の作成。

### **Step 3: UIの実装**

1. `st.status` を用いた解析プロセスの可視化。
2. `st.metric` を用いた主要数値の表示。
3. 判定結果に基づいた警告メッセージの表示（`st.warning`, `st.error`）。

### **Step 4: テスト**

1. 既知のラグプル、ハニーポット案件のCAでF判定が出るか。
2. Bluechip（検証済みトークン）でS判定が出るか。

---

## 4. プロトタイプコード (`app.py`)

```python
import streamlit as st
import requests
import re

# --- 補助関数: CAの抽出 ---
def extract_ca(input_text):
    # SolanaのCA（Base58で32-44文字）を正規表現で抽出
    pattern = r'[1-9A-HJ-NP-Za-km-z]{32,44}'
    match = re.search(pattern, input_text)
    return match.group(0) if match else None

# --- データ取得ロジック ---
def get_data(ca):
    # 1. Market Data (DEXScreener)
    dex_url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
    dex_res = requests.get(dex_url).json()
    
    # 2. Security Data (GoPlus - Solana Specialized Endpoint)
    goplus_url = f"https://api.gopluslabs.io/api/v1/solana/token_security?contract_addresses={ca}"
    go_res = requests.get(goplus_url).json()
    
    return dex_res, go_res

# --- 判定スコアリング ---
def calculate_safety(dex_data, go_data, ca):
    score = 100
    details = []
    
    # GoPlusのレスポンスは小文字のアドレスをキーに持つ
    results = go_data.get('result', {})
    sec = results.get(ca) or results.get(ca.lower()) or {}
    
    pair = None
    if dex_data.get('pairs'):
        # 流動性が最大のペアを選択
        pair = max(dex_data['pairs'], key=lambda x: x.get('liquidity', {}).get('usd', 0))
    
    # セキュリティチェック項目 (Solana固有の構造)
    if sec.get('is_honeypot') == '1':
        score -= 100
        details.append("❌ ハニーポットの疑いあり")
        
    if sec.get('mintable', {}).get('status') == '1':
        score -= 50
        details.append("⚠️ Mint権限が有効（追加発行リスク）")
        
    if sec.get('freezable', {}).get('status') == '1':
        score -= 40
        details.append("⚠️ Freeze権限が有効（取引停止リスク）")
        
    # LP Burnチェック (DEXScreenerまたはGoPlusのデータを使用)
    burn_pct = 0
    if pair and 'liquidity' in pair:
        # DEXScreenerのペア情報からBurn情報を推測することもあるが、
        # ここではGoPlusのデータがあれば優先
        pass
    
    # 市場データチェック項目
    liquidity = pair.get('liquidity', {}).get('usd', 0) if pair else 0
    if liquidity < 50000:
        score -= 20
        details.append(f"⚠️ 流動性が低い (${liquidity:,.0f})")
    
    return score, details, pair

# --- UI設定 ---
st.set_page_config(page_title="Solana Safety Checker Pro", layout="centered")
st.title("🛡️ Solana Meme Checker Pro")

input_text = st.text_input("CAまたはDEXScreenerのURLを入力してください:")
ca = extract_ca(input_text) if input_text else None

if ca:
    with st.status("データを解析中...", expanded=True) as status:
        dex, go = get_data(ca)
        if dex.get("pairs"):
            score, warnings, pair = calculate_safety(dex, go, ca)
            status.update(label="解析完了！", state="complete", expanded=False)
            
            # 結果表示
            st.subheader(f"判定結果: {'🟢 S' if score >= 80 else '🟡 B' if score >= 50 else '🔴 F'} ランク")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("時価総額 (FDV)", f"${pair.get('fdv', 0):,.0f}")
                st.metric("流動性 (USD)", f"${pair.get('liquidity', {}).get('usd', 0):,.0f}")
            
            with col2:
                st.write("**安全性チェック:**")
                if not warnings:
                    st.success("重大なリスクは見つかりませんでした")
                for w in warnings:
                    st.warning(w)
            
            # ソーシャルリンク
            if pair.get('info', {}).get('socials'):
                st.write("---")
                cols = st.columns(len(pair['info']['socials']))
                for i, social in enumerate(pair['info']['socials']):
                    cols[i].link_button(social['type'].capitalize(), social['url'])
        else:
            status.update(label="エラー", state="error")
            st.error("トークン情報が見つかりませんでした。CAが正しいか、上場しているか確認してください。")
```


---

## 5. インフラ構成とデプロイ (Infrastructure)

### **Streamlit Community Cloud (推奨)**

GitHubと連携するだけで、無料でスマホからも利用可能なWebアプリとして公開できます。

1. GitHubリポジトリを作成し、`app.py` と `requirements.txt` をアップロード。
2. `requirements.txt` には以下を記述：
   ```text
   streamlit
   requests
   pandas
   ```
3. [share.streamlit.io](https://share.streamlit.io/) でアプリをデプロイ。