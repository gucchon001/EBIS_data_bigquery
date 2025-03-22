#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
GCSファイルのカラム名前処理モジュール

GCSからファイルをダウンロードし、カラム名の前処理（カッコや特殊文字の置換）を行い、
BigQueryでロードできるようにするユーティリティを提供します。
"""

import os
import sys
import re
import csv
import tempfile
import pandas as pd
from pathlib import Path
from loguru import logger
from google.cloud import storage
from google.oauth2 import service_account

# プロジェクトのルートディレクトリをシステムパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.utils.environment import EnvironmentUtils

class GCSFilePreprocessor:
    """
    GCSファイルの前処理を行うクラス
    特にカラム名の処理（カッコや特殊文字の処理）に特化しています
    """

    def __init__(self):
        """初期化処理"""
        # GCSキーファイルのパスを解決
        gcs_key_path = EnvironmentUtils.get_env_var("GCS_KEY_PATH")
        key_path = Path(EnvironmentUtils.get_project_root()) / gcs_key_path
        
        if not key_path.exists():
            raise FileNotFoundError(f"GCS認証キーファイルが見つかりません: {key_path}")
        
        # 認証情報とクライアントを作成
        credentials = service_account.Credentials.from_service_account_file(key_path)
        self.storage_client = storage.Client(credentials=credentials)
        
        # 一時ディレクトリの準備
        self.temp_dir = tempfile.mkdtemp(prefix="gcs_preprocess_")
        logger.info(f"一時ディレクトリを作成しました: {self.temp_dir}")

    def cleanup(self):
        """一時ファイルをクリーンアップします"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            logger.info(f"一時ディレクトリを削除しました: {self.temp_dir}")

    def download_from_gcs(self, gcs_uri):
        """
        GCSからファイルをダウンロードします
        
        Args:
            gcs_uri (str): GCSファイルのURI（例: gs://bucket_name/path/to/file.csv）
            
        Returns:
            str: ダウンロードしたローカルファイルのパス
        """
        # URIからバケット名とオブジェクト名を抽出
        if gcs_uri.startswith("gs://"):
            bucket_path = gcs_uri[5:]  # "gs://" を削除
        else:
            bucket_path = gcs_uri
            
        parts = bucket_path.split("/", 1)
        bucket_name = parts[0]
        blob_name = parts[1] if len(parts) > 1 else None
        
        if not blob_name:
            raise ValueError(f"無効なGCS URI: {gcs_uri}")
        
        # ダウンロード先のローカルファイルパスを生成
        filename = os.path.basename(blob_name)
        local_path = os.path.join(self.temp_dir, filename)
        
        # GCSからダウンロード
        bucket = self.storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.download_to_filename(local_path)
        
        logger.info(f"ファイルをダウンロードしました: {gcs_uri} -> {local_path}")
        return local_path

    def upload_to_gcs(self, local_path, gcs_uri):
        """
        ローカルファイルをGCSにアップロードします
        
        Args:
            local_path (str): アップロードするローカルファイルのパス
            gcs_uri (str): アップロード先のGCS URI
            
        Returns:
            str: アップロードしたGCSのURI
        """
        # URIからバケット名とオブジェクト名を抽出
        if gcs_uri.startswith("gs://"):
            bucket_path = gcs_uri[5:]  # "gs://" を削除
        else:
            bucket_path = gcs_uri
            
        parts = bucket_path.split("/", 1)
        bucket_name = parts[0]
        blob_name = parts[1] if len(parts) > 1 else None
        
        if not blob_name:
            raise ValueError(f"無効なGCS URI: {gcs_uri}")
        
        # GCSにアップロード
        bucket = self.storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(local_path)
        
        logger.info(f"ファイルをアップロードしました: {local_path} -> gs://{bucket_name}/{blob_name}")
        return f"gs://{bucket_name}/{blob_name}"

    def sanitize_column_name(self, column_name):
        """
        カラム名をBigQuery用に整形します
        カッコや特殊文字を置換します
        
        Args:
            column_name (str): 元のカラム名
            
        Returns:
            str: 整形後のカラム名
        """
        # 特殊文字チェック (文字化けも含む)
        if any(ord(c) > 127 for c in column_name) and re.search(r'[^\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\uFF00-\uFFEFA-Za-z0-9_]', column_name):
            # 文字化けかもしれない - 一般的な日本語の文字範囲外の文字を含む
            # 完全に文字化けしていると判断される場合は代替名を使用
            if sum(1 for c in column_name if re.match(r'[^\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\uFF00-\uFFEFA-Za-z0-9_]', c)) > len(column_name) / 2:
                # 半分以上が特殊文字なら文字化けと判断
                return f"column_{hash(column_name) % 10000:04d}"
        
        # カッコの置換
        sanitized = re.sub(r'[\(\)\[\]\{\}<>]', '_', column_name)
        
        # その他の特殊文字の置換
        sanitized = re.sub(r'[^A-Za-z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\uFF00-\uFFEF_]', '_', sanitized)
        
        # 連続するアンダースコアを1つにまとめる
        sanitized = re.sub(r'_+', '_', sanitized)
        
        # 先頭や末尾のアンダースコアを削除
        sanitized = sanitized.strip('_')
        
        # 空文字列になった場合は代替名を使用
        if not sanitized:
            sanitized = f"column_{hash(column_name) % 10000:04d}"
            
        logger.debug(f"カラム名を整形: '{column_name}' -> '{sanitized}'")
        return sanitized

    def preprocess_csv(self, gcs_uri):
        """
        CSVファイルのカラム名を前処理します
        
        Args:
            gcs_uri (str): 処理するCSVファイルのGCS URI
            
        Returns:
            str: 前処理後のCSVファイルのGCS URI
        """
        try:
            # GCSからファイルをダウンロード
            local_path = self.download_from_gcs(gcs_uri)
            
            # CSVファイルを読み込み
            df = None
            
            # 複数のエンコーディングを試す
            encodings = ['utf-8', 'shift-jis', 'cp932', 'euc-jp']
            for encoding in encodings:
                try:
                    df = pd.read_csv(local_path, encoding=encoding)
                    logger.info(f"CSVファイルを読み込みました: {local_path} (エンコーディング: {encoding})")
                    break
                except UnicodeDecodeError:
                    logger.debug(f"エンコーディング {encoding} での読み込みに失敗しました")
                except Exception as e:
                    logger.error(f"CSVファイルの読み込み中にエラーが発生: {str(e)}")
                    raise
            
            if df is None:
                raise ValueError(f"CSVファイルを読み込めませんでした: {local_path}")
            
            # カラム名を整形
            original_columns = df.columns.tolist()
            sanitized_columns = [self.sanitize_column_name(col) for col in original_columns]
            
            # カラム名の対応マップを作成 (デバッグ用)
            column_map = dict(zip(original_columns, sanitized_columns))
            logger.info(f"カラム名の整形マップ: {column_map}")
            
            # 整形したカラム名でDataFrameを更新
            df.columns = sanitized_columns
            
            # 処理後のCSVファイルを保存
            filename = os.path.basename(local_path)
            processed_filename = f"processed_{filename}"
            processed_path = os.path.join(self.temp_dir, processed_filename)
            df.to_csv(processed_path, index=False, encoding='utf-8')
            
            logger.info(f"処理後のCSVファイルを保存しました: {processed_path}")
            
            # 処理後のファイルをGCSにアップロード
            parts = gcs_uri.split('/')
            processed_gcs_uri = '/'.join(parts[:-1] + [f"processed_{parts[-1]}"])
            return self.upload_to_gcs(processed_path, processed_gcs_uri)
            
        except Exception as e:
            logger.error(f"CSVファイルの前処理中にエラーが発生: {str(e)}")
            raise

    def preprocess_parquet(self, gcs_uri):
        """
        Parquetファイルのカラム名を前処理します
        
        Args:
            gcs_uri (str): 処理するParquetファイルのGCS URI
            
        Returns:
            str: 前処理後のParquetファイルのGCS URI
        """
        try:
            # GCSからファイルをダウンロード
            local_path = self.download_from_gcs(gcs_uri)
            
            # Parquetファイルを読み込み
            try:
                df = pd.read_parquet(local_path)
                logger.info(f"Parquetファイルを読み込みました: {local_path}")
            except Exception as e:
                logger.error(f"Parquetファイルの読み込み中にエラーが発生: {str(e)}")
                raise
            
            # カラム名を整形
            original_columns = df.columns.tolist()
            sanitized_columns = [self.sanitize_column_name(col) for col in original_columns]
            
            # カラム名の対応マップを作成 (デバッグ用)
            column_map = dict(zip(original_columns, sanitized_columns))
            logger.info(f"カラム名の整形マップ: {column_map}")
            
            # 整形したカラム名でDataFrameを更新
            df.columns = sanitized_columns
            
            # 処理後のParquetファイルを保存
            filename = os.path.basename(local_path)
            processed_filename = f"processed_{filename}"
            processed_path = os.path.join(self.temp_dir, processed_filename)
            df.to_parquet(processed_path, index=False)
            
            logger.info(f"処理後のParquetファイルを保存しました: {processed_path}")
            
            # 処理後のファイルをGCSにアップロード
            parts = gcs_uri.split('/')
            processed_gcs_uri = '/'.join(parts[:-1] + [f"processed_{parts[-1]}"])
            return self.upload_to_gcs(processed_path, processed_gcs_uri)
            
        except Exception as e:
            logger.error(f"Parquetファイルの前処理中にエラーが発生: {str(e)}")
            raise

    def preprocess_file(self, gcs_uri):
        """
        ファイルの種類に応じた前処理を行います
        
        Args:
            gcs_uri (str): 処理するファイルのGCS URI
            
        Returns:
            str: 前処理後のファイルのGCS URI
        """
        if gcs_uri.endswith('.csv'):
            return self.preprocess_csv(gcs_uri)
        elif gcs_uri.endswith('.parquet'):
            return self.preprocess_parquet(gcs_uri)
        else:
            logger.warning(f"サポートされていないファイル形式です: {gcs_uri}")
            return gcs_uri 