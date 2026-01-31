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
        # Market Data
        dex_url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
        dex_res = requests.get(dex_url, timeout=10).json()
        
        # Security Data
        goplus_url = f"https://api.gopluslabs.io/api/v1/solana/token_security?contract_addresses={ca}"
        go_res = requests.get(goplus_url, timeout=10).json()
        
        return dex_res, go_res
    except Exception as e:
        st.error(f"データ取得中にエラーが発生しました: {e}")
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
    
    if not pair:
        return None, None, None, None

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
    
    if lp_burned:
        score += 10
    else:
        score -= 20
        details.append("⚠️ LP未焼却（Rugpullリスク）")
    
    liquidity = pair.get('liquidity', {}).get('usd', 0)
    if liquidity < 50000:
        score -= 20
        details.append(f"⚠️ 流動性が低い (${liquidity:,.0f})")
    
    return score, details, pair, lp_burned

# --- セッション状態の初期化 ---
if 'results' not in st.session_state:
    st.session_state.results = []

# --- 入力処理コールバック ---
def on_input_change():
    input_text = st.session_state.ca_input_val
    if not input_text:
        return
        
    ca = extract_ca(input_text)
    if ca:
        with st.spinner(f"CA: {ca} を解析中..."):
            dex, go = get_data(ca)
            if dex and dex.get("pairs"):
                score, warnings, pair, is_lp_burned = calculate_safety(dex, go, ca)
                if pair:
                    res_obj = {
                        "id": str(uuid.uuid4()),
                        "ca": ca,
                        "score": score,
                        "warnings": warnings,
                        "pair": pair,
                        "is_lp_burned": is_lp_burned,
                        "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    # 新しい結果を先頭に追加（要件：新しい結果の上に表示）
                    st.session_state.results.insert(0, res_obj)
                else:
                    st.toast("有効なペアが見つかりませんでした", icon="⚠️")
            else:
                st.toast("トークン情報が見つかりませんでした", icon="❌")
    else:
        st.toast("有効なコントラクトアドレスまたはURLを入力してください", icon="❓")
    
    # 入力枠をクリア（要件：入力枠クリア）
    st.session_state.ca_input_val = ""

# --- UI設定 ---
st.set_page_config(page_title="Solana Validator Pro", layout="centered", page_icon="🛡️")

st.title("🛡️ Solana Token Validator Pro")
st.markdown("CAまたはURLを入力してEnterを押してください。解析結果は新しい順に表示されます。")

# 入力セクション
st.text_input(
    "Contract Address / DEXScreener URL", 
    key="ca_input_val", 
    on_change=on_input_change,
    placeholder="例: EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
)

st.divider()

# 解析結果の表示
if not st.session_state.results:
    st.info("解析結果がここに表示されます。")

for i, res in enumerate(st.session_state.results):
    with st.container(border=True):
        # ヘッダーエリア（削除ボタンを右上に配置）
        header_col1, header_col2 = st.columns([9, 1])
        
        pair = res["pair"]
        base_token = pair.get('baseToken', {})
        info = pair.get('info', {})
        
        with header_col1:
            # トークン情報 (要件2)
            col_img, col_info = st.columns([1, 5])
            with col_img:
                if info.get('imageUrl'):
                    st.image(info['imageUrl'], width=64)
            with col_info:
                st.subheader(f"{base_token.get('name', 'Unknown')} ({base_token.get('symbol', '???')})")
                st.caption(f"CA: `{res['ca']}`")
        
        with header_col2:
            # 削除ボタン (要件：Xボタンで消せる)
            if st.button("❌", key=f"del_{res['id']}"):
                st.session_state.results.pop(i)
                st.rerun()

        # 判定ランクと主要メトリクス
        score = res["score"]
        rank = "🟢 S" if score >= 85 else "🟡 B" if score >= 50 else "🔴 F"
        
        rank_col, m1, m2, m3 = st.columns([1.5, 2, 2, 2])
        rank_col.markdown(f"### {rank}")
        m1.metric("時価総額", f"${pair.get('fdv', 0):,.0f}")
        m2.metric("流動性", f"${pair.get('liquidity', {}).get('usd', 0):,.0f}")
        m3.metric("LP Burn", "✅ Yes" if res["is_lp_burned"] else "❌ No")

        # 警告と補足情報
        exp_col1, exp_col2 = st.columns(2)
        with exp_col1:
            if res["warnings"]:
                for w in res["warnings"]:
                    st.warning(w, icon="⚠️")
            else:
                st.success("重大なリスクなし", icon="✅")
        
        with exp_col2:
            # 市場補足情報
            changes = pair.get('priceChange', {})
            st.markdown(f"**価格変化率 (24h):** `{changes.get('h24', 0)}%` | **取引数:** `{pair.get('txns', {}).get('h24', {}).get('buys', 0)}B / {pair.get('txns', {}).get('h24', {}).get('sells', 0)}S`")
            
            created_at = pair.get('pairCreatedAt')
            if created_at:
                created_dt = datetime.fromtimestamp(created_at / 1000).strftime("%Y-%m-%d %H:%M")
                st.caption(f"📅 ペア作成: {created_dt}")

        # 外部リンク
        websites = info.get('websites', [])
        socials = info.get('socials', [])
        all_links = websites + socials
        if all_links:
            link_cols = st.columns(min(len(all_links), 6))
            for j, link in enumerate(all_links):
                label = link.get('label') or link.get('type', 'Link').capitalize()
                link_cols[j % 6].link_button(label, link['url'], use_container_width=True)

        st.caption(f"🕒 データ取得日時: {res['fetch_time']}")
