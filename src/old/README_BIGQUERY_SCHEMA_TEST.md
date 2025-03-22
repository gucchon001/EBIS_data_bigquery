# BigQueryスキーマテスト手順書

このプロジェクトは、AE_CVresult_schema.csvファイルからBigQueryスキーマを作成し、サンプルデータを使用してスキーマが正しく機能するかテストするためのツールセットです。

## 前提条件

- Python 3.6以上
- GCPアカウントとBigQueryへのアクセス権
- サービスアカウントキーファイル（JSON形式）

## セットアップ手順

### 1. 環境変数の設定

以下のコマンドで環境変数設定スクリプトを実行し、必要な環境変数を設定します。

```
.\set_bigquery_env.bat
```

このスクリプトは以下の環境変数を設定します：
- `BIGQUERY_PROJECT_ID`: BigQueryのプロジェクトID
- `BIGQUERY_DATASET`: 使用するBigQueryデータセットID
- `GCS_KEY_PATH`: GCPサービスアカウントキーファイルのパス

### 2. 必要なPythonライブラリのインストール

```
pip install google-cloud-bigquery pandas
```

## テスト実行手順

### 方法1: テスト自動実行スクリプトを使用する

すべてのステップを自動で実行するには、以下のコマンドを実行します。

```
.\run_bigquery_schema_test.bat
```

このスクリプトは以下の処理を順番に実行します：
1. 環境変数のチェック
2. 必要なライブラリのインストール
3. テストデータの作成
4. BigQueryへのテーブル作成とデータロード
5. ロードされたデータの検証

### 方法2: 個別のスクリプトを使用する

#### 2.1. テストデータの作成

```
python create_test_data.py
```

このスクリプトは、AE_CVresult_schema.csvファイルを読み込み、以下のファイルを生成します：
- BigQueryスキーマを表すJSONファイル
- テスト用のCSVデータファイル

#### 2.2. BigQueryへのデータロードとテスト

```
python test_load_to_bigquery.py --csv-file "<生成されたCSVファイルパス>" --schema-file "<生成されたスキーマファイルパス>" --table-name "ae_cvresult_test"
```

例：
```
python test_load_to_bigquery.py --csv-file "data\SE_SSresult\test\test_data_20250322_211631.csv" --schema-file "data\SE_SSresult\test\test_schema_20250322_211631.json" --table-name "ae_cvresult_test"
```

## ファイル構成

- `set_bigquery_env.bat`: BigQuery接続用の環境変数を設定するスクリプト
- `create_test_data.py`: テストデータとスキーマJSONを作成するスクリプト
- `test_load_to_bigquery.py`: CSVデータをBigQueryにロードしてテストするスクリプト
- `run_bigquery_schema_test.bat`: テスト全体を自動実行するスクリプト
- `create_and_test_bigquery_schema.py`: スキーマ作成からテストまでを一括で行うスクリプト

## 生成されるスキーマについて

生成されるBigQueryスキーマは以下のルールに従います：

1. `column_name_mod`フィールドがBigQueryのフィールド名として使用されます
2. データ型の変換規則：
   - `str` → `STRING`
   - `int` → `INTEGER`
   - `timestamp` → `TIMESTAMP`

## 注意事項

- timestampデータは、Excelの日付シリアル値（1900-01-01からの日数）から変換されます
- すべてのフィールドは`NULLABLE`（NULL許容）として定義されます
- 一時ファイルはdata/SE_SSresult/testディレクトリに保存されます 