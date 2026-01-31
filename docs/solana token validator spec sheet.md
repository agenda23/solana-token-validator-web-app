
## 1. 要件定義書 (Requirements Definition)

### **【目的】**

Solana上のMemeコインのコントラクトアドレス（CA）を入力するだけで、市場の厚み（流動性・時価総額）と安全性（権限設定・詐欺リスク）を即座に判定し、投資判断をサポートする。

### **【機能要件】**

1. **CA/URL検索機能:** ユーザーがSolanaのCA、またはDEXScreener等のURLを入力し、解析を開始する。URLからのCA自動抽出機能を含む。入力後はフォームを自動クリアし、連続入力に対応する。
    
2. **トークン基本情報表示:** 検索結果の冒頭に、トークン名、シンボル、およびロゴ画像を表示し、即座に対象を特定できるようにする。
    
3. **履歴管理機能:** 解析結果をセッション内で保持し、新しい結果を常にリストの最上部に表示する。
    
4. **個別削除機能:** 解析結果ごとに削除ボタン（❌）を設け、不要な情報を個別に消去可能とする。
    
5. **市場データ解析:** 時価総額(MC/FDV)、流動性(Liquidity)、SNS情報を表示。複数のペアが存在する場合、最も流動性の高いペアを優先して表示する。
    
6. **セキュリティ診断:** ハニーポット判定、Mint権限（追加発行）、Freeze権限（取引停止）の有無、LPのBurn状況を判定。
    
7. **コミュニティリンク抽出:** 公式公式サイト、公式X(Twitter)、Telegramへのリンクを表示。
    
8. **補足データ表示:** 価格変化率（24時間）、取引数（buy/sell）、ペア作成日時を表示。情報の透明性を高めるため、データ取得日時を併記する。
    
9. **総合判定（ランク付け）:** セキュリティと市場流動性を加味したスコアリングに基づき、「S・B・F」の3段階で評価。結果は展開された状態で表示される。
    

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

1. `st.session_state` を用いた解析履歴の保持ロジックの実装。
2. `on_change` コールバックを用いた入力フォームの自動クリア機能の実装。
3. カード型UI（`st.container`）を用いた、展開済み状態での結果表示と削除ボタンの実装。
4. `st.metric` を用いた主要数値の表示。

### **Step 4: テスト**

1. 連続して異なるCAを入力し、新しい順に履歴が積み上がるか。
2. 個別削除ボタンで対象のカードが消去されるか。
3. 既知のラグプル、ハニーポット案件のCAでF判定が出るか。

---

## 4. プロトタイプコード (`app.py`)

