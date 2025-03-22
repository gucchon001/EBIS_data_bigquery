#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
アドエビス詳細分析ページ操作モジュール
詳細分析ページへのアクセスとCSVダウンロード機能を提供します。
POMパターン（Page Object Model）で実装し、Browser クラスの機能を活用します。
"""

import os
import time
import sys
import shutil
import traceback
from datetime import datetime, timedelta
from pathlib import Path

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent.parent.parent.parent)
sys.path.append(project_root)

from src.utils.logging_config import get_logger
from src.utils.environment import EnvironmentUtils as env
from src.modules.browser.browser import Browser
from src.modules.browser.login_page_template import handle_errors

logger = get_logger(__name__)

class DetailedAnalysisPage:
    """
    アドエビス詳細分析ページ操作を担当するクラス
    POMパターンに基づき、詳細分析ページ専用の操作メソッドを提供します
    """
    
    def __init__(self, browser=None):
        """
        初期化
        settings.iniの[AdEBIS]と[Download]セクションから設定を読み込みます
        Browser クラスのインスタンスを使用してブラウザ操作を行います
        
        Args:
            browser (Browser): 既存のブラウザインスタンス（省略時は新規作成）
        """
        # 環境変数を確実に読み込む
        env.load_env()
        
        # ブラウザインスタンスの初期化
        self.browser_created = False
        if browser is None:
            # ヘッドレスモード設定を取得
            headless_value = env.get_config_value("BROWSER", "headless", "false")
            headless = headless_value.lower() == "true" if isinstance(headless_value, str) else bool(headless_value)
            
            # セレクタファイルのパスを設定
            selectors_path = "config/selectors.csv"
            if not os.path.exists(selectors_path):
                logger.warning(f"セレクタファイルが見つかりません: {selectors_path}")
                selectors_path = None
            
            # ブラウザインスタンスを作成
            self.browser = Browser(selectors_path=selectors_path, headless=headless)
            if not self.browser.setup():
                logger.error("ブラウザのセットアップに失敗しました")
                raise RuntimeError("ブラウザのセットアップに失敗しました")
            
            self.browser_created = True
        else:
            # 既存のブラウザインスタンスを使用
            self.browser = browser
            
        # 設定の読み込み
        self.detailed_analysis_url = env.get_config_value("AdEBIS", "url_details", 
                                                          "https://bishamon.ebis.ne.jp/details-analysis")
        
        # ダウンロード関連設定
        timeout_value = env.get_config_value("Download", "timeout", "90")
        self.download_timeout = int(timeout_value) if isinstance(timeout_value, str) else int(timeout_value or 90)
        
        self.download_dir = env.resolve_path(env.get_config_value("Download", "directory", "data/downloads"))
        if not os.path.exists(self.download_dir):
            try:
                os.makedirs(self.download_dir, exist_ok=True)
                logger.info(f"ダウンロードディレクトリを作成しました: {self.download_dir}")
            except Exception as e:
                logger.error(f"ダウンロードディレクトリの作成に失敗しました: {str(e)}")
        
        logger.info("詳細分析ページクラスを初期化しました")
    
    @handle_errors(screenshot_name="navigate_error")
    def navigate_to_detailed_analysis(self):
        """
        詳細分析ページに移動します
        
        Returns:
            bool: 移動が成功した場合はTrue
        """
        if not self.detailed_analysis_url:
            logger.error("詳細分析ページのURLが設定されていません")
            return False
            
        try:
            logger.info(f"詳細分析ページへ移動します: {self.detailed_analysis_url}")
            
            # Browserクラスを使用してナビゲーション
            result = self.browser.navigate_to(self.detailed_analysis_url)
            
            # ページの読み込みを待機
            self.browser.wait_for_page_load()
            
            logger.info("詳細分析ページへの移動が完了しました")
            return result
            
        except Exception as e:
            logger.error(f"詳細分析ページへの移動中にエラーが発生しました: {str(e)}")
            return False
    
    @handle_errors(screenshot_name="date_picker_error")
    def select_date_range(self, start_date, end_date):
        """
        日付範囲を選択します
        
        Args:
            start_date (str): 開始日（YYYY/MM/DD形式）
            end_date (str): 終了日（YYYY/MM/DD形式）
            
        Returns:
            bool: 日付選択が成功した場合はTrue
        """
        try:
            # 日付カレンダーを開く
            logger.debug("日付カレンダーを開きます")
            self.browser.click_element('detailed_analysis', 'date_picker_trigger')
            time.sleep(2)
            
            # 開始日を入力
            logger.debug(f"開始日を入力します: {start_date}")
            start_element = self.browser.get_element('detailed_analysis', 'start_date_input')
            # 入力フィールドをクリア
            self.browser.execute_script("arguments[0].value = '';", start_element)
            time.sleep(1)
            self.browser.input_text_by_selector('detailed_analysis', 'start_date_input', start_date)
            
            # 終了日を入力
            logger.debug(f"終了日を入力します: {end_date}")
            end_element = self.browser.get_element('detailed_analysis', 'end_date_input')
            # 入力フィールドをクリア
            self.browser.execute_script("arguments[0].value = '';", end_element)
            time.sleep(1)
            self.browser.input_text_by_selector('detailed_analysis', 'end_date_input', end_date)
            
            # 入力値の確認
            actual_start = self.browser.execute_script("return arguments[0].value;", start_element)
            actual_end = self.browser.execute_script("return arguments[0].value;", end_element)
            
            if actual_start != start_date or actual_end != end_date:
                logger.warning(f"日付が正しく入力されていません。開始日: {actual_start}（期待値: {start_date}）、終了日: {actual_end}（期待値: {end_date}）")
            
            # 適用ボタンをクリック
            logger.debug("適用ボタンをクリックします")
            result = self.browser.click_element('detailed_analysis', 'apply_button')
            if result:
                logger.info(f"日付範囲を選択しました: {start_date} から {end_date}")
                time.sleep(3)  # ページ更新の待機
            return result
            
        except Exception as e:
            logger.error(f"日付範囲の選択中にエラーが発生しました: {str(e)}")
            return False
    
    @handle_errors(screenshot_name="select_custom_view_error")
    def select_custom_view(self):
        """
        カスタムビュー「プログラム用全項目ビュー」を選択します
        
        Returns:
            bool: ビュー選択が成功した場合はTrue
        """
        try:
            # ビューボタンをクリック
            logger.debug("ビューボタンをクリックします")
            if not self.browser.click_element('detailed_analysis', 'view_button', retry_count=2):
                logger.error("ビューボタンのクリックに失敗しました")
                return False
                
            time.sleep(2)  # ドロップダウンメニューの表示待ち
            
            # プログラム用全項目ビューをクリック
            logger.debug("プログラム用全項目ビューをクリックします")
            if not self.browser.click_element('detailed_analysis', 'program_all_view', retry_count=2):
                logger.error("プログラム用全項目ビューのクリックに失敗しました")
                return False
                
            logger.info("カスタムビュー「プログラム用全項目ビュー」を選択しました")
            time.sleep(3)  # ビュー適用の待機
            
            return True
            
        except Exception as e:
            logger.error(f"カスタムビュー選択中にエラーが発生しました: {str(e)}")
            return False
    
    @handle_errors(screenshot_name="select_tab_error")
    def select_all_traffic_tab(self):
        """
        全トラフィックタブを選択します
        
        Returns:
            bool: タブ選択が成功した場合はTrue
        """
        try:
            # 全トラフィックタブをクリック
            logger.debug("全トラフィックタブをクリックします")
            if not self.browser.click_element('detailed_analysis', 'all_traffic_tab', retry_count=2):
                logger.error("全トラフィックタブのクリックに失敗しました")
                return False
                
            logger.info("全トラフィックタブを選択しました")
            time.sleep(3)  # ページ更新の待機
            
            return True
            
        except Exception as e:
            logger.error(f"全トラフィックタブ選択中にエラーが発生しました: {str(e)}")
            return False
    
    @handle_errors(screenshot_name="download_error")
    def download_csv(self):
        """
        CSVをダウンロードします
        
        Returns:
            bool: ダウンロードが成功した場合はTrue
        """
        try:
            # インポートボタンをクリック
            logger.debug("インポートボタンをクリックします")
            if not self.browser.click_element('detailed_analysis', 'import_button', retry_count=2):
                logger.error("インポートボタンのクリックに失敗しました")
                return False
                
            time.sleep(1)
            
            # ダウンロードボタンをクリック
            logger.debug("ダウンロードボタンをクリックします")
            if not self.browser.click_element('detailed_analysis', 'download_button', retry_count=2):
                logger.error("ダウンロードボタンのクリックに失敗しました")
                return False
                
            logger.info("CSVのダウンロードを開始しました")
            return True
            
        except Exception as e:
            logger.error(f"CSVダウンロード中にエラーが発生しました: {str(e)}")
            return False
    
    @handle_errors(screenshot_name="process_file_error")
    def wait_for_download_and_process(self, target_date, output_dir=None):
        """
        ダウンロード完了を待機し、ファイル処理を行います
        
        Args:
            target_date (datetime): 対象日付
            output_dir (str, optional): 出力ディレクトリ
            
        Returns:
            str: 処理後のファイルパス、失敗した場合はNone
        """
        try:
            # 出力ディレクトリの設定
            if output_dir is None:
                output_dir = self.download_dir
                
            logger.info(f"ダウンロード完了を待機しています（タイムアウト: {self.download_timeout}秒）")
            time.sleep(self.download_timeout)
            
            # ダウンロードディレクトリの確認
            if not os.path.exists(self.download_dir):
                logger.error(f"ダウンロードディレクトリが存在しません: {self.download_dir}")
                return None
                
            # ダウンロードファイルを検索
            download_files = [f for f in os.listdir(self.download_dir) if os.path.isfile(os.path.join(self.download_dir, f))]
            csv_files = [s for s in download_files if 'detail_analyze' in s.lower()]
            
            if not csv_files:
                logger.error(f"ダウンロードされたCSVファイルが見つかりません。ディレクトリ内のファイル: {download_files}")
                return None
                
            # 最新のファイルを取得
            latest_file = sorted(csv_files, key=lambda x: os.path.getmtime(os.path.join(self.download_dir, x)), reverse=True)[0]
            source_path = os.path.join(self.download_dir, latest_file)
            
            logger.debug(f"ダウンロードファイルを特定しました: {source_path}")
            
            # 移動先のパスを作成
            date_str = target_date.strftime('%Y%m%d')
            target_filename = f"{date_str}_ebis_SS_CV.csv"
            target_path = os.path.join(output_dir, target_filename)
            
            # 出力ディレクトリが存在しない場合は作成
            os.makedirs(output_dir, exist_ok=True)
            
            # ファイルを移動
            shutil.move(source_path, target_path)
            
            logger.info(f"ダウンロードファイルを移動しました: {target_path}")
            return target_path
            
        except Exception as e:
            logger.error(f"ファイル処理中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    @handle_errors(screenshot_name="download_flow_error", raise_exception=True)
    def execute_download_flow(self, start_date, end_date=None, output_dir=None):
        """
        ダウンロードフロー全体を実行します
        
        Args:
            start_date (datetime): 開始日
            end_date (datetime, optional): 終了日（省略時は開始日と同じ）
            output_dir (str, optional): 出力ディレクトリ
            
        Returns:
            str: 処理後のファイルパス、失敗した場合はNone
        """
        if end_date is None:
            end_date = start_date
            
        try:
            # 詳細分析ページに移動
            if not self.navigate_to_detailed_analysis():
                logger.error("詳細分析ページへの移動に失敗しました")
                return None
                
            # 日付範囲選択
            start_date_str = start_date.strftime('%Y/%m/%d')
            end_date_str = end_date.strftime('%Y/%m/%d')
            
            if not self.select_date_range(start_date_str, end_date_str):
                logger.error("日付範囲の選択に失敗しました")
                return None
                
            # 全トラフィックタブを選択
            if not self.select_all_traffic_tab():
                logger.error("全トラフィックタブの選択に失敗しました")
                return None
                
            # カスタムビュー「プログラム用全項目ビュー」を選択
            if not self.select_custom_view():
                logger.error("カスタムビューの選択に失敗しました")
                return None
                
            # CSVダウンロード
            if not self.download_csv():
                logger.error("CSVのダウンロードに失敗しました")
                return None
                
            # ダウンロード完了待機とファイル処理
            result = self.wait_for_download_and_process(start_date, output_dir)
            if not result:
                logger.error("ダウンロードファイルの処理に失敗しました")
                return None
                
            logger.info("ダウンロードフローが正常に完了しました")
            return result
            
        except Exception as e:
            logger.error(f"ダウンロードフロー実行中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    def quit(self):
        """
        ブラウザを終了します
        自分で作成したブラウザインスタンスのみ終了します
        """
        if self.browser and self.browser_created:
            self.browser.quit()
            logger.info("ブラウザを終了しました") 