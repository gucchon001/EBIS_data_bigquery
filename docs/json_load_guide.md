# JSONファイルからBigQueryへのデータロード手順

このドキュメントでは、JSONファイルからBigQueryにデータをロードするための手順を説明します。

## 前提条件

- Python 3.7以上
- 必要なPythonパッケージがインストールされていること
- BigQueryへのアクセス権限が設定されていること
- 環境変数ファイル（`config/secrets.env`）が適切に設定されていること

## 使用方法

### 1. CSVファイルからJSONファイルへの変換（必要な場合）

CSVファイルをJSONファイルに変換する必要がある場合は、以下のコマンドを使用します：

```bash
python -m src.convert_csv_to_json <CSV_ファイルパス> <JSONファイルパス> [オプション]
```

#### オプション：

- `--encoding <エンコーディング>`: CSVファイルのエンコーディングを指定します（デフォルト: cp932）
- `--limit <行数>`: 読み込む行数を制限します
- `--orient <形式>`: JSONの出力形式を指定します（デフォルト: records）
- `--no-lines`: 各行を独立したJSON形式で出力しない

#### 例：

```bash
python -m src.convert_csv_to_json data/AE_SSresult/AE_CV属性result.csv data/AE_SSresult/converted_data.json --limit 10
```

### 2. JSONファイルをBigQueryにロードする

JSONファイルをBigQueryにロードするには、以下のコマンドを使用します：

```bash
python -m src.load_json_to_bigquery <JSONファイルパス> <テーブル名> [オプション]
```

#### オプション：

- `--write-disposition <処理方法>`: テーブルが既に存在する場合の挙動を指定します
  - `WRITE_TRUNCATE`: テーブルを切り捨てて新しいデータを書き込む（デフォルト）
  - `WRITE_APPEND`: 既存のテーブルにデータを追加する
  - `WRITE_EMPTY`: テーブルが空の場合のみ書き込む

#### 例：

```bash
python -m src.load_json_to_bigquery data/AE_SSresult/converted_data.json test_converted_data
```

## 注意事項

### カラム名の正規化

BigQueryでは、テーブルのカラム名に使用できる文字に制限があります。`load_json_to_bigquery`スクリプトは、自動的にカラム名を正規化して次のような変換を行います：

- カッコや特殊文字をアンダースコアに置換（例：`間接効果7(広告ID)` → `間接効果7_広告ID`）
- 連続するアンダースコアを1つに統合
- 先頭と末尾のアンダースコアを削除
- 空白文字をアンダースコアに置換
- 先頭が数字の場合は、先頭に'f_'を追加

### JSONファイル形式

BigQueryがロードするJSONファイルは、改行区切りのJSON（Newline Delimited JSON）形式である必要があります。この形式では、各行が1つの独立したJSONオブジェクトを表します。

## トラブルシューティング

### エンコーディングの問題

CSVファイルのエンコーディングにより読み込みエラーが発生する場合は、適切なエンコーディングを指定してください。日本語のCSVファイルでは、`cp932`や`shift-jis`などが一般的です。

```bash
python -m src.convert_csv_to_json <CSVファイルパス> <JSONファイルパス> --encoding cp932
```

### BigQueryのロードエラー

BigQueryへのロード中にエラーが発生した場合は、エラーメッセージを確認してください。一般的な問題としては：

- カラム名の不正（特殊文字を含む）
- データ型の不一致
- 不正な日付/時刻形式
- アクセス権限の問題

## データの確認

ロードされたデータを確認するには、以下のコマンドを使用します：

```bash
python -m src.query_bigquery <テーブル名>
```

例：

```bash
python -m src.query_bigquery test_converted_data
``` 