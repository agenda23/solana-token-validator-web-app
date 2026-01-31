DEX Screener APIは、複数のブロックチェーンにまたがる分散型取引所（DEX）のペア情報、価格、ボリューム、トークンプロフィールなどを取得するための無料のREST APIです。

## 1. 基本情報

- **ベースURL**: `https://api.dexscreener.com/`
    
- **認証**: 不要（Public API）
    
- **フォーマット**: JSON
    

## 2. トークンプロフィール・広告・ブースト関連

これらのエンドポイントは、DEX Screener上で有料サービス（トークン情報の更新や広告）を利用しているトークンに関する情報を取得します。

|**エンドポイント**|**メソッド**|**レート制限**|**内容**|
|---|---|---|---|
|`/token-profiles/latest/v1`|GET|60 req/min|最新のトークンプロフィールを取得|
|`/community-takeovers/latest/v1`|GET|60 req/min|最新のコミュニティ・テイクオーバー情報を取得|
|`/ads/latest/v1`|GET|60 req/min|現在掲載されている最新の広告を取得|
|`/token-boosts/latest/v1`|GET|60 req/min|最新のブースト（有料露出）トークンを取得|
|`/token-boosts/top/v1`|GET|60 req/min|最も多くブーストされているトークンを取得|
|`/orders/v1/{chainId}/{tokenAddress}`|GET|60 req/min|特定トークンの有料注文（情報の更新など）の状態を確認|

## 3. DEXペア・検索関連（コア機能）

トークンの価格、時価総額、流動性などの詳細データを取得するためのメインのエンドポイントです。

|**エンドポイント**|**メソッド**|**レート制限**|**内容**|
|---|---|---|---|
|`/latest/dex/pairs/{chainId}/{pairAddress}`|GET|300 req/min|チェーンIDとペアアドレスで特定のペア情報を取得|
|`/latest/dex/tokens/{tokenAddresses}`|GET|300 req/min|1つまたは複数のトークンアドレス（最大30個、カンマ区切り）から関連するペア情報を取得|
|`/latest/dex/search?q={query}`|GET|300 req/min|クエリ（トークン名、シンボル、ペア等）に一致するペアを検索|

## 4. 主なレスポンスフィールド（Pair Object）

`pairs` 配列に含まれる主なデータ構造は以下の通りです。

- **chainId**: チェーンの識別子（例: `solana`, `ethereum`, `bsc`）
    
- **dexId**: DEXの識別子（例: `raydium`, `uniswap`）
    
- **pairAddress**: ペアのコントラクトアドレス
    
- **baseToken / quoteToken**: トークンのアドレス、名前、シンボル
    
- **priceNative**: ネイティブ通貨（SOLやETHなど）建ての価格
    
- **priceUsd**: USD建ての価格
    
- **txns**: 過去24時間、6時間、1時間、5分間の売買回数
    
- **volume**: 各期間の取引高
    
- **priceChange**: 各期間の価格変化率
    
- **liquidity**: 流動性（USD, Base, Quote）
    
- **fdv**: 完全希薄化時価総額
    
- **marketCap**: 時価総額（データがある場合）
    
- **info**: 画像URL、Webサイト、SNSリンクなどの追加情報
    

## 5. 利用上の注意

- **レート制限**: 各エンドポイントに設定された制限を超えるとHTTP 429エラーが返されます。
    
- **最新性**: APIは非常に高頻度で更新されますが、フロントエンドの表示とわずかなタイムラグが生じる場合があります。
    
- **利用規約**: APIを商用利用する場合や大量のアクセスを行う場合は、公式のTerms & Conditionsを確認してください。
    

---

_詳細なJSONスキーマやテスト実行については、[公式ドキュメント](https://docs.dexscreener.com/api/reference)を参照してください。_