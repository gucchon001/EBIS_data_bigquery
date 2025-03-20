#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Google Spreadsheetを操作するためのユーティリティモジュール

このモジュールは、Google Spreadsheetへの接続、データの読み書き、
CSVファイルからのデータインポートなどの機能を提供します。
"""

import os
import csv
import time
import configparser
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError, SpreadsheetNotFound

from src.utils.logging_config import get_logger
from src.utils.environment import EnvironmentUtils as env

logger = get_logger(__name__)

class SpreadsheetManager:
    """
    Google Spreadsheetを操作するためのクラス
    
    このクラスは、Google Spreadsheetへの接続、データの読み書き、
    CSVファイルからのデータインポートなどの機能を提供します。
    """
    
    def __init__(self, credential_path: str = None):
        """
        SpreadsheetManagerの初期化
        
        Args:
            credential_path (str, optional): サービスアカウントのJSONファイルパス。
                                           指定しない場合はデフォルトのパスを使用。
        """
        # スプレッドシートIDを設定ファイルから取得
        self.spreadsheet_id = env.get_config_value('SPREADSHEET', 'SSID').strip('"\'')
        
        # 認証情報の設定
        if (credential_path is None):
            try:
                env.load_env()
            except Exception as e:
                logger.warning(f"Failed to load environment: {e}")
            credential_path = str(env.get_service_account_file())
        
        # 認証情報ファイルの存在確認
        if not os.path.exists(credential_path):
            logger.warning(f"指定された認証情報ファイルが存在しません: {credential_path}")
            # ファイル名の変更を試みる（設定ファイルの名前とファイルの実際の名前が異なる場合）
            base_dir = env.get_project_root()
            potential_files = [
                os.path.join(base_dir, 'config', 'boxwood-dynamo-384411-6dec80faabfc.json'),
                os.path.join(base_dir, 'config', 'service_account.json')
            ]
            
            for potential_file in potential_files:
                if os.path.exists(potential_file):
                    credential_path = potential_file
                    logger.info(f"代替の認証情報ファイルを使用します: {credential_path}")
                    break
        
        self.credential_path = credential_path
        self.client = self._authenticate()
        self.spreadsheet = None
        
        logger.info(f"SpreadsheetManager initialized with spreadsheet ID: {self.spreadsheet_id}")
        logger.info(f"Using credential file: {self.credential_path}")
    
    def _authenticate(self) -> gspread.Client:
        """
        Google APIに認証する
        
        Returns:
            gspread.Client: 認証済みのgspreadクライアント
        """
        try:
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            credentials = Credentials.from_service_account_file(
                self.credential_path, 
                scopes=scopes
            )
            
            client = gspread.authorize(credentials)
            logger.info("Successfully authenticated with Google API")
            return client
            
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def open_spreadsheet(self) -> gspread.Spreadsheet:
        """
        スプレッドシートを開く
        
        Returns:
            gspread.Spreadsheet: 開いたスプレッドシート
        """
        try:
            self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            logger.info(f"Successfully opened spreadsheet: {self.spreadsheet.title}")
            return self.spreadsheet
            
        except SpreadsheetNotFound:
            logger.error(f"Spreadsheet not found with ID: {self.spreadsheet_id}")
            raise
        except Exception as e:
            logger.error(f"Failed to open spreadsheet: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def get_worksheet(self, sheet_key: str) -> gspread.Worksheet:
        """
        ワークシートを取得する
        
        Args:
            sheet_key (str): シート名またはシートのキー
                           （'entryprocess_all', 'users_all', 'logging', 'data_ep'など）
            
        Returns:
            gspread.Worksheet: 取得したワークシート
        """
        if self.spreadsheet is None:
            self.open_spreadsheet()
        
        # settings.iniから対応するシート名を取得
        sheet_name = None
        try:
            # 引数として渡されたsheet_keyがsettings.iniで定義されている「値」と一致するか確認
            # SHEET_NAMESセクションの全キーを取得
            sheet_name_configs = env.get_config_file()
            config = configparser.ConfigParser()
            config.read(str(sheet_name_configs), encoding='utf-8')
            
            if 'SHEET_NAMES' in config:
                sheet_name_dict = dict(config['SHEET_NAMES'])
                
                # 値としてsheet_keyと一致するものを探す
                for config_key, config_value in sheet_name_dict.items():
                    # 設定ファイルの値は引用符で囲まれていることがあるので削除する
                    clean_value = config_value.strip('"\'')
                    if clean_value == sheet_key:
                        logger.debug(f"シートキー '{sheet_key}' は設定ファイルに存在しています")
                        sheet_name = sheet_key
                        break
            
            if not sheet_name:
                # 見つからなかった場合は直接シート名として使用
                sheet_name = sheet_key
                logger.debug(f"シートキー '{sheet_key}' を直接シート名として使用します")
                
        except Exception as e:
            logger.warning(f"設定ファイルからシートキー '{sheet_key}' の解決に失敗しました: {str(e)}")
            sheet_name = sheet_key  # 設定から取得できない場合は直接シート名として使用
        
        try:
            worksheet = self.spreadsheet.worksheet(sheet_name)
            logger.info(f"Successfully got worksheet: {sheet_name}")
            return worksheet
            
        except Exception as e:
            logger.error(f"Failed to get worksheet '{sheet_name}': {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def get_worksheet_by_gid(self, gid: int) -> gspread.Worksheet:
        """
        GIDを使ってワークシートを取得する
        
        Args:
            gid (int): ワークシートのGID
            
        Returns:
            gspread.Worksheet: 取得したワークシート
            
        Raises:
            ValueError: 指定したGIDのワークシートが見つからない場合
        """
        if self.spreadsheet is None:
            self.open_spreadsheet()
        
        try:
            worksheets = self.spreadsheet.worksheets()
            for sheet in worksheets:
                if sheet.id == gid:
                    logger.info(f"Successfully got worksheet with GID {gid}: '{sheet.title}'")
                    return sheet
            
            # 指定したGIDが見つからない場合
            logger.error(f"Worksheet with GID {gid} not found")
            raise ValueError(f"Worksheet with GID {gid} not found")
            
        except Exception as e:
            logger.error(f"Failed to get worksheet with GID {gid}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def clear_worksheet(self, sheet_key: str) -> None:
        """
        ワークシートのデータをクリアする
        
        Args:
            sheet_key (str): シート名またはシートのキー
        """
        worksheet = self.get_worksheet(sheet_key)
        
        try:
            # ヘッダー行を保持するため、2行目以降をクリア
            if worksheet.row_count > 1:
                worksheet.batch_clear(["A2:ZZ"])
                logger.info(f"Successfully cleared worksheet: {worksheet.title}")
            else:
                logger.warning(f"Worksheet {worksheet.title} has no data to clear")
                
        except Exception as e:
            logger.error(f"Failed to clear worksheet: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def import_csv_to_sheet(self, csv_path: str, sheet_key: str, has_header: bool = True) -> None:
        """
        CSVファイルからデータをシートにインポートする
        
        Args:
            csv_path (str): CSVファイルのパス
            sheet_key (str): シートのキー ('users_all', 'entryprocess_all', 'logging')
            has_header (bool, optional): CSVファイルにヘッダーがあるかどうか。デフォルトはTrue。
        """
        if not os.path.exists(csv_path):
            logger.error(f"CSV file not found: {csv_path}")
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
        worksheet = self.get_worksheet(sheet_key)
        
        try:
            # CSVファイルを読み込む（複数の文字コードを試す）
            encodings = ['utf-8-sig', 'utf-8', 'shift-jis', 'cp932']
            data = None
            used_encoding = None
            
            for encoding in encodings:
                try:
                    with open(csv_path, 'r', encoding=encoding) as f:
                        csv_reader = csv.reader(f)
                        data = list(csv_reader)
                    used_encoding = encoding
                    logger.info(f"Successfully read CSV file with encoding: {encoding}")
                    break
                except UnicodeDecodeError:
                    logger.warning(f"Failed to read CSV file with encoding: {encoding}")
                    continue
            
            if data is None:
                logger.error("Failed to read CSV file with any encoding")
                raise UnicodeError("Failed to read CSV file with any encoding")
            
            if not data:
                logger.warning(f"CSV file is empty: {csv_path}")
                return
            
            # データの行数と列数を確認
            row_count = len(data)
            col_count = max(len(row) for row in data) if data else 0
            logger.info(f"CSV data: {row_count} rows, {col_count} columns")
            
            # ヘッダー行の処理
            start_row = 1
            if has_header:
                # ヘッダー行を更新
                header = data[0]
                logger.info(f"Header row: {header}")
                worksheet.update('A1', [header])
                # データは2行目から
                data = data[1:]
                start_row = 2
            
            # データが空の場合は終了
            if not data:
                logger.warning(f"CSV file has no data rows: {csv_path}")
                return
            
            # データを一括でアップロード
            if data:
                # APIの制限に対応するため、一度に更新する行数を制限
                batch_size = 1000  # Google Sheets APIの制限に基づく適切な値
                total_batches = (len(data) + batch_size - 1) // batch_size  # 切り上げ除算
                
                for i in range(0, len(data), batch_size):
                    batch_num = i // batch_size + 1
                    logger.info(f"Uploading batch {batch_num}/{total_batches} ({len(data[i:i+batch_size])} rows)")
                    
                    batch_data = data[i:i+batch_size]
                    range_str = f'A{start_row + i}:ZZ{start_row + i + len(batch_data) - 1}'
                    
                    try:
                        worksheet.update(range_str, batch_data)
                        logger.info(f"Successfully updated range: {range_str}")
                    except Exception as e:
                        logger.error(f"Failed to update range {range_str}: {str(e)}")
                        # エラーが発生しても処理を継続
                        import traceback
                        logger.error(traceback.format_exc())
                    
                    # API制限に引っかからないよう少し待機
                    if i + batch_size < len(data):
                        time.sleep(1)
            
            logger.info(f"Successfully imported {len(data)} rows from CSV to worksheet: {worksheet.title}")
            
        except Exception as e:
            logger.error(f"Failed to import CSV to worksheet: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def append_log(self, log_data: List[str]) -> None:
        """
        ログシートにデータを追加する
        
        Args:
            log_data (List[str]): 追加するログデータ（1行分）
        """
        worksheet = self.get_worksheet('logging')
        
        try:
            worksheet.append_row(log_data)
            logger.info(f"Successfully appended log data: {log_data}")
            
        except Exception as e:
            logger.error(f"Failed to append log data: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            # ログの追加に失敗してもプログラムは継続 