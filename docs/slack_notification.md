# Slack通知の設定

このプロジェクトではエラー発生時などの重要なイベントをSlackに通知する機能があります。この文書では、Slack通知の設定方法について説明します。

## 1. Slack Webhookの取得

Slack通知を有効にするには、SlackのWebhook URLが必要です。以下の手順で取得できます：

1. [Slack API](https://api.slack.com/apps)にアクセスします
2. 「Create New App」をクリックします
   - 「From scratch」を選択
   - アプリ名（例：「EBiS Automation」）を入力
   - ワークスペースを選択
3. 「Incoming Webhooks」を有効にします
   - 「Incoming Webhooks」をクリックし、「Activate Incoming Webhooks」をオンにします
4. 「Add New Webhook to Workspace」をクリックします
   - 通知を送信するチャンネルを選択します
5. 「Webhook URL」をコピーします
   - これが設定に必要なWebhook URLです

## 2. 環境変数の設定

取得したWebhook URLを環境変数に設定します：

1. `config/secrets.env`ファイルを開きます
2. `SLACK_WEBHOOK_URL`の値を更新します：

```
# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXXXX/YYYYY/ZZZZZ
```

**注意**: Webhook URLにはシークレットトークンが含まれているため、GitHubなどの公開リポジトリにコミットしないでください。

## 3. トラブルシューティング

### Webhook URLが無効になった場合

Webhook URLは、以下の理由で無効になることがあります：

1. URLの有効期限が切れた
2. Slackワークスペースの設定が変更された
3. Webhookが管理者によって無効化された

**解決策**: 上記の手順に従って新しいWebhook URLを取得し、設定を更新してください。

### 「invalid_token」エラーが表示される場合

このエラーは、トークンが無効であることを示しています。以下の対応を行ってください：

1. Slack API管理画面でWebhookが有効になっているか確認
2. 新しいWebhookを作成して設定を更新

### Slack通知を無効にする方法

一時的にSlack通知を無効にする場合は、`SLACK_WEBHOOK_URL`を空にします：

```
# Slack
SLACK_WEBHOOK_URL=
```

## 4. 通知内容のカスタマイズ

通知内容をカスタマイズする場合は、`src/utils/slack_notifier.py`ファイルを編集します：

- メッセージのタイトル、フッター、カラーコードなどを変更できます
- 追加のフィールド情報やスタックトレースの表示形式も調整可能です

## 5. 通知テストの実行

以下のコマンドを実行することで、通知機能のテストができます：

```bash
python -m src.modules.browser.test_error
```

このコマンドは意図的にブラウザエラーを発生させ、Slack通知が正しく機能しているか確認します。 