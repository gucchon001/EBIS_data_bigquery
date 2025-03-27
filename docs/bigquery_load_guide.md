# EBIS CSV → BigQuery データロード仕様書

## 1. 概要
EBISからエクスポートされたCSVファイルをBigQueryにロードするシステムの仕様を定義します。

## 2. 重要なポイント
- **エンコーディング**: EBISのCSVファイルはcp932（Shift-JIS）エンコーディングを使用
- **カラム名変換**: `売上金額` → `応募ID` などの日本語カラム名マッピングが必要
- **特殊文字処理**: 括弧や特殊文字をアンダースコアに置き換え（`間接効果2(発生日時)` → `間接効果2_発生日時`）
- **データ型変換**: 日本語日付形式（yyyy年mm月dd日）を標準形式（yyyy-mm-dd）に変換
- **アップサート処理**: 同一キー（応募ID）の既存レコードは更新、新規レコードは挿入
- **PYTHONPATH設定**: スクリプト実行前に`PYTHONPATH`環境変数にプロジェクトのルートディレクトリを設定する必要があります

## 3. 処理フロー
### ファイル構成と主要クラス・関数
メインの処理は以下のファイル、クラスと関数で実装されています：

1. **メイン処理・ブラウザ自動操作**: `src/main.py`
   - 自動ブラウザ操作によるCSVダウンロード処理を実行
   - `main()`: メイン実行関数（コマンドライン引数解析、EBISログイン、レポートダウンロード）
   - 関連クラス: `LoginPage`, `DetailedAnalysisPage`, `CVAttributePage`

2. **BigQueryロード処理**: `src/modules/bigquery/load_to_bigquery_fixed.py`
   - CSVファイルからBigQueryへのロード処理を担当
   - `load_data_to_bigquery(file_path, table_name, write_disposition)`: メインのローダー関数
   - `normalize_column_name(column_name)`: カラム名の正規化関数
   - `convert_date_format(date_str)`: 日付変換関数
   - `clean_integer_value(value)`: 数値型データ変換関数

3. **BigQueryクライアント**: `src/modules/bigquery/bigquery_client.py`
   - `BigQueryClient` クラス: BigQuery連携機能を提供
   - `load_from_gcs(source_uri, table_id, schema, dataset_id, write_disposition)`: GCSからのロード
   - `generate_query_with_japanese_columns(query, table_id, dataset_id)`: 日本語カラム名対応クエリ生成

4. **データローダー**: `src/modules/bigquery/data_loader.py`
   - `BigQueryDataLoader` クラス: データロード処理全体を担当
   - `load_data(csv_file_path, schema_file_path)`: CSVデータロード処理
   - `_transform_data(csv_data, schema_data)`: データ変換処理

5. **カラム名マッピング定義**: `src/modules/bigquery/column_mappings.py`
   - `get_cv_report_mappings()`: CVレポート用のマッピング定義を提供
   - `get_detailed_analysis_mappings()`: 詳細分析レポート用のマッピング定義を提供

6. **チャンク処理**: `src/modules/bigquery/process_in_chunks.py`
   - `process_in_chunks(csv_file, table_name, chunk_size, ...)`: 大きなCSVファイルを分割処理
   - カラムマッピング、日付・整数変換を適用してBigQueryにロード

7. **アップサート処理**: `src/modules/bigquery/upsert_to_bigquery.py`
   - `upsert_data_to_bigquery(file_path, table_name, key_column)`: キーカラム（応募ID）に基づく更新・挿入処理
   - 日本語形式の日付変換や数値変換も実装

### 処理の流れ
1. CSVファイル読み込み（cp932エンコーディング対応）：`load_data_to_bigquery`関数で実装
2. カラム名マッピング適用：`column_mappings.py`で定義、`process_in_chunks`関数で適用
3. データ型変換（日付・数値）：`convert_date_format`と`clean_integer_value`関数で実装
4. BigQueryへのアップロード（アップサート処理）：`BigQueryDataLoader.load_data`で実装

## 4. カラム名マッピング定義
基本カラムマッピング：
```python
{
    'ユーザーID': 'セッションID',
    'ユーザー名': '会員ID',
    '売上金額': '応募ID',  # この変換が特に重要
    '項目1': '教室名',
    '項目2': '学歴',
    '項目3': '都道府県',
    '項目4': '生年月日',
    '項目5': '現在の職業',
}
```

間接効果カラムのマッピング：
```python
# 間接効果2-10のカラムを動的に生成
for i in range(2, 11):
    prefix = f'間接効果{i}'
    mapping.update({
        f'{prefix}(発生日時)': f'{prefix}_発生日時',
        f'{prefix}(媒体種別)': f'{prefix}_媒体種別',
        f'{prefix}(広告グループ1)': f'{prefix}_広告グループ1',
        f'{prefix}(広告グループ2)': f'{prefix}_広告グループ2',
        f'{prefix}(広告ID)': f'{prefix}_広告ID',
        f'{prefix}(広告名)': f'{prefix}_広告名',
    })
```

## 5. 特殊文字処理の仕様
カラム名の特殊文字を処理する方法：
```python
def normalize_column_name(column_name):
    if isinstance(column_name, str):
        # 括弧や特殊文字をアンダースコアに置き換え
        normalized = column_name.replace('(', '_').replace(')', '')
                             .replace('（', '_').replace('）', '')
                             .replace(':', '_').replace(' ', '_')
        return normalized
    return column_name
```

