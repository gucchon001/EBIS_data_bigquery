#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BigQueryデータローダーのテスト

詳細分析レポートのBigQueryへのデータロード機能をテストします。
"""

import os
import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
import datetime
from io import StringIO

from src.modules.bigquery.data_loader import BigQueryDataLoader

class TestBigQueryDataLoader(unittest.TestCase):
    """
    BigQueryDataLoaderクラスのテスト
    """
    
    def setUp(self):
        """
        テスト前の準備
        """
        # テスト用の設定
        self.project_id = "test-project"
        self.dataset_id = "test_dataset"
        self.table_id = "test_table"
        self.service_account_path = "path/to/service_account.json"
        
        # モックパッチの適用
        self.client_patch = patch('src.modules.bigquery.data_loader.bigquery.Client')
        self.mock_client = self.client_patch.start()
        
        self.env_patch = patch('src.modules.bigquery.data_loader.EnvironmentUtils')
        self.mock_env = self.env_patch.start()
        self.mock_env.resolve_path.return_value = '/resolved/path'
        
        self.mappings_patch = patch('src.modules.bigquery.data_loader.get_detailed_analysis_mappings')
        self.mock_mappings = self.mappings_patch.start()
        self.mock_mappings.return_value = {
            'column_mapping': {
                '日付': '日付',
                'チャネル種別': 'チャネル名',
                '表示回数': '表示',
                'クリック／流入回数': 'クリック数'
            },
            'date_columns': ['日付', 'データ取得日'],
            'integer_columns': ['表示', 'クリック数']
        }
        
        # テスト対象オブジェクトの作成
        self.loader = BigQueryDataLoader(
            self.project_id, 
            self.dataset_id, 
            self.table_id, 
            self.service_account_path
        )
    
    def tearDown(self):
        """
        テスト後のクリーンアップ
        """
        self.client_patch.stop()
        self.env_patch.stop()
        self.mappings_patch.stop()
    
    def test_parse_date(self):
        """
        _parse_date メソッドのテスト
        """
        # 正常な日付形式のテスト
        self.assertEqual(
            self.loader._parse_date('2023-01-15'),
            datetime.date(2023, 1, 15)
        )
        
        self.assertEqual(
            self.loader._parse_date('2023/01/15'),
            datetime.date(2023, 1, 15)
        )
        
        # 無効な日付形式のテスト
        self.assertIsNone(self.loader._parse_date('invalid-date'))
        self.assertIsNone(self.loader._parse_date('2023.01.15'))
    
    @patch('builtins.open', new_callable=mock_open, read_data=json.dumps([
        {"name": "date", "type": "DATE", "description": "日付", "mode": "NULLABLE"},
        {"name": "channel_name", "type": "STRING", "description": "チャネル名", "mode": "NULLABLE"}
    ]))
    def test_load_schema_from_file(self, mock_file):
        """
        _load_schema_from_file メソッドのテスト
        """
        schema = self.loader._load_schema_from_file('test_schema.json')
        
        self.assertEqual(len(schema), 2)
        self.assertEqual(schema[0]['name'], 'date')
        self.assertEqual(schema[1]['type'], 'STRING')
        
        mock_file.assert_called_once_with('/resolved/path', 'r', encoding='utf-8')
    
    @patch('src.modules.bigquery.data_loader.bigquery.SchemaField')
    def test_convert_schema_to_bigquery_format(self, mock_schema_field):
        """
        _convert_schema_to_bigquery_format メソッドのテスト
        """
        schema_data = [
            {"name": "date", "type": "DATE", "description": "日付", "mode": "NULLABLE"},
            {"name": "channel_name", "type": "STRING", "description": "チャネル名", "mode": "NULLABLE"}
        ]
        
        # モックの戻り値を設定
        mock_schema_field.side_effect = lambda **kwargs: kwargs
        
        result = self.loader._convert_schema_to_bigquery_format(schema_data)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['name'], 'date')
        self.assertEqual(result[0]['field_type'], 'DATE')
        self.assertEqual(result[1]['name'], 'channel_name')
        self.assertEqual(result[1]['field_type'], 'STRING')
    
    @patch('src.modules.bigquery.data_loader.csv.DictReader')
    def test_read_csv_data(self, mock_reader):
        """
        _read_csv_data メソッドのテスト
        """
        # CSVデータのモック
        mock_reader.return_value = [
            {'日付': '2023-01-15', 'チャネル種別': 'Organic', '表示回数': '1000', 'クリック／流入回数': '50'},
            {'日付': '2023-01-16', 'チャネル種別': 'Paid', '表示回数': '2000', 'クリック／流入回数': '100'}
        ]
        
        # openのモック
        with patch('builtins.open', mock_open()) as mock_file:
            csv_data, dates = self.loader._read_csv_data('test.csv')
            
            # 結果の検証
            self.assertEqual(len(csv_data), 2)
            self.assertEqual(csv_data[0]['チャネル名'], 'Organic')
            self.assertEqual(csv_data[1]['表示'], '2000')
            
            # 日付リストの検証
            self.assertEqual(len(dates), 2)
            self.assertIn(datetime.date(2023, 1, 15), dates)
            self.assertIn(datetime.date(2023, 1, 16), dates)
    
    def test_transform_data(self):
        """
        _transform_data メソッドのテスト
        """
        # 入力データ
        csv_data = [
            {'日付': '2023-01-15', 'チャネル名': 'Organic', '表示': '1,000', 'クリック数': '50'},
            {'日付': '2023-01-16', 'チャネル名': 'Paid', '表示': '2,000', 'クリック数': ''}
        ]
        
        # スキーマ
        schema = [
            {"name": "date", "type": "DATE", "description": "日付", "mode": "NULLABLE"},
            {"name": "channel_name", "type": "STRING", "description": "チャネル名", "mode": "NULLABLE"},
            {"name": "impressions", "type": "INTEGER", "description": "表示", "mode": "NULLABLE"},
            {"name": "clicks", "type": "INTEGER", "description": "クリック数", "mode": "NULLABLE"}
        ]
        
        # データ変換
        transformed_data = self.loader._transform_data(csv_data, schema)
        
        # 結果の検証
        self.assertEqual(len(transformed_data), 2)
        
        # 日付の変換検証
        self.assertEqual(transformed_data[0]['date'], datetime.date(2023, 1, 15))
        
        # 整数の変換検証（カンマ除去）
        self.assertEqual(transformed_data[0]['impressions'], 1000)
        self.assertEqual(transformed_data[0]['clicks'], 50)
        
        # 空の値はNoneに変換されることを確認
        self.assertIsNone(transformed_data[1]['clicks'])
    
    def test_filter_new_data(self):
        """
        _filter_new_data メソッドのテスト
        """
        # 既存の日付
        existing_dates = [datetime.date(2023, 1, 15), datetime.date(2023, 1, 17)]
        
        # 変換済みデータ
        data = [
            {'date': datetime.date(2023, 1, 15), 'channel_name': 'Organic'},  # 既存
            {'date': datetime.date(2023, 1, 16), 'channel_name': 'Paid'},     # 新規
            {'date': datetime.date(2023, 1, 17), 'channel_name': 'Social'},   # 既存
            {'date': datetime.date(2023, 1, 18), 'channel_name': 'Email'}     # 新規
        ]
        
        # フィルタリング
        filtered_data = self.loader._filter_new_data(data, existing_dates)
        
        # 結果の検証
        self.assertEqual(len(filtered_data), 2)
        self.assertEqual(filtered_data[0]['date'], datetime.date(2023, 1, 16))
        self.assertEqual(filtered_data[1]['date'], datetime.date(2023, 1, 18))
    
    @patch('src.modules.bigquery.data_loader.BigQueryDataLoader._load_schema_from_file')
    @patch('src.modules.bigquery.data_loader.BigQueryDataLoader._convert_schema_to_bigquery_format')
    @patch('src.modules.bigquery.data_loader.BigQueryDataLoader._get_existing_dates')
    @patch('src.modules.bigquery.data_loader.BigQueryDataLoader._read_csv_data')
    @patch('src.modules.bigquery.data_loader.BigQueryDataLoader._transform_data')
    @patch('src.modules.bigquery.data_loader.BigQueryDataLoader._filter_new_data')
    def test_load_data(self, mock_filter, mock_transform, mock_read, mock_get_dates, 
                      mock_convert, mock_load_schema):
        """
        load_data メソッドのテスト
        """
        # モックの設定
        mock_load_schema.return_value = [{"name": "test_field", "type": "STRING"}]
        mock_convert.return_value = ["converted_schema"]
        mock_get_dates.return_value = [datetime.date(2023, 1, 15)]
        mock_read.return_value = (
            [{"field1": "value1"}],  # CSVデータ
            [datetime.date(2023, 1, 16)]  # 日付リスト
        )
        mock_transform.return_value = [{"transformed_field": "value"}]
        mock_filter.return_value = [{"new_data": "value"}]
        
        # ロードジョブのモック
        self.loader.client.load_table_from_json.return_value = MagicMock()
        
        # テスト実行
        result = self.loader.load_data("test.csv", "schema.json")
        
        # 検証
        self.assertEqual(result, 1)  # 新規データは1行
        
        # 各モックが呼ばれたことを確認
        mock_load_schema.assert_called_once()
        mock_convert.assert_called_once()
        mock_get_dates.assert_called_once()
        mock_read.assert_called_once()
        mock_transform.assert_called_once()
        mock_filter.assert_called_once()
        
        # BigQueryのロードが呼ばれたことを確認
        self.loader.client.load_table_from_json.assert_called_once()

if __name__ == '__main__':
    unittest.main() 