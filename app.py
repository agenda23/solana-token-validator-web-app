import streamlit as st
import requests
import re
from datetime import datetime
import uuid
import json

# --- 補助関数: CAの抽出 ---
def extract_ca(input_text):
    pattern = r'[1-9A-HJ-NP-Za-km-z]{32,44}'
    match = re.search(pattern, input_text)
    return match.group(0) if match else None

# --- 補助関数: 数値の短縮表記 ---
def format_abbreviated(val):
    prefix = "&#36;" # $ sign
    if val >= 1_000_000_000:
        return f"{prefix}{val/1_000_000_000:.2f}B"
    if val >= 1_000_000:
        return f"{prefix}{val/1_000_000:.2f}M"
    if val >= 1_000:
        return f"{prefix}{val/1_000:.1f}K"
    return f"{prefix}{val:,.0f}"

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
    is_honeypot = False
    has_boost = False
    boost_amount = 0
    has_web = False
    has_sns = False
    
    results = go_data.get('result')
    if not isinstance(results, dict):
        results = {}
    
    sec = results.get(ca) or results.get(ca.lower()) or {}
    pair = None
    if dex_data and dex_data.get('pairs'):
        pair = max(dex_data['pairs'], key=lambda x: x.get('liquidity', {}).get('usd', 0))
    
    if sec.get('is_honeypot') == '1':
        score -= 100
        is_honeypot = True
        details.append("❌ ハニーポット検出 (-100)")
    if sec.get('mintable', {}).get('status') == '1':
        score -= 50
        details.append("⚠️ Mint権限が有効 (-50)")
    if sec.get('freezable', {}).get('status') == '1':
        score -= 40
        details.append("⚠️ Freeze権限が有効 (-40)")
        
    lp_burned = False
    if pair and 'pairAddress' in pair:
        pair_address = pair['pairAddress']
        for g_dex in sec.get('dex', []):
            if g_dex.get('id') == pair_address:
                if float(g_dex.get('burn_percent', 0)) > 95:
                    lp_burned = True
                    break
    
    if pair:
        if lp_burned:
            score += 10
            details.append("✅ LP Burn済み (+10)")
        else:
            score -= 10
            details.append("⚠️ LP未焼却 (-10)")
        
        liquidity = pair.get('liquidity', {}).get('usd', 0)
        if liquidity < 50000:
            score -= 20
            details.append(f"⚠️ 流動性が低い (${liquidity:,.0f}) (-20)")

        info = pair.get('info', {})
        websites = info.get('websites', [])
        socials = info.get('socials', [])
        
        if not websites:
            score -= 5
            details.append("🔻 公式サイト未設定 (-5)")
        else:
            has_web = True
        
        if not socials:
            score -= 5
            details.append("🔻 SNSリンク未設定 (-5)")
        else:
            has_sns = True

        boosts_active = pair.get('boosts', {}).get('active', 0)
        if boosts_active > 0:
            score += 5
            has_boost = True
            boost_amount = boosts_active
            details.append(f"🔥 DEXScreener Boost有効 ({boosts_active}) (+5)")
    else:
        score -= 30
        details.append("❓ 市場データ未検出 (-30)")
    
    if is_honeypot or score <= 0:
        rank, r_label, color = "💀 F-", "Deadly", "#CC0000" # Dark Red
    elif score < 30:
        rank, r_label, color = "🔴 F", "Fail", "#CC0000"
    elif score < 50:
        rank, r_label, color = "☠️ F+", "Suspicious", "#D35400" # Dark Orange
    elif score < 85:
        rank, r_label, color = "🔸 C", "Caution", "#856404" # Dark Yellow/Brown
    elif score >= 85 and (not has_web or not has_sns):
        rank, r_label, color = "🥉 B", "Barebones", "#873600" # Dark Bronze
    elif score >= 85 and not has_boost:
        rank, r_label, color = "🥈 A", "Authenticity", "#424949" # Dark Silver/Gray
    elif score >= 90 and has_boost and has_web and has_sns and lp_burned:
        rank, r_label, color = "🥇 S", "Premium", "#996515" # Dark Gold
    else:
        rank, r_label, color = "🥈 A", "Authenticity", "#424949"
        
    return score, details, pair, lp_burned, has_boost, boost_amount, has_web, has_sns, rank, r_label, color

# --- セッション管理 ---
if 'results' not in st.session_state:
    st.session_state.results = []

def on_input_change():
    input_text = st.session_state.ca_input_val
    if not input_text: return
    ca = extract_ca(input_text)
    if ca:
        with st.spinner(f"CA: {ca} を解析中..."):
            dex, go = get_data(ca)
            score, warnings, pair, is_lp_burned, has_boost, b_amt, h_web, h_sns, rank, r_label, color = calculate_safety(dex or {"pairs": []}, go or {"result": {}}, ca)
            res_obj = {
                "id": str(uuid.uuid4()), "ca": ca, "score": score, "warnings": warnings, "pair": pair,
                "is_lp_burned": is_lp_burned, "has_boost": has_boost, "boost_amount": b_amt,
                "has_web": h_web, "has_sns": h_sns, "rank": rank, "rank_label": r_label, "rank_color": color,
                "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "raw_dex": dex, "raw_go": go, "not_found_on_dex": pair is None
            }
            st.session_state.results.insert(0, res_obj)
    st.session_state.ca_input_val = ""

# --- アプリUI ---
st.set_page_config(page_title="Solana Validator", layout="centered", page_icon="🛡️")
debug_mode = "debug-mode" in st.query_params

