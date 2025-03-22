# -*- coding: utf-8 -*-
"""
OpenAI APIによるHTML処理テスト
指定されたHTMLファイルを読み込み、OpenAI APIに送信して処理できるかテストします。
"""

import os
import sys
from pathlib import Path
import json
import time

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from src.utils.environment import EnvironmentUtils as env
from src.utils.logging_config import get_logger

# openaiパッケージをインポート
import openai

logger = get_logger(__name__)

class OpenAIHTMLProcessingTest:
    """HTMLファイルをOpenAI APIで処理するテストを行うクラス"""
    
    def __init__(self):
        """初期化"""
        # 環境変数を読み込む
        env.load_env()
        
        # APIキーを取得
        self.api_key = env.get_env_var("OPENAI_API_KEY", "")
        if not self.api_key:
            logger.error("OpenAI APIキーが設定されていません")
            raise ValueError("OpenAI APIキーが設定されていません")
            
        # AIモデルを設定ファイルから取得
        self.ai_model = env.get_config_value("API", "ai_model", "gpt-3.5-turbo-16k")
        logger.info(f"使用するAIモデル: {self.ai_model}")
        
        # クライアントの設定
        openai.api_key = self.api_key
    
    def read_html_file(self, file_path):
        """HTMLファイルを読み込む"""
        try:
            # ファイルパスを絶対パスに変換
            absolute_path = env.resolve_path(file_path)
            logger.info(f"HTMLファイルを読み込みます: {absolute_path}")
            
            # ファイルの存在確認
            if not os.path.exists(absolute_path):
                logger.error(f"ファイルが存在しません: {absolute_path}")
                return None
                
            # ファイルサイズを確認
            file_size = os.path.getsize(absolute_path) / 1024  # KBに変換
            logger.info(f"ファイルサイズ: {file_size:.2f} KB")
            
            # ファイルを読み込む
            with open(absolute_path, 'r', encoding='utf-8') as file:
                html_content = file.read()
                
            logger.info(f"HTMLファイルを読み込みました（{len(html_content)} 文字）")
            return html_content
            
        except Exception as e:
            logger.error(f"HTMLファイルの読み込み中にエラーが発生しました: {str(e)}")
            return None
    
    def test_process_html_with_openai(self, html_content, chunk_size=12000):
        """OpenAI APIでHTMLを処理するテスト"""
        if not html_content:
            logger.error("HTMLコンテンツがありません")
            return False, "HTMLコンテンツがありません"
            
        try:
            logger.info("OpenAI APIによるHTML処理テストを開始します")
            
            # HTMLの長さを確認
            html_length = len(html_content)
            logger.info(f"HTML長さ: {html_length} 文字")
            
            # APIにリクエストを送信
            start_time = time.time()
            
            # HTMLが長すぎる場合は分割
            if html_length > chunk_size:
                logger.info(f"HTMLが長いため、分割して処理します（{chunk_size}文字ごと）")
                first_chunk = html_content[:chunk_size]
                
                response = openai.chat.completions.create(
                    model=self.ai_model,
                    messages=[
                        {"role": "system", "content": "あなたはHTMLの解析エキスパートです。与えられたHTMLの構造を分析し、主要な要素をリストアップしてください。"},
                        {"role": "user", "content": f"このHTMLを分析してください（部分的なHTMLです）:\n\n{first_chunk}"}
                    ],
                    max_tokens=1000
                )
                logger.info(f"分割HTMLの処理に成功しました（最初の{chunk_size}文字）")
            else:
                # HTMLが短い場合はそのまま送信
                response = openai.chat.completions.create(
                    model=self.ai_model,
                    messages=[
                        {"role": "system", "content": "あなたはHTMLの解析エキスパートです。与えられたHTMLの構造を分析し、主要な要素をリストアップしてください。"},
                        {"role": "user", "content": f"このHTMLを分析してください:\n\n{html_content}"}
                    ],
                    max_tokens=1000
                )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # レスポンスを確認
            message = response.choices[0].message.content
            logger.info(f"API処理時間: {processing_time:.2f}秒")
            logger.info(f"APIレスポンス（最初の100文字）: {message[:100]}...")
            
            return True, {
                "message": message,
                "processing_time": processing_time,
                "html_length": html_length,
                "model": self.ai_model
            }
                
        except Exception as e:
            logger.error(f"HTML処理テスト中にエラーが発生しました: {str(e)}")
            if "maximum context length" in str(e):
                logger.error("HTMLが長すぎます。トークン制限を超えています。")
            return False, str(e)

def run_html_test(html_file_path):
    """HTMLファイル処理テストを実行する"""
    try:
        print(f"HTMLファイル '{html_file_path}' の処理テストを開始します...")
        
        tester = OpenAIHTMLProcessingTest()
        
        # HTMLファイルを読み込む
        html_content = tester.read_html_file(html_file_path)
        if not html_content:
            print("HTMLファイルの読み込みに失敗しました。")
            return False
        
        # HTMLをOpenAI APIで処理
        success, result = tester.test_process_html_with_openai(html_content)
        
        if success:
            print(f"HTML処理テスト成功:")
            print(f"- 使用モデル: {result['model']}")
            print(f"- HTML長さ: {result['html_length']} 文字")
            print(f"- 処理時間: {result['processing_time']:.2f} 秒")
            print("\nAPIレスポンス:")
            print("-" * 50)
            print(result["message"])
            print("-" * 50)
        else:
            print(f"HTML処理テスト失敗: {result}")
            
        return success
        
    except Exception as e:
        print(f"テスト実行中にエラーが発生しました: {str(e)}")
        return False

if __name__ == "__main__":
    # コマンドライン引数からHTMLファイルのパスを取得
    if len(sys.argv) > 1:
        html_file_path = sys.argv[1]
    else:
        html_file_path = "data/pages/bishamon_ebis_ne_jp_20250321_075218.html"
    
    success = run_html_test(html_file_path)
    sys.exit(0 if success else 1) 