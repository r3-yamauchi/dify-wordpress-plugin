# Privacy Policy

## English

### Data Handling
This plugin exchanges the minimum data required to send email through wordpress:
1. **wordpress Credentials** – `api_key` is supplied by users through Dify's secret storage and is only used for authentication with wordpress REST API v3 during request execution.
2. **Email Payloads** – recipient addresses, subjects, message bodies, headers, metadata, and optional attachments provided as tool inputs are serialized into the wordpress API v3 format.
3. **Delivery Identifiers** – Message IDs returned by wordpress are surfaced back to the workflow for status tracking.

### Data Storage
- The plugin does not persist credentials, payloads, or attachments on disk. Temporary files supplied by Dify are deleted automatically by the runtime.
- No telemetry or message content is logged beyond minimal delivery identifiers for debugging if logging is enabled.

### Security
- All outbound calls use wordpress's HTTPS endpoints.
- Secrets remain managed by Dify; the plugin only reads them in memory when a tool runs.
- Attachments are validated locally to avoid uploading unsupported formats.

### Third-Party Disclosure
- Data is sent only to wordpress's official API endpoints selected by the user. No other third parties receive any information.

---

## 日本語

### 取り扱うデータ
`wordpress` はメール送信に必要な最小限の情報のみを扱います。
1. **wordpress認証情報** – `api_key` はDifyのシークレット管理で保存され、ツール実行時にwordpress REST API v3への認証に使用します。
2. **メールペイロード** – 受信者、件名、本文、ヘッダー、メタデータ、添付ファイルなどツール入力として受け取った内容を wordpress API v3 形式に変換します。
3. **配信ID** – wordpressから返却されるMessage IDをワークフローに返し、ステータス確認に利用します。

### データ保存
- プラグインは認証情報やメール内容をローカルディスクに保存しません。Difyが提供する一時ファイルは実行終了後に削除されます。
- ログにはDelivery IDなど最小限のメタデータのみを記録し、本文/添付ファイルの内容は記録しません。

### セキュリティ
- すべての通信はwordpressのHTTPSエンドポイントを使用します。
- シークレットはDify側で管理され、プラグインはツール実行時のみメモリ上で参照します。
- 添付ファイルは送信前にローカル検証し、禁止拡張子やサイズ超過を防ぎます。

### 第三者提供
- ユーザーが指定したwordpress公式API以外の第三者へデータを送信することはありません。