## 6. 日付型データ変換仕様
日本語形式の日付変換：
```python
def convert_japanese_date(date_str):
    if not isinstance(date_str, str):
        return date_str
        
    # 日本語形式の日付（yyyy年mm月dd日）を検出
    pattern = r'(\d{4})年(\d{1,2})月(\d{1,2})日'
    match = re.match(pattern, date_str.strip())
    
    if match:
        year, month, day = match.groups()
        # 桁数が足りない場合はゼロ埋め
        month = month.zfill(2)
        day = day.zfill(2)
        return f"{year}-{month}-{day}"
    
    return date_str
```

## 7. 数値型データ変換仕様
数値型データのクリーニング：
```python
def clean_integer_value(value):
    # None値の処理
    if pd.isna(value):
        return None
    
    # 整数型はそのまま
    if isinstance(value, int):
        return value
    
    # 浮動小数点は整数に変換（小数点以下切り捨て）
    if isinstance(value, float):
        if not np.isfinite(value):  # 無限大やNaNはNoneに変換
            return None
        return int(value)
    
    # 文字列の場合
    if isinstance(value, str):
        # 空文字チェック
        if not value.strip():
            return None
            
        # カンマを削除して数値変換
        clean_value = value.replace(',', '').replace('"', '').strip()
        try:
            return int(float(clean_value))
        except ValueError:
            pass
    
    return None
```

## 8. BigQueryへのアップサートの重要ポイント
- 一時テーブルにデータをロードしてからマージクエリを実行
- キーカラム（応募ID）を基準に更新または挿入
- 日本語カラム名はバッククォートで囲む必要あり

## 9. エラー回避のための重要事項
1. **エンコーディング問題**:
   ```python
   try:
       df = pd.read_csv(file_path, encoding='utf-8')
   except UnicodeDecodeError:
       df = pd.read_csv(file_path, encoding='cp932')
   ```

2. **カラム名のミスマッチ**:
   - マッピング辞書に存在するキーのみを変換
   - スキーマにあるが、データフレームにないカラムはNone値で追加

3. **BigQuery接続エラー**:
   - サービスアカウントキーファイルのパスを正確に指定
   - 必要な権限（BigQuery Data Editor）が付与されているか確認

4. **日付変換エラー**:
   ```python
   # エラーが出ないよう明示的に変換前後の値チェック
   df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
   # NaTはNoneに変換
   df[date_column] = df[date_column].where(pd.notna(df[date_column]), None)
   ```

5. **PYTHONPATH設定に関するエラー**:
   - スクリプト実行前に必ずPYTHONPATHにプロジェクトのルートディレクトリを設定
   ```powershell
   $env:PYTHONPATH="C:\dev\CODE\EBIS_BIGQUERY"
   ```
   これがないとModuleNotFoundErrorが発生します。

## 10. メインロード処理の基本コード構造
```python
def load_csv_to_bigquery(csv_file, table_name, key_column='応募ID'):
    # 1. CSVファイル読み込み（エンコーディング対応）
    try:
        df = pd.read_csv(csv_file, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(csv_file, encoding='cp932')
        
    # 2. カラム名マッピング適用
    mapping = get_cv_report_mappings()['column_mapping']
    df = apply_column_mapping(df, mapping)
    
    # 3. カラム名の正規化
    df.columns = [normalize_column_name(col) for col in df.columns]
    
    # 4. データ型変換
    date_columns = get_cv_report_mappings()['date_columns']
    integer_columns = get_cv_report_mappings()['integer_columns']
    
    df = process_date_columns(df, date_columns)
    df = process_integer_columns(df, integer_columns)
    
    # 5. BigQueryへのアップロード
    result = upsert_to_bigquery(df, table_name, key_column)
    
    return result
```

## 11. チャンク処理による大規模CSVファイルの処理
大きなCSVファイルを効率的に処理するため、`process_in_chunks.py`を使用してファイルを分割して処理できます：

```powershell
# PowerShellでの実行例
cd C:\dev\CODE\EBIS_BIGQUERY
$env:PYTHONPATH="C:\dev\CODE\EBIS_BIGQUERY"
python -m src.modules.bigquery.process_in_chunks data\20250326_ebis_CVrepo.csv cv_report_test --chunk-size 1000 --write-disposition WRITE_TRUNCATE
```

チャンク処理の特徴:
- CSVファイルを指定された行数単位で分割して処理
- 初回チャンクはテーブルをTRUNCATE（または指定された書き込み方式）
- 後続チャンクはテーブルにAPPEND
- エラーが発生しても処理を継続し、成功・失敗を記録
- カラム名マッピングを完全に適用（`column_mappings.py`から取得）

## 12. 注意事項とよくある問題
1. カラム名のマッピングが正しく適用されず、BigQueryでNULL値が発生する問題
   - `process_in_chunks.py`のmain関数で`get_cv_report_mappings()`から取得したマッピングを使用していることを確認
   - マッピング辞書に必要なカラムがすべて含まれていることを確認

2. ファイルパスの指定
   - 相対パスではなく絶対パスを使用することを推奨
   - パス区切り文字はWindowsでは`\`、Unix系では`/`

3. BigQueryテーブルが存在しない場合
   - 初回実行時はテーブルが自動的に作成されます
   - テーブル名は`データセット.テーブル名`の形式で指定

4. 環境変数ファイルの設定
   - デフォルトでは`config/secrets.env`ファイルから環境変数を読み込み
   - 必要に応じて`--env-file`パラメータで指定可能 