# カスタムCSS
st.markdown("""
<style>
    .metric-card {
        background-color: rgba(255, 255, 255, 0.05);
        padding: 15px;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .stLinkButton > a {
        margin-bottom: 8px !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Solana Token Validator")
st.text_input("Contract Address / DEXScreener URL", key="ca_input_val", on_change=on_input_change, placeholder="CAまたはURLを入力してEnter")

st.divider()

for i, res in enumerate(st.session_state.results):
    with st.container(border=True):
        header_col, del_col = st.columns([9, 1])
        pair = res["pair"]
        base_token = pair.get('baseToken', {}) if pair else {}
        info = pair.get('info', {}) if pair else {}
        
        with header_col:
            img_col, info_col = st.columns([1, 6])
            with img_col:
                if info.get('imageUrl'): st.image(info['imageUrl'], width=80)
                else: st.markdown("<div style='font-size: 60px; margin-top: 10px;'>🪙</div>", unsafe_allow_html=True)
            with info_col:
                st.markdown(f"<h2 style='margin-bottom: 0;'>{base_token.get('name', 'Unknown')} ({base_token.get('symbol', '???')})</h2>", unsafe_allow_html=True)
                caption_html = f"<div style='margin-bottom: 15px;'>"
                if res["has_boost"]:
                    caption_html += f"<span style='color: #FF8C00; font-weight: bold; font-size: 0.9em;'>🔥 BOOSTED ({res['boost_amount']})</span> | "
                caption_html += f"<span style='color: gray; font-size: 0.85em;'>CA: {res['ca']}</span>"
                caption_html += "</div>"
                st.markdown(caption_html, unsafe_allow_html=True)
                
                if not res["not_found_on_dex"]:
                    all_links = info.get('websites', []) + info.get('socials', [])
                    if all_links:
                        link_cols = st.columns(min(len(all_links), 5))
                        for j, l in enumerate(all_links):
                            label = l.get('label') or l.get('type', 'Link').capitalize()
                            link_cols[j % 5].link_button(label, l['url'], use_container_width=True)
        
        with del_col:
            if st.button("❌", key=f"del_{res['id']}"):
                st.session_state.results.pop(i)
                st.rerun()

        st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)

        # 市場データ
        r_col, m1, m2, m3 = st.columns([2.5, 2, 2, 2])
        r_col.markdown(
            f"<div style='line-height: 1.1; margin-bottom: 10px;'>"
            f"<small style='color: gray;'>RANK</small><br>"
            f"<span style='color: {res['rank_color']}; font-size: 1.8em; font-weight: bold;'>{res['rank']}</span><br>"
            f"<small style='color: {res['rank_color']}; font-size: 0.85em;'>({res['rank_label']})</small>"
            f"</div>", 
            unsafe_allow_html=True
        )
        
        if not res["not_found_on_dex"]:
            fdv = pair.get('fdv', 0)
            m1.markdown(f"<div><small style='color: gray;'>時価総額</small><br><strong style='font-size: 1.3em;'>{format_abbreviated(fdv)}</strong><br><small style='color: #888;'>&#36;{fdv:,.0f}</small></div>", unsafe_allow_html=True)
            liq = pair.get('liquidity', {}).get('usd', 0)
            m2.markdown(f"<div><small style='color: gray;'>流動性</small><br><strong style='font-size: 1.3em;'>{format_abbreviated(liq)}</strong><br><small style='color: #888;'>&#36;{liq:,.0f}</small></div>", unsafe_allow_html=True)
            m3.markdown(f"<div><small style='color: gray;'>LP Burn</small><br><strong style='font-size: 1.3em;'>{'✅ Yes' if res['is_lp_burned'] else '❌ No'}</strong></div>", unsafe_allow_html=True)
        else:
            m1.markdown("<div><small style='color: gray;'>時価総額</small><br><strong>N/A</strong></div>", unsafe_allow_html=True)
            m2.markdown("<div><small style='color: gray;'>流動性</small><br><strong>N/A</strong></div>", unsafe_allow_html=True)
            m3.markdown("<div><small style='color: gray;'>LP Burn</small><br><strong>N/A</strong></div>", unsafe_allow_html=True)

        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

        # 判定理由とスコア
        warn_col, score_col = st.columns([6, 4])
        with warn_col:
            with st.expander("📝 判定理由・詳細", expanded=True):
                if not res["warnings"]: st.success("主要なリスクなし")
                else:
                    for w in res["warnings"]:
                        if any(x in w for x in ["✅", "🔥"]): st.caption(w)
                        else: st.warning(w)
        
        with score_col:
            score_color = '#1E7E34' if res['score'] >= 85 else '#856404' if res['score'] >= 50 else '#CC0000'
            st.markdown(
                f"<div class='metric-card'>"
                f"<div style='margin-bottom: 15px;'><small style='color: gray;'>TOTAL SCORE</small><br><strong style='font-size: 2.2em; color: {score_color};'>{res['score']}</strong></div>", 
                unsafe_allow_html=True
            )
            if not res["not_found_on_dex"]:
                changes = pair.get('priceChange', {}).get('h24', 0)
                st.markdown(f"<div style='margin-bottom: 12px;'><small style='color: gray;'>価格変化 (24h)</small><br><strong style='font-size: 1.3em;'>{changes}%</strong></div>", unsafe_allow_html=True)
                txns = pair.get('txns', {}).get('h24', {})
                st.markdown(f"<div><small style='color: gray;'>取引数 (24h)</small><br><strong style='font-size: 1.1em;'>{txns.get('buys', 0)} Buy / {txns.get('sells', 0)} Sell</strong></div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        st.caption(f"🕒 解析日時: {res['fetch_time']}")
        if debug_mode:
            with st.expander("🛠️ Raw Data"): st.json({"DexScreener": res["raw_dex"], "GoPlus": res["raw_go"]})
