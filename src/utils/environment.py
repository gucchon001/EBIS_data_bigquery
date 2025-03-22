#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
環境設定ユーティリティ

設定ファイルや環境変数を読み込み、一元管理するためのユーティリティクラスです。
"""

import os
import sys
import configparser
from pathlib import Path
from typing import Optional, Dict, Any


class EnvironmentUtils:
    """
    環境変数や設定ファイルを管理するユーティリティクラス
    """
    _env_loaded = False
    _config = None
    _project_root = None

    @classmethod
    def get_project_root(cls) -> Path:
        """プロジェクトのルートディレクトリを取得します"""
        if cls._project_root is None:
            # 現在のファイルの親ディレクトリを辿って、プロジェクトルートを特定
            current_file = Path(__file__).resolve()
            cls._project_root = current_file.parent.parent.parent
        return cls._project_root

    @classmethod
    def resolve_path(cls, path: str) -> Path:
        """
        相対パスを絶対パスに解決します
        
        Args:
            path: 解決する相対パス
            
        Returns:
            解決された絶対パス
        """
        if os.path.isabs(path):
            return Path(path)
        return cls.get_project_root() / path

    @classmethod
    def load_env(cls, env_file: str = "config/secrets.env") -> None:
        """
        環境変数ファイルを読み込みます
        
        Args:
            env_file: 環境変数ファイルのパス（デフォルト: config/secrets.env）
        """
        if cls._env_loaded:
            return
        
        env_path = cls.resolve_path(env_file)
        
        if not env_path.exists():
            print(f"警告: 環境変数ファイル {env_path} が見つかりません。", file=sys.stderr)
            cls._env_loaded = True
            return
        
        # .envファイルを読み込む
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # コメント行や空行はスキップ
                if not line or line.startswith('#'):
                    continue
                
                # key=valueの形式を解析
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # 既存の環境変数を上書きしないように注意
                    if key not in os.environ:
                        os.environ[key] = value
        
        cls._env_loaded = True
        print(f"環境変数ファイル {env_path} を読み込みました。")

    @classmethod
    def get_env_var(cls, var_name: str, default: Optional[str] = None) -> str:
        """
        環境変数の値を取得します
        
        Args:
            var_name: 環境変数名
            default: デフォルト値（未設定時に返す値）
            
        Returns:
            環境変数の値またはデフォルト値
            
        Raises:
            ValueError: 環境変数が設定されておらず、デフォルト値も指定されていない場合
        """
        if not cls._env_loaded:
            cls.load_env()
        
        value = os.environ.get(var_name)
        if value is None:
            if default is not None:
                return default
            raise ValueError(f"環境変数 {var_name} が設定されていません。")
        return value

    @classmethod
    def get_config_file(cls, config_file: str = "config/settings.ini") -> configparser.ConfigParser:
        """
        設定ファイルを読み込みます
        
        Args:
            config_file: 設定ファイルのパス（デフォルト: config/settings.ini）
            
        Returns:
            ConfigParser オブジェクト
        """
        if cls._config is not None:
            return cls._config
        
        config_path = cls.resolve_path(config_file)
        if not config_path.exists():
            print(f"警告: 設定ファイル {config_path} が見つかりません。", file=sys.stderr)
            cls._config = configparser.ConfigParser()
            return cls._config
        
        cls._config = configparser.ConfigParser()
        cls._config.read(str(config_path), encoding='utf-8')
        return cls._config

    @classmethod
    def get_config_value(cls, section: str, key: str, default: Optional[str] = None) -> str:
        """
        設定ファイルから値を取得します
        
        Args:
            section: セクション名
            key: キー名
            default: デフォルト値（未設定時に返す値）
            
        Returns:
            設定値またはデフォルト値
            
        Raises:
            ValueError: 設定値が存在せず、デフォルト値も指定されていない場合
        """
        config = cls.get_config_file()
        try:
            return config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            if default is not None:
                return default
            raise ValueError(f"設定 [{section}]の{key} が見つかりません。")

    @classmethod
    def get_bigquery_settings(cls) -> Dict[str, str]:
        """
        BigQuery接続に必要な設定を取得します
        
        Returns:
            BigQuery設定のディクショナリ
        """
        if not cls._env_loaded:
            cls.load_env()
        
        return {
            "project_id": cls.get_env_var("BIGQUERY_PROJECT_ID"),
            "dataset_id": cls.get_env_var("BIGQUERY_DATASET"),
            "key_path": cls.resolve_path(cls.get_env_var("GCS_KEY_PATH")),
        }

    @classmethod
    def get_gcs_settings(cls) -> Dict[str, str]:
        """
        GCS接続に必要な設定を取得します
        
        Returns:
            GCS設定のディクショナリ
        """
        if not cls._env_loaded:
            cls.load_env()
        
        return {
            "project_id": cls.get_env_var("GCP_PROJECT_ID"),
            "bucket_name": cls.get_env_var("GCS_BUCKET_NAME"),
            "key_path": cls.resolve_path(cls.get_env_var("GCS_KEY_PATH")),
        }
