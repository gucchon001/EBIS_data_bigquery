# EBIS_BIGQUERY - BigQueryスキーマ作成・テストツールセット

このプロジェクトは、BigQuery用のスキーマを作成し、テストデータをロードしてスキーマの検証を行うためのツールセットです。日本語の列名や特殊文字を含むフィールド名、および括弧を含む列名の処理に対応しています。

## 主な機能

1. CSVファイルからBigQueryスキーマを作成
   - 列名と型情報を抽出
   - 日本語の列名に対応
   - フィールド名の特殊文字処理

2. テストデータの自動生成
   - サンプル値からランダムなバリエーションを作成
   - タイムスタンプ型の適切な処理

3. BigQueryへのロードテスト機能
   - スキーマに基づくテーブル作成
   - テストデータのロード
   - 検証機能

4. GCSからBigQueryへのロード機能
   - 括弧や特殊文字を含む列名の前処理
   - CSV/Parquetファイルの対応
   - 文字エンコーディングの処理

## ファイル構成

```
EBIS_BIGQUERY/
├── README.md                          # このファイル
├── config/
│   └── secrets.env                    # 環境変数設定ファイル
├── src/
│   ├── __init__.py                   # ソースパッケージ定義
│   │   ├── __init__.py               # ユーティリティパッケージ定義
│   │   └── environment.py            # 環境変数管理ユーティリティ
│   └── modules/
│       └── bigquery/
│           ├── preprocess_gcs_files.py         # GCSファイル前処理ユーティリティ
│           ├── load_preprocessed_files.py      # 前処理済みファイルロードユーティリティ
│           └── load_preprocessed_ae_ssresult.py # AE_SSresult専用ロードスクリプト
├── create_and_test_bigquery_schema.py  # スキーマ作成・テストメインスクリプト
├── create_test_data.py                 # テストデータ・スキーマJSON生成スクリプト
├── test_load_to_bigquery.py            # BigQueryへのテストデータロードスクリプト
├── run_bigquery_schema_test.bat        # テスト自動実行バッチファイル
├── set_bigquery_env.bat                # 環境変数設定ツール
├── run_preprocessed_gcs_to_bigquery.bat # GCSデータロード実行バッチファイル
└── requirements.txt                    # 必要なPythonライブラリ
```

## 使用方法

### 前提条件

1. Python 3.7以上
2. 必要なライブラリ：
   - google-cloud-bigquery
   - google-cloud-storage
   - pandas
   - python-dotenv

### 環境変数の設定

1. `set_bigquery_env.bat`を実行して環境変数を設定します。
   - 実行すると`config/secrets.env`ファイルが生成されます（存在しない場合）
   - このファイルをテキストエディタで開き、以下の値を設定します：
     
     ```
     #GCS
     GCP_PROJECT_ID=your-project-id
     GCS_BUCKET_NAME=your-bucket-name
     GCS_KEY_PATH=config/your-key-file.json
     
     #bigquery
     BIGQUERY_PROJECT_ID=your-project-id
     BIGQUERY_DATASET=your-dataset
     LOG_TABLE=rawdata_log
     ```

2. GoogleCloudのサービスアカウントキーファイルを取得し、`GCS_KEY_PATH`で指定したパスに配置します。

### スキーマ作成とテスト

1. `run_bigquery_schema_test.bat`を実行します
   - オプション:
     - `--schema FILE`: 使用するスキーマCSVファイル（デフォルト: data/SE_SSresult/AE_CVresult_schema.csv）
     - `--mode MODE`: 実行モード（create: データ作成のみ、load: ロードのみ、all: 両方）

   例: `run_bigquery_schema_test.bat --mode create`

### GCSデータのBigQueryへのロード

カッコや特殊文字を含む列名のファイルをGCSからBigQueryにロードする場合：

1. `run_preprocessed_gcs_to_bigquery.bat`を実行します
   - オプション:
     - `--gcs-path`: GCSパス (例: gs://your_bucket/path)
     - `--table-prefix`: テーブル名のプレフィックス
     - `--dataset`: データセットID
     - `--file-type`: ファイル形式（csv/parquet）
     - `--write-disposition`: 書き込みモード（WRITE_EMPTY/WRITE_TRUNCATE/WRITE_APPEND）

   例: `run_preprocessed_gcs_to_bigquery.bat --gcs-path gs://your_bucket/path --table-prefix prefix --file-type csv`

## 注意事項

- BigQueryへのアクセスには適切な権限を持つサービスアカウントが必要です
- 大量のデータを処理する場合は、メモリ使用量に注意してください
- ログは`logs`ディレクトリに保存されます

## テスト環境

このツールは以下の環境でテスト済みです：
- Windows 10
- Python 3.9.7
- BigQuery API v2

# EBIS BigQuery データローダー

## 概要

このプロジェクトは、CSVファイルをGoogle BigQueryにロードするためのツールです。特にExcelから出力されたタイムスタンプ値を含むデータを適切に変換し、BigQueryのスキーマに合わせて処理します。

## 前提条件

- Python 3.7以上
- Google Cloud認証情報（サービスアカウントキー）
- 必要なPythonパッケージ（requirements.txt参照）

## セットアップ

1. リポジトリをクローン/ダウンロード

2. 必要なパッケージをインストール
   ```
   pip install -r requirements.txt
   ```

3. 環境変数ファイルを設定
   `config/secrets.env`ファイルを作成し、以下の内容を設定してください：
   ```
   BIGQUERY_PROJECT_ID=あなたのGCPプロジェクトID
   BIGQUERY_DATASET_ID=使用するデータセットID
   BIGQUERY_KEY_PATH=サービスアカウントキーファイルのパス
   ```

## 使用方法

### コマンドライン

```bash
# デフォルト値を使用
load_to_bigquery.bat

# 引数を指定
load_to_bigquery.bat --input "data/path/to/your/file.csv" --output "your_table_name"
```

### パラメータ

- `--input` : 入力CSVファイルのパス（デフォルト: `data\AE_CV\SE_SSresult\result_schema.csv`）
- `--output` : 出力BigQueryテーブル名（デフォルト: `AE_CVresult`）

## 入力CSVファイル形式

CSVファイルには以下の列が必要です：

- `column_name_mod` : フィールド名
- `data_type` : データ型（`str`, `int`, `timestamp`のいずれか）
- `sample` : サンプルデータ（タイムスタンプはExcelシリアル値形式）

## ディレクトリ構造

```
├── config/               # 設定ファイル
│   └── secrets.env       # 環境変数ファイル（要作成）
├── data/                 # データファイル
│   ├── schema/           # 生成されたスキーマJSONファイル
│   └── AE_CV/            # 入力CSVファイル
├── src/                  # ソースコード
│   ├── load_to_bigquery.py  # メインスクリプト
│   └── utils/            # ユーティリティ
│       └── environment.py    # 環境変数ユーティリティ
├── load_to_bigquery.bat  # 実行用バッチファイル
└── requirements.txt      # 依存パッケージ
```

## 注意事項

- BigQueryの命名規則に合わせて、フィールド名の特殊文字はアンダースコアに置換されます
- タイムスタンプ値はExcelシリアル値から適切なBigQueryタイムスタンプ形式に変換されます
- 既存のテーブルは上書きされます
