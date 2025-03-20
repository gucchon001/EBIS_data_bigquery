import pytest
from pathlib import Path

# プロジェクトルートのパス
PROJECT_ROOT = Path(__file__).resolve().parent.parent

def test_project_structure():
    """フォルダ構成が正しいかを確認"""
    assert (PROJECT_ROOT / "config").exists(), "config フォルダが存在しません"
    assert (PROJECT_ROOT / "docs").exists(), "docs フォルダが存在しません"
    assert (PROJECT_ROOT / "logs").exists(), "logs フォルダが存在しません"
    assert (PROJECT_ROOT / "spec_tools").exists(), "spec_tools フォルダが存在しません"
    assert (PROJECT_ROOT / "src").exists(), "src フォルダが存在しません"
    assert (PROJECT_ROOT / "tests").exists(), "tests フォルダが存在しません"

def test_config_files():
    """config フォルダ内の重要ファイルが存在するか確認"""
    config_path = PROJECT_ROOT / "config"
    assert (config_path / "secrets.env").exists(), "secrets.env が存在しません"
    assert (config_path / "settings.ini").exists(), "settings.ini が存在しません"

def test_src_modules():
    """src/modules フォルダが存在するか確認"""
    modules_path = PROJECT_ROOT / "src" / "modules"
    assert modules_path.exists(), "src/modules フォルダが存在しません"
    assert (modules_path / "db_connector.py").exists(), "db_connector.py が存在しません"

def test_utils_access():
    """src/utils フォルダが存在するか確認"""
    utils_path = PROJECT_ROOT / "src" / "utils"
    assert utils_path.exists(), "src/utils フォルダが存在しません"
    assert (utils_path / "environment.py").exists(), "environment.py が存在しません"
    assert (utils_path / "logging_config.py").exists(), "logging_config.py が存在しません"

def test_logs_directory():
    """logs フォルダへのアクセス確認"""
    logs_path = PROJECT_ROOT / "logs"
    assert logs_path.exists(), "logs フォルダが存在しません"
