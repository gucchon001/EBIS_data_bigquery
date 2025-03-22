#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
BigQueryデータローダーの単体テスト

以下の機能をテストします：
- Excelシリアル値の日時変換
- CSVスキーマの読み込みと解析
- BigQueryスキーマへの変換
- 特殊文字の置換処理
- データのロード処理（モックを使用）
"""

import os
import sys
import csv
import json
import tempfile
import datetime
import pytest
from unittest import mock
from pathlib import Path

# テスト対象のモジュールへのパスを追加
module_path = Path(__file__).resolve().parent.parent
if str(module_path) not in sys.path:
    sys.path.insert(0, str(module_path))

from src.load_to_bigquery import (
    excel_to_datetime,
    read_csv_schema,
    convert_to_bigquery_schema,
    read_data_csv,
    load_data_to_bigquery,
    save_schema_json
)

# テストデータのパス
TEST_DATA_DIR = Path(__file__).resolve().parent / "test_data"
SAMPLE_SCHEMA_CSV = TEST_DATA_DIR / "sample_schema.csv"

class TestExcelToDatetime:
    """Excelシリアル値の日時変換テスト"""
    
    def test_valid_excel_date(self):
        """正常なExcelシリアル値の変換テスト"""
        # 2025/03/22 23:56:49 相当のシリアル値
        result = excel_to_datetime("45737.99779")
        assert isinstance(result, datetime.datetime)
        assert result.year == 2025
        assert result.month == 3
        assert result.day == 22
        assert result.hour == 23
        assert result.minute == 56
        assert 45 <= result.second <= 50  # 小数点以下の丸め誤差を考慮
    
    def test_empty_input(self):
        """空の入力テスト"""
        result = excel_to_datetime("")
        assert result == ""
        
        result = excel_to_datetime("  ")
        assert result == ""
    
    def test_invalid_input(self):
        """無効な入力テスト"""
        result = excel_to_datetime("invalid")
        assert result is None
        
    def test_pre_1900_march_bug(self):
        """1900年のうるう年バグ（3月1日以前）テスト"""
        # 1900年2月28日相当のシリアル値
        result = excel_to_datetime("59")
        assert result.year == 1900
        assert result.month == 2
        assert result.day == 28
        
    def test_post_1900_march_bug(self):
        """1900年のうるう年バグ（3月1日以降）テスト"""
        # 1900年3月1日相当のシリアル値（60をスキップ）
        result = excel_to_datetime("61")
        assert result.year == 1900
        assert result.month == 3
        assert result.day == 1

class TestReadCsvSchema:
    """CSVスキーマの読み込みテスト"""
    
    def test_read_valid_schema(self):
        """正常なスキーマCSVの読み込みテスト"""
        schema_data = read_csv_schema(str(SAMPLE_SCHEMA_CSV))
        
        assert len(schema_data) == 12  # サンプルCSVには12行のデータがある
        
        # 最初のフィールドを確認
        assert schema_data[0]["name"] == "CV名"
        assert schema_data[0]["type"] == "str"
        assert schema_data[0]["sample"] == "応募完了"
        
        # タイムスタンプフィールドを確認
        timestamp_field = next(field for field in schema_data if field["type"] == "timestamp")
        assert timestamp_field["name"] == "CV時間"
        assert timestamp_field["sample"] == "45737.99779"
        
    def test_read_nonexistent_file(self):
        """存在しないファイルの読み込みテスト"""
        with pytest.raises(Exception):
            read_csv_schema("nonexistent_file.csv")

class TestConvertToBigQuerySchema:
    """BigQueryスキーマへの変換テスト"""
    
    def test_schema_conversion(self):
        """スキーマ変換のテスト"""
        input_schema = [
            {"name": "normal_field", "type": "str", "sample": "test"},
            {"name": "number_field", "type": "int", "sample": "123"},
            {"name": "time_field", "type": "timestamp", "sample": "45737.99779"},
            {"name": "special chars!?", "type": "str", "sample": "special"},
            {"name": "（括弧）フィールド", "type": "str", "sample": "parens"},
            {"name": "1starts_with_number", "type": "int", "sample": "456"}
        ]
        
        result = convert_to_bigquery_schema(input_schema)
        
        assert len(result) == 6
        
        # 通常フィールドの確認
        assert result[0]["name"] == "normal_field"
        assert result[0]["type"] == "STRING"
        
        # 数値フィールドの確認
        assert result[1]["name"] == "number_field"
        assert result[1]["type"] == "INTEGER"
        
        # タイムスタンプフィールドの確認
        assert result[2]["name"] == "time_field"
        assert result[2]["type"] == "TIMESTAMP"
        
        # 特殊文字を含むフィールドの確認
        assert result[3]["name"] == "special_chars__"
        assert result[3]["type"] == "STRING"
        
        # 括弧を含むフィールドの確認
        assert result[4]["name"] == "________"
        assert result[4]["type"] == "STRING"
        
        # 数字から始まるフィールドの確認
        assert result[5]["name"] == "_1starts_with_number"
        assert result[5]["type"] == "INTEGER"

class TestReadDataCsv:
    """データCSVの読み込みテスト"""
    
    def setup_method(self):
        """テスト用のCSVファイルを作成"""
        self.temp_csv = tempfile.NamedTemporaryFile(mode="w+", suffix=".csv", delete=False)
        
        # テストデータの書き込み
        writer = csv.writer(self.temp_csv)
        writer.writerow(["CV名", "CV時間", "ユーザーID", "売上金額"])
        writer.writerow(["応募完了", "45737.99779", "user1", "1000"])
        writer.writerow(["購入", "45738.5", "user2", "2000"])
        self.temp_csv.close()
        
    def teardown_method(self):
        """一時ファイルの削除"""
        os.unlink(self.temp_csv.name)
    
    def test_read_data_csv(self):
        """データCSVの読み込みテスト"""
        schema_data = [
            {"name": "CV名", "type": "str", "sample": "応募完了"},
            {"name": "CV時間", "type": "timestamp", "sample": "45737.99779"},
            {"name": "ユーザーID", "type": "str", "sample": "user1"},
            {"name": "売上金額", "type": "int", "sample": "1000"}
        ]
        
        result = read_data_csv(self.temp_csv.name, schema_data)
        
        assert len(result) == 2
        
        # 1行目の確認
        assert result[0]["CV名"] == "応募完了"
        assert "T23:56" in result[0]["CV時間"]  # タイムスタンプ変換の確認（時間部分のみ）
        assert result[0]["ユーザーID"] == "user1"
        assert result[0]["売上金額"] == 1000
        
        # 2行目の確認
        assert result[1]["CV名"] == "購入"
        assert result[1]["ユーザーID"] == "user2"
        assert result[1]["売上金額"] == 2000

class TestSaveSchemaJson:
    """スキーマJSONの保存テスト"""
    
    def test_save_schema_json(self):
        """スキーマJSONの保存テスト"""
        schema = [
            {"name": "test_field", "type": "STRING", "mode": "NULLABLE"},
            {"name": "test_field2", "type": "INTEGER", "mode": "NULLABLE"}
        ]
        
        # 一時的な出力先ディレクトリを作成
        with tempfile.TemporaryDirectory() as temp_dir:
            # data/schemaへのパスをモック
            with mock.patch("pathlib.Path", side_effect=lambda p: Path(temp_dir) if p == "data/schema" else Path(p)):
                result = save_schema_json(schema, "test_table")
                
                # 生成されたJSONファイルのパスを取得
                json_file_path = Path(result)
                
                # ファイルが存在することを確認
                assert json_file_path.exists()
                
                # ファイル内容を確認
                with open(json_file_path, "r", encoding="utf-8") as f:
                    loaded_schema = json.load(f)
                    assert len(loaded_schema) == 2
                    assert loaded_schema[0]["name"] == "test_field"
                    assert loaded_schema[1]["name"] == "test_field2"

class TestLoadDataToBigQuery:
    """BigQueryへのデータロードテスト（モック使用）"""
    
    @mock.patch("src.load_to_bigquery.initialize_bigquery_client")
    def test_load_data_to_bigquery(self, mock_init_client):
        """BigQueryへのデータロードテスト"""
        # BigQueryクライアントのモック
        mock_client = mock.MagicMock()
        mock_init_client.return_value = mock_client
        
        # データセット参照のモック
        mock_dataset_ref = mock.MagicMock()
        mock_client.dataset.return_value = mock_dataset_ref
        
        # テーブル参照のモック
        mock_table_ref = mock.MagicMock()
        mock_dataset_ref.table.return_value = mock_table_ref
        
        # テーブルのモック
        mock_table = mock.MagicMock()
        mock_client.create_table.return_value = mock_table
        
        # テーブル取得の例外（テーブルが存在しない場合）
        from google.cloud.exceptions import NotFound
        mock_client.get_table.side_effect = NotFound("Table not found")
        
        # 一時ファイルをモック
        with mock.patch("tempfile.NamedTemporaryFile") as mock_tempfile:
            # 一時ファイルのモック
            mock_temp = mock.MagicMock()
            mock_tempfile.return_value.__enter__.return_value = mock_temp
            mock_temp.name = "temp_file.jsonl"
            
            # 環境変数ユーティリティをモック
            with mock.patch("src.load_to_bigquery.EnvironmentUtils") as mock_env:
                mock_env.get_bigquery_settings.return_value = {
                    "project_id": "test-project",
                    "dataset_id": "test_dataset",
                    "key_path": "test/key.json"
                }
                
                # テスト実行
                data_rows = [
                    {"field1": "value1", "field2": 123},
                    {"field1": "value2", "field2": 456}
                ]
                
                schema = [
                    {"name": "field1", "type": "STRING", "mode": "NULLABLE"},
                    {"name": "field2", "type": "INTEGER", "mode": "NULLABLE"}
                ]
                
                load_data_to_bigquery(data_rows, schema, "test_table")
                
                # BigQueryクライアントが正しく初期化されたか確認
                mock_init_client.assert_called_once()
                
                # データセットとテーブルの参照が正しく作成されたか確認
                mock_client.dataset.assert_called_once_with("test_dataset")
                mock_dataset_ref.table.assert_called_once_with("test_table")
                
                # テーブルが作成されたか確認
                mock_client.create_table.assert_called_once()
                
                # load_table_from_fileが呼ばれたか確認
                mock_client.load_table_from_file.assert_called_once()

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 