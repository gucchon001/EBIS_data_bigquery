import os
import sys
import json
from datetime import datetime, timedelta

# プロジェクトルートへのパスを追加
sys.path.append(os.path.abspath('.'))

from src.utils.environment import EnvironmentUtils as env
from src.utils.logging_config import get_logger
from src.modules.ai_element_extractor import AIElementExtractor

logger = get_logger(__name__)

def test_detail_analytics_with_operations():
    """detail_analyticsセクションの要素抽出と操作実行をテストする"""
    try:
        # 環境変数の読み込み
        env.load_env()
        
        # ディレクションファイルのパス
        direction_file = "docs/ai_selenium_direction.md"
        section = "detail_analytics"
        
        logger.info(f"AIElementExtractorを使用して {section} セクションの要素抽出と操作実行をテストします")
        
        # AIElementExtractorのインスタンス作成
        extractor = AIElementExtractor(
            direction_file=direction_file,
            section=section
        )
        
        # AIElementExtractorのrunメソッドを実行
        logger.info("AIElementExtractorのrunメソッドを実行します")
        success = extractor.run()
        
        if success:
            logger.info("テスト成功: AIElementExtractorのrun実行が完了しました")
            print("テスト成功: AIElementExtractorのrun実行が完了しました")
        else:
            logger.error("テスト失敗: AIElementExtractorのrun実行に失敗しました")
            print("テスト失敗: AIElementExtractorのrun実行に失敗しました")
        
        return success
        
    except Exception as e:
        logger.error(f"テスト中にエラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # ブラウザを終了
        if 'extractor' in locals() and extractor:
            extractor.quit()

def test_detail_analytics_extraction_and_operations():
    """detail_analyticsセクションの要素抽出と手動操作実行をテストする"""
    try:
        # 環境変数の読み込み
        env.load_env()
        
        # ディレクションファイルのパス
        direction_file = "docs/ai_selenium_direction.md"
        section = "detail_analytics"
        
        logger.info(f"AIElementExtractorを使用して {section} セクションの要素抽出と手動操作をテストします")
        
        # AIElementExtractorのインスタンス作成
        extractor = AIElementExtractor(
            direction_file=direction_file,
            section=section
        )
        
        # ブラウザの準備（ヘッドレスモードを無効化）
        logger.info("ブラウザを準備します")
        extractor.prepare_browser(headless=False)
        
        # ディレクションファイルを解析
        logger.info(f"ディレクションファイル {direction_file} のセクション {section} を解析します")
        direction = extractor.parse_direction_file(direction_file, section)
        
        if not direction:
            logger.error(f"セクション {section} が見つかりませんでした")
            return False
        
        logger.info(f"ディレクションの概要: {direction.get('overview', 'なし')}")
        logger.info(f"URL: {direction.get('url', 'なし')}")
        
        # 前提操作（ログインなど）の確認
        prerequisites = direction.get('prerequisites')
        if prerequisites:
            logger.info(f"前提条件があります: {prerequisites}")
            # ここで前提条件の操作を実行する場合の処理を追加
            if "login_page.py" in prerequisites.lower():
                logger.info("ログイン処理を実行します")
                try:
                    # LoginPageクラスをインポート
                    from src.modules.browser.login_page import LoginPage
                    
                    # ログインページインスタンスを作成し、ログイン実行
                    login_page = LoginPage(browser=extractor.browser)
                    login_result = login_page.execute_login_flow()
                    
                    if not login_result:
                        logger.error("ログイン処理に失敗しました")
                        return False
                        
                    logger.info("✅ ログイン処理が完了しました")
                except Exception as e:
                    logger.error(f"ログイン処理中にエラーが発生しました: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    return False
        
        # URLからページコンテンツを取得
        url = direction.get('url')
        if not url:
            logger.error("URLが指定されていません")
            return False
        
        logger.info(f"URLにアクセスしてコンテンツを取得します: {url}")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_file = f"detail_analytics_{timestamp}.html"
        html_result = extractor.get_page_content_with_selenium(url, html_file)
        
        if not html_result or not html_result[0]:
            logger.error("ページコンテンツの取得に失敗しました")
            return False
        
        html_content = html_result[0]  # HTMLコンテンツを取得
        html_file_path = html_result[1]  # 保存されたHTMLファイルのパス
        
        logger.info(f"ページコンテンツを {html_file_path} に保存しました")
        
        # 抽出する要素リストを取得
        elements_to_extract = direction.get('elements_to_extract', [])
        if not elements_to_extract:
            logger.error("抽出する要素が指定されていません")
            return False
        
        logger.info(f"抽出する要素: {', '.join(elements_to_extract)}")
        
        # OpenAI APIを使用して要素を抽出
        logger.info("OpenAI APIを使用して要素を抽出します")
        elements = extractor.extract_elements_with_openai(html_content, elements_to_extract)
        
        if not elements:
            logger.error("要素の抽出に失敗しました")
            return False
        
        # 結果の表示と保存
        logger.info(f"抽出された要素数: {len(elements)}")
        for i, element in enumerate(elements, 1):
            logger.info(f"要素 {i}: {element.get('name')} - XPath: {element.get('xpath')}")
            
        # 結果をJSONファイルに保存
        output_dir = env.resolve_path("data/output")
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"detail_analytics_elements_{timestamp}.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(elements, f, ensure_ascii=False, indent=2)
            
        logger.info(f"抽出結果をファイルに保存しました: {output_file}")
        print(f"要素抽出結果を保存: {output_file}")
        
        # 操作リストがあれば実行
        operations = direction.get('operations')
        if operations:
            logger.info(f"操作リスト（{len(operations)}項目）を実行します")
            if extractor.perform_operations(operations):
                logger.info("操作の実行が完了しました")
            else:
                logger.error("操作の実行に失敗しました")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"テスト中にエラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # ブラウザを終了
        if 'extractor' in locals() and extractor:
            extractor.quit()

if __name__ == "__main__":
    # どちらのテストを実行するか選択
    use_auto_run = False  # Trueの場合は自動実行、Falseの場合は手動ステップ実行
    
    if use_auto_run:
        success = test_detail_analytics_with_operations()
    else:
        success = test_detail_analytics_extraction_and_operations()
        
    if success:
        print("テスト成功: detail_analyticsのテストが完了しました")
    else:
        print("テスト失敗: detail_analyticsのテストに失敗しました") 