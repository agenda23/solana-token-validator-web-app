# 🛡️ Solana Token Validator

Solanaブロックチェーン上のトークン（CA）を解析し、技術的安全性と市場の活性度を多角的に評価するプロフェッショナル向け検証ツールです。

## 🌟 主な特徴

- **7段階の高度な格付けシステム**: セキュリティスコアだけでなく、運営のプロモーション状況やコミュニティの実体を加味した S〜F- の評価を算出。
- **DEXScreener Boost連携**: 運営がどれだけの広告費を投じているかをリアルタイムに表示。
- **GoPlus Security 統合**: ハニーポット判定、Mint/Freeze権限、LPの焼却（Burn）状況を技術的に検証。
- **洗練されたUI**:
    - 通貨単位の短縮表記（$M, $K）と全桁表示のハイブリッド。
    - 直感的なコミュニティリンク・ナビゲーション。
    - Total Scoreと市場変動の垂直配置レイアウト。

## 📊 判定ランクの定義

1.  **🥇 S (Premium)**: 安全・人気・運営のやる気の三拍子が揃った最高ランク。
2.  **🥈 A (Authenticity)**: 健全な運営とコミュニティ。広告（Boost）がないのみ。
3.  **🥉 B (Barebones)**: 技術的には安全だが、公式サイト等のコミュニティ情報が欠損している「中身空っぽ」状態。
4.  **🔸 C (Caution)**: 流動性不足やLP未焼却など、リスクはあるが投機可能な範囲。
5.  **☠️ F+ (Suspicious)**: 無限発行（Mint）リスクや重大な権限残りがある危険状態。
6.  **🔴 F (Fail)**: 投資非推奨。
7.  **💀 F- (Deadly)**: ハニーポット検出。確定詐欺。

## 🚀 セットアップ

### 必要条件
- Python 3.10以上
- pip

### インストール
```bash
git clone <repository-url>
cd solana-token-validator-web-app
pip install -r requirements.txt
```

### 実行
```bash
streamlit run app.py
```

## 🛠️ デバッグモード
URLの末尾に `?debug-mode` を追加することで、生データ（JSON）を確認できるエンジニアモードが有効になります。

## 📜 ドキュメント
- [詳細仕様書 (Spec Sheet)](docs/solana%20token%20validator%20spec%20sheet.md)
- [開発ウォークスルー (Walkthrough)](docs/walkthrough.md)

## 免責事項
本ツールはデータに基づいた解析情報を提供するものであり、投資を助言するものではありません。暗号資産投資は高いリスクを伴います。最終的な判断はご自身で行ってください。