```python
import streamlit as st
import requests
import re
from datetime import datetime
import uuid

# --- 補助関数: CAの抽出 ---
def extract_ca(input_text):
    pattern = r'[1-9A-HJ-NP-Za-km-z]{32,44}'
    match = re.search(pattern, input_text)
    return match.group(0) if match else None

# --- データ取得ロジック ---
def get_data(ca):
    try:
        dex_url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        dex_res = requests.get(dex_url, timeout=10).json()
        goplus_url = f"https://api.gopluslabs.io/api/v1/solana/token_security?contract_addresses={ca}"
        go_res = requests.get(goplus_url, timeout=10).json()
        return dex_res, go_res
    except Exception as e:
        return None, None

# --- 判定スコアリング ---
def calculate_safety(dex_data, go_data, ca):
    score = 100
    details = []
    results = go_data.get('result', {})
    sec = results.get(ca) or results.get(ca.lower()) or {}
    
    pair = None
    if dex_data.get('pairs'):
        pair = max(dex_data['pairs'], key=lambda x: x.get('liquidity', {}).get('usd', 0))
    if not pair: return None, None, None, None

    # セキュリティチェック
    if sec.get('is_honeypot') == '1':
        score -= 100
        details.append("❌ ハニーポットの疑いあり")
    if sec.get('mintable', {}).get('status') == '1':
        score -= 50
        details.append("⚠️ Mint権限が有効")
    if sec.get('freezable', {}).get('status') == '1':
        score -= 40
        details.append("⚠️ Freeze権限が有効")
        
    # LP Burn判定
    lp_burned = False
    if 'pairAddress' in pair:
        pair_address = pair['pairAddress']
        for g_dex in sec.get('dex', []):
            if g_dex.get('id') == pair_address:
                if float(g_dex.get('burn_percent', 0)) > 95:
                    lp_burned = True
                    break
    if lp_burned: score += 10
    else: score -= 20; details.append("⚠️ LP未焼却（Rugpull）")

    return score, details, pair, lp_burned

# --- セッション管理とUI表示 ---
if 'results' not in st.session_state: st.session_state.results = []

def on_input_change():
    input_text = st.session_state.ca_input_val
    ca = extract_ca(input_text)
    if ca:
        dex, go = get_data(ca)
        if dex and dex.get("pairs"):
            score, warnings, pair, is_lp_burned = calculate_safety(dex, go, ca)
            if pair:
                res_obj = {
                    "id": str(uuid.uuid4()), "ca": ca, "score": score, 
                    "warnings": warnings, "pair": pair, "is_lp_burned": is_lp_burned, 
                    "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                st.session_state.results.insert(0, res_obj)
    st.session_state.ca_input_val = ""

st.set_page_config(page_title="Solana Validator Pro", layout="centered", page_icon="🛡️")
st.title("🛡️ Solana Token Validator Pro")

st.text_input("Contract Address / DEXScreener URL", key="ca_input_val", on_change=on_input_change)

for i, res in enumerate(st.session_state.results):
    with st.container(border=True):
        pair = res["pair"]
        base_token = pair.get('baseToken', {})
        st.subheader(f"{base_token.get('name')} ({base_token.get('symbol')})")
        if st.button("❌", key=f"del_{res['id']}"):
            st.session_state.results.pop(i)
            st.rerun()
        # (判定結果・メトリクス等の表示ロジック...)
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

---

## 6. 付録: DEXScreener API 参考資料 (Reference)

### **【主要な取得フィールド】**

| **階層 / フィールド** | **内容** | **用途** |
| :--- | :--- | :--- |
| **`pairs[]`** | トークンが上場している各市場（ペア）のリスト。 | 複数市場からのデータ集計。 |
| ├ **`baseToken.name`** | トークンの正式名称。 | **[要件2]** ヘッダー表示。 |
| ├ **`baseToken.symbol`** | トークンのシンボル（銘柄名）。 | **[要件2]** ヘッダー表示。 |
| ├ **`priceChange`** | 5分/1時間/6時間/24時間の価格変化。 | **[要件6]** 補足データ表示。 |
| ├ **`txns`** | 売買件数。 | **[要件6]** 補足データ表示。 |
| ├ **`pairCreatedAt`** | ペアが作成された日時（Unix Time）。 | **[要件6]** 市場の歴史の確認。 |
| ├ **`liquidity.usd`** | プール内の総流動性（USD）。 | 市場の厚みの判定に使用。 |
| ├ **`fdv`** | 完全希薄化時価総額（FDV）。 | トークンの規模評価に使用。 |
| └ **`info`** | 開発者が設定した各種情報。 | |
| 　 ├ **`imageUrl`** | トークンのロゴ画像URL。 | **[要件2]** UIでのアイコン表示。 |
| 　 ├ **`websites[]`** | 公式サイトのURLとラベルのリスト。 | コミュニティリンク抽出。 |
| 　 └ **`socials[]`** | X(Twitter), Telegram等のSNSリンク。 | コミュニティリンク抽出。 |

### **【利用上の注意点】**
- **複数ペアの存在:** 一つのCAに対してRaydiumやOrcaなど複数のペアが返されるため、必ず `liquidity.usd` が最大のペアを特定して計算に利用する必要があります。
- **データの鮮度:** APIはキャッシュされている場合があるため、超短期の価格変動よりも、時価総額や流動性といったファンダメンタルデータの取得に適しています。
- **SNS情報の有無:** 新規作成直後のトークンには `info` フィールドが存在しない場合があるため、コード内での `None` チェックが必須です。