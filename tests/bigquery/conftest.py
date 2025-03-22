#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
pytestの設定ファイル
テスト環境の設定とフィクスチャの定義
"""

import os
import sys
import pytest
from pathlib import Path

# テスト対象のモジュールへのパスを追加
module_path = Path(__file__).resolve().parent.parent.parent
if str(module_path) not in sys.path:
    sys.path.insert(0, str(module_path))

@pytest.fixture
def sample_schema():
    """サンプルスキーマデータを提供するフィクスチャ"""
    return [
        {"name": "CV名", "type": "str", "sample": "応募完了"},
        {"name": "CV時間", "type": "timestamp", "sample": "45737.99779"},
        {"name": "ユーザーID", "type": "str", "sample": "v7n8kt2ogd.1742563093"},
        {"name": "ユーザー名", "type": "str", "sample": "undefined"},
        {"name": "売上金額", "type": "int", "sample": "1039482"},
        {"name": "売上商品名", "type": "str", "sample": "プレミアムプラン"},
        {"name": "ユーザー年齢", "type": "int", "sample": "32"},
        {"name": "潜伏期間 （秒）", "type": "int", "sample": "3600"},
        {"name": "潜伏期間（分）", "type": "int", "sample": "60"},
        {"name": "（ABC）商品コード", "type": "str", "sample": "ABC123"},
        {"name": "1日あたり売上", "type": "int", "sample": "15000"},
        {"name": "直接効果_発生日時", "type": "timestamp", "sample": "45737.99667"}
    ]

@pytest.fixture
def bq_schema():
    """BigQueryスキーマを提供するフィクスチャ"""
    return [
        {"name": "CV名", "type": "STRING", "mode": "NULLABLE"},
        {"name": "CV時間", "type": "TIMESTAMP", "mode": "NULLABLE"},
        {"name": "ユーザーID", "type": "STRING", "mode": "NULLABLE"},
        {"name": "ユーザー名", "type": "STRING", "mode": "NULLABLE"},
        {"name": "売上金額", "type": "INTEGER", "mode": "NULLABLE"},
        {"name": "売上商品名", "type": "STRING", "mode": "NULLABLE"},
        {"name": "ユーザー年齢", "type": "INTEGER", "mode": "NULLABLE"},
        {"name": "潜伏期間___秒_", "type": "INTEGER", "mode": "NULLABLE"},
        {"name": "潜伏期間_分_", "type": "INTEGER", "mode": "NULLABLE"},
        {"name": "_ABC_商品コード", "type": "STRING", "mode": "NULLABLE"},
        {"name": "_1日あたり売上", "type": "INTEGER", "mode": "NULLABLE"},
        {"name": "直接効果_発生日時", "type": "TIMESTAMP", "mode": "NULLABLE"}
    ] 