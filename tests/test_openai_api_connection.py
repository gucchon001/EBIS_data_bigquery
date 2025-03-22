# -*- coding: utf-8 -*-
"""
OpenAI API接続テスト
環境変数からAPIキーを読み込み、APIに接続してレスポンスを確認します。
"""

import os
import sys
from pathlib import Path
import json

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from src.utils.environment import EnvironmentUtils as env
from src.utils.logging_config import get_logger

# openaiパッケージをインポート
import openai

logger = get_logger(__name__)

class OpenAIConnectionTest:
    """OpenAI APIの接続テストを行うクラス"""
    
    def __init__(self):
        """初期化"""
        # 環境変数を読み込む
        env.load_env()
        
        # APIキーを取得
        self.api_key = env.get_env_var("OPENAI_API_KEY", "")
        if not self.api_key:
            logger.error("OpenAI APIキーが設定されていません")
            raise ValueError("OpenAI APIキーが設定されていません")
        
        # 最初の6文字のみログ出力（セキュリティ対策）
        logger.info(f"OpenAI APIキー（先頭6文字）: {self.api_key[:6]}***")
        
        # クライアントの設定
        openai.api_key = self.api_key
    
    def test_connection(self):
        """APIへの接続テスト"""
        try:
            logger.info("OpenAI APIへの接続テストを開始します")
            
            # Chat completions APIを呼び出す
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "あなたは役立つアシスタントです。"},
                    {"role": "user", "content": "こんにちは、APIテストです。「OpenAI API接続テスト成功」と応答してください。"}
                ],
                max_tokens=50
            )
            
            # レスポンスを確認
            message = response.choices[0].message.content
            logger.info(f"APIレスポンス: {message}")
            
            # 応答の検証
            if "OpenAI API接続テスト成功" in message:
                logger.info("接続テスト成功: 期待通りの応答を受信しました")
                return True, message
            else:
                logger.warning(f"期待する文字列が応答に含まれていません: {message}")
                return False, message
                
        except Exception as e:
            logger.error(f"接続テストエラー: {str(e)}")
            return False, str(e)
    
    def test_image_generation(self):
        """画像生成APIの接続テスト"""
        try:
            logger.info("OpenAI 画像生成APIへの接続テストを開始します")
            
            # 画像生成APIを呼び出す
            response = openai.images.generate(
                model="dall-e-3",
                prompt="A cute robot waving hello, digital art style",
                n=1,
                size="1024x1024"
            )
            
            # レスポンスを確認
            image_url = response.data[0].url
            logger.info(f"画像生成テスト成功: URL: {image_url[:30]}...")
            return True, image_url
            
        except Exception as e:
            logger.error(f"画像生成テストエラー: {str(e)}")
            return False, str(e)
    
    def test_moderation(self):
        """モデレーションAPIの接続テスト"""
        try:
            logger.info("OpenAI モデレーションAPIへの接続テストを開始します")
            
            # モデレーションAPIを呼び出す
            response = openai.moderations.create(
                input="テスト文章です。これはOpenAI接続テストの一部です。"
            )
            
            # レスポンスを確認
            result = response.results[0]
            logger.info(f"モデレーション結果: flagged={result.flagged}")
            return True, result
            
        except Exception as e:
            logger.error(f"モデレーションテストエラー: {str(e)}")
            return False, str(e)

def run_tests():
    """テストを実行する"""
    try:
        tester = OpenAIConnectionTest()
        
        # テキスト生成のテスト
        success, message = tester.test_connection()
        print(f"Chat Completions APIテスト: {'成功' if success else '失敗'}")
        print(f"応答メッセージ: {message}")
        print("-" * 50)
        
        # 画像生成のテスト（オプション）
        try:
            success, url = tester.test_image_generation()
            print(f"画像生成APIテスト: {'成功' if success else '失敗'}")
            if success:
                print(f"生成された画像URL: {url[:50]}...")
            else:
                print(f"エラー: {url}")
        except Exception as e:
            print(f"画像生成APIテストをスキップしました: {str(e)}")
            
        print("-" * 50)
        
        # モデレーションのテスト
        success, result = tester.test_moderation()
        print(f"モデレーションAPIテスト: {'成功' if success else '失敗'}")
        if success:
            print(f"モデレーション結果: {result}")
        else:
            print(f"エラー: {result}")
            
    except Exception as e:
        print(f"テスト実行中にエラーが発生しました: {str(e)}")
        return False
        
    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1) 