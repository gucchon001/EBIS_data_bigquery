#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
GCSアップローダー

data/AE_SSresultディレクトリ内のファイルを全てGoogle Cloud Storageにアップロードするスクリプト。
"""

import os
import glob
from pathlib import Path
from google.cloud import storage
from google.oauth2 import service_account
from loguru import logger
import sys

from src.utils.environment import EnvironmentUtils

def setup_logger():
    """ロガーの設定を行います"""
    log_format = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
    logger.remove()
    logger.add(sys.stderr, format=log_format, level="INFO")
    logger.add(
        os.path.join(EnvironmentUtils.get_project_root(), "logs", "gcs_uploader_{time:YYYY-MM-DD}.log"),
        format=log_format,
        rotation="1 day",
        level="DEBUG"
    )

class GCSUploader:
    """
    Google Cloud Storageへのファイルアップロードを行うクラス
    """
    
    def __init__(self):
        """初期化処理"""
        # 環境変数をロード
        EnvironmentUtils.load_env()
        
        # ロガーを設定
        setup_logger()
        
        # GCSバケット名を取得
        self.bucket_name = EnvironmentUtils.get_env_var("GCS_BUCKET_NAME")
        if not self.bucket_name:
            raise ValueError("GCS_BUCKET_NAME環境変数が設定されていません")
        
        # 認証
        self.gcs_client = self._authenticate_gcs()
    
    def _authenticate_gcs(self):
        """GCSの認証を行い、クライアントを返します"""
        try:
            # 環境変数からGCSの設定を取得
            gcs_key_path = EnvironmentUtils.get_env_var("GCS_KEY_PATH")
            
            # キーファイルのパスを解決
            key_path = Path(EnvironmentUtils.get_project_root()) / gcs_key_path
            
            if not key_path.exists():
                raise FileNotFoundError(f"GCS認証キーファイルが見つかりません: {key_path}")
            
            # 認証情報を作成
            credentials = service_account.Credentials.from_service_account_file(key_path)
            
            # ストレージクライアントを作成
            return storage.Client(credentials=credentials, project=EnvironmentUtils.get_env_var("GCP_PROJECT_ID"))
        
        except Exception as e:
            logger.error(f"GCS認証に失敗しました: {str(e)}")
            raise
    
    def upload_file(self, local_file_path, bucket_name=None, destination_blob_name=None):
        """
        指定されたファイルをGCSにアップロードします
        
        Args:
            local_file_path: アップロードするローカルファイルのパス
            bucket_name: アップロード先のバケット名（デフォルトはインスタンス初期化時のバケット名）
            destination_blob_name: アップロード先のブロブ名（パス）。未指定時はファイル名をそのまま使用
            
        Returns:
            str: アップロードしたGCSのURI
        """
        try:
            bucket_name = bucket_name or self.bucket_name
            
            # destination_blob_nameが指定されていない場合は、ファイル名をそのまま使用
            if destination_blob_name is None:
                destination_blob_name = os.path.basename(local_file_path)
            
            bucket = self.gcs_client.bucket(bucket_name)
            blob = bucket.blob(destination_blob_name)
            
            # ファイルをアップロード
            blob.upload_from_filename(local_file_path)
            
            gcs_uri = f"gs://{bucket_name}/{destination_blob_name}"
            logger.info(f"アップロード完了: {local_file_path} → {gcs_uri}")
            return gcs_uri
        
        except Exception as e:
            logger.error(f"アップロード失敗 - ファイル: {local_file_path}, エラー: {str(e)}")
            raise
    
    def upload_directory(self, source_dir, destination_prefix=None):
        """
        ディレクトリ内のすべてのファイルをGCSにアップロードします
        
        Args:
            source_dir: アップロードするディレクトリのパス
            destination_prefix: GCS内でのプレフィックス（デフォルトはディレクトリ名）
            
        Returns:
            tuple: (成功数, 全ファイル数)
        """
        try:
            source_path = Path(source_dir)
            if not source_path.exists():
                raise FileNotFoundError(f"ソースディレクトリが見つかりません: {source_path}")
            
            # ディレクトリ名をプレフィックスとして使用（指定がない場合）
            if destination_prefix is None:
                destination_prefix = source_path.name
            
            # スラッシュで終わるようにする
            if destination_prefix and not destination_prefix.endswith('/'):
                destination_prefix += '/'
            
            # ディレクトリ内のすべてのファイルを取得
            file_paths = list(source_path.glob("*"))
            logger.info(f"アップロード対象のファイル数: {len(file_paths)}")
            
            # ファイルをGCSにアップロード
            success_count = 0
            for file_path in file_paths:
                if file_path.is_file():
                    # アップロード先のブロブ名（パス）を設定
                    destination_blob_name = f"{destination_prefix}{file_path.name}"
                    
                    try:
                        # ファイルをアップロード
                        self.upload_file(str(file_path), self.bucket_name, destination_blob_name)
                        success_count += 1
                    except Exception as e:
                        logger.error(f"ファイルのアップロードに失敗: {file_path}, エラー: {str(e)}")
            
            logger.info(f"アップロード処理完了。成功: {success_count}/{len(file_paths)}ファイル")
            return success_count, len(file_paths)
        
        except Exception as e:
            logger.error(f"ディレクトリアップロード中にエラーが発生: {str(e)}")
            raise

def authenticate_gcs():
    """GCSの認証を行い、クライアントを返します（旧関数、後方互換性のため残す）"""
    uploader = GCSUploader()
    return uploader.gcs_client

def upload_file_to_gcs(gcs_client, local_file_path, bucket_name, destination_blob_name):
    """
    指定されたファイルをGCSにアップロードします（旧関数、後方互換性のため残す）
    
    Args:
        gcs_client: Google Cloud Storageクライアント
        local_file_path: アップロードするローカルファイルのパス
        bucket_name: アップロード先のバケット名
        destination_blob_name: アップロード先のブロブ名（パス）
    """
    try:
        uploader = GCSUploader()
        uploader.upload_file(local_file_path, bucket_name, destination_blob_name)
        return True
    except Exception:
        return False

def main():
    """メイン処理"""
    try:
        # 環境変数をロード
        EnvironmentUtils.load_env()
        
        # ロガーを設定
        setup_logger()
        
        logger.info("GCSアップロード処理を開始します")
        
        # アップローダーを作成
        uploader = GCSUploader()
        
        # アップロード対象のディレクトリ
        source_dir = Path(EnvironmentUtils.get_project_root()) / "data" / "AE_SSresult"
        
        # ディレクトリ内のファイルをアップロード
        success_count, total_count = uploader.upload_directory(source_dir, "AE_SSresult")
        
        if success_count == total_count:
            logger.info(f"すべてのファイルのアップロードが成功しました: {success_count}ファイル")
        else:
            logger.warning(f"一部のファイルがアップロードできませんでした。成功: {success_count}/{total_count}")
    
    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 