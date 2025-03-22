#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OpenAI APIを使用してHTMLを分析するモジュール
HTMLコンテンツを最適化してOpenAI APIで処理します
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import traceback
from datetime import datetime

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent.parent.parent.parent)
import sys
sys.path.append(project_root)

# 独自モジュールのインポート
from openai_token_helper import OpenAITokenHelper

# ロガー設定
logger = logging.getLogger(__name__)

class OpenAIHTMLAnalyzer:
    """OpenAI APIを使用してHTMLを分析するクラス"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        """
        初期化
        
        Args:
            api_key: OpenAI APIキー（Noneの場合は環境変数から取得）
            model: 使用するモデル名
        """
        # トークンヘルパーの初期化
        self.token_helper = OpenAITokenHelper(api_key=api_key, model=model)
        
        # 結果保存用ディレクトリ
        self.results_dir = os.path.join(project_root, "data", "analysis")
        os.makedirs(self.results_dir, exist_ok=True)
        
        logger.info(f"OpenAIHTMLAnalyzer初期化: モデル={model}")
    
    def _create_system_prompt(self, task_type: str) -> str:
        """
        タスクタイプに応じたシステムプロンプトを作成
        
        Args:
            task_type: タスクの種類
            
        Returns:
            システムプロンプト
        """
        prompts = {
            "extract_elements": "あなたはHTMLから要素を抽出するエキスパートです。ボタン、リンク、フォーム要素、日本語テキストなど、ユーザーインターフェースの重要な要素を特定し、それらの関連情報を提供してください。",
            "analyze_ui": "あなたはUIデザインと分析のエキスパートです。HTMLのユーザーインターフェースを分析し、その構造、レイアウト、主な機能について詳細なレポートを提供してください。",
            "find_buttons": "あなたはHTMLからボタン要素を特定するエキスパートです。すべてのボタン要素を見つけ、それらのテキスト、クラス、ID、その他の重要な属性を抽出してください。日本語のテキストを含むボタンには特に注目してください。",
            "find_links": "あなたはHTMLからリンク要素を特定するエキスパートです。すべてのリンク要素を見つけ、それらのテキスト、URL、クラス、その他の重要な属性を抽出してください。日本語のテキストを含むリンクには特に注目してください。",
            "find_forms": "あなたはHTMLからフォーム要素を特定するエキスパートです。すべてのフォームとその入力フィールドを見つけ、フィールドタイプ、ラベル、検証要件などの詳細情報を提供してください。",
            "find_japanese_text": "あなたはHTMLから日本語テキストを抽出するエキスパートです。すべての日本語テキストを見つけ、それらが含まれている要素の種類と構造についての情報を提供してください。",
            "analyze_dashboard": "あなたはダッシュボードUIの分析エキスパートです。このダッシュボードの主要な指標、グラフ、インタラクティブ要素を特定し、それらがどのように構成されているかを説明してください。",
            "analyze_login": "あなたはログイン画面のセキュリティと使いやすさを分析するエキスパートです。このログインフォームの要素、セキュリティ機能、ユーザー体験について詳細に説明してください。"
        }
        
        return prompts.get(task_type, "あなたはHTML分析の専門家です。提供されたHTMLを分析し、その構造と内容について詳細な情報を提供してください。")
    
    def _create_user_prompt(self, task_type: str, additional_instructions: Optional[str] = None) -> str:
        """
        タスクタイプに応じたユーザープロンプトを作成
        
        Args:
            task_type: タスクの種類
            additional_instructions: 追加の指示
            
        Returns:
            ユーザープロンプト
        """
        prompts = {
            "extract_elements": "以下のHTMLから重要な要素を抽出してください。ボタン、リンク、フォーム入力、日本語テキストなどに注目してください。それぞれの要素のテキスト、属性、役割などを詳しく説明してください。",
            "analyze_ui": "以下のHTMLのユーザーインターフェースを分析してください。UIの構造、主要なセクション、インタラクティブ要素、全体的なデザインパターンについて詳しく説明してください。",
            "find_buttons": "以下のHTMLからすべてのボタン要素を特定してください。通常のボタン、送信ボタン、リンクとして機能するボタンなど、すべてのタイプのボタンを含めてください。各ボタンのテキスト、機能、スタイルクラスを一覧にしてください。",
            "find_links": "以下のHTMLからすべてのリンク（アンカー）要素を特定してください。各リンクのテキスト、URL、ターゲット、およびその他の重要な属性を一覧にしてください。",
            "find_forms": "以下のHTMLからすべてのフォームとその入力フィールドを特定してください。各フォームの目的、入力フィールドのタイプ、ラベル、および検証要件を詳しく説明してください。",
            "find_japanese_text": "以下のHTMLからすべての日本語テキストを抽出してください。各テキストが含まれている要素のタイプと階層構造も特定してください。",
            "analyze_dashboard": "以下のHTMLはダッシュボード画面です。このダッシュボードの主要な指標、グラフ、フィルタリングオプション、ナビゲーション要素を特定し、それらがどのように構成されているかを説明してください。ユーザーができるアクションも含めてください。",
            "analyze_login": "以下のHTMLはログイン画面です。ログインフォームの構成要素、セキュリティ機能（パスワードの要件、2要素認証など）、エラー処理、およびユーザー支援機能（パスワードリセットリンクなど）を特定してください。"
        }
        
        prompt = prompts.get(task_type, "以下のHTMLを分析し、その構造と内容について詳細な情報を提供してください。")
        
        if additional_instructions:
            prompt = f"{prompt}\n\n追加の指示:\n{additional_instructions}"
            
        return prompt
    
    def analyze_html_file(self, html_file_path: str, task_type: str = "extract_elements", 
                           additional_instructions: Optional[str] = None, 
                           save_result: bool = True) -> Dict[str, Any]:
        """
        HTMLファイルを分析
        
        Args:
            html_file_path: 分析するHTMLファイルのパス
            task_type: 分析タスクの種類
            additional_instructions: 追加の指示
            save_result: 結果を保存するかどうか
            
        Returns:
            分析結果を含む辞書
        """
        try:
            # HTMLファイルを読み込み
            with open(html_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            result = self.analyze_html_content(
                html_content, 
                task_type=task_type, 
                additional_instructions=additional_instructions,
                source_file=html_file_path,
                save_result=save_result
            )
            
            return result
            
        except Exception as e:
            error_msg = f"HTMLファイル分析中にエラーが発生: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": error_msg,
                "file": html_file_path
            }
    
    def analyze_html_content(self, html_content: str, task_type: str = "extract_elements", 
                             additional_instructions: Optional[str] = None, 
                             source_file: Optional[str] = None, 
                             save_result: bool = True) -> Dict[str, Any]:
        """
        HTML内容を分析
        
        Args:
            html_content: 分析するHTML内容
            task_type: 分析タスクの種類
            additional_instructions: 追加の指示
            source_file: 元のHTMLファイルのパス（保存用）
            save_result: 結果を保存するかどうか
            
        Returns:
            分析結果を含む辞書
        """
        if not html_content:
            return {"success": False, "error": "HTMLコンテンツがありません"}
        
        try:
            # システムプロンプトとユーザープロンプトを作成
            system_prompt = self._create_system_prompt(task_type)
            user_prompt = self._create_user_prompt(task_type, additional_instructions)
            
            # HTMLの分析
            logger.info(f"HTMLの分析を開始: タスク={task_type}")
            
            # ファイル名の特定（保存用）
            if source_file:
                file_name = os.path.basename(source_file)
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_name = f"html_analysis_{timestamp}.html"
            
            # 推奨モデルの確認
            recommended_model = self.token_helper.get_recommended_model(html_content)
            current_model = self.token_helper.model
            
            if recommended_model != current_model:
                logger.info(f"推奨モデルが現在のモデルと異なります: 現在={current_model}, 推奨={recommended_model}")
                if task_type in ["analyze_ui", "analyze_dashboard"]:
                    logger.info(f"タスク '{task_type}' のために推奨モデル '{recommended_model}' に切り替えます")
                    self.token_helper.switch_model(recommended_model)
            
            # OpenAI APIを使用してHTMLを処理
            api_result = self.token_helper.process_html_with_openai(
                html_content, 
                system_prompt, 
                user_prompt, 
                max_tokens=2000
            )
            
            # 結果を整形
            result = {
                "success": api_result.get("success", False),
                "task_type": task_type,
                "source_file": source_file,
                "timestamp": datetime.now().isoformat(),
                "model": self.token_helper.model,
                "method": api_result.get("method", ""),
                "response": api_result.get("response", ""),
            }
            
            if not result["success"]:
                result["error"] = api_result.get("error", "不明なエラー")
            
            # 結果を保存
            if save_result and result["success"]:
                self._save_analysis_result(result, file_name, task_type)
            
            return result
            
        except Exception as e:
            error_msg = f"HTML分析中にエラーが発生: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": error_msg,
                "task_type": task_type
            }
    
    def _save_analysis_result(self, result: Dict[str, Any], file_name: str, task_type: str) -> str:
        """
        分析結果を保存
        
        Args:
            result: 保存する分析結果
            file_name: 元のHTMLファイル名
            task_type: 分析タスクの種類
            
        Returns:
            保存されたファイルパス
        """
        # ファイル名から拡張子を除去
        base_name = os.path.splitext(file_name)[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 結果ファイル名を作成
        result_file_name = f"{base_name}_{task_type}_{timestamp}.json"
        result_file_path = os.path.join(self.results_dir, result_file_name)
        
        # 結果を保存
        try:
            with open(result_file_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            logger.info(f"分析結果を保存しました: {result_file_path}")
            return result_file_path
            
        except Exception as e:
            logger.error(f"分析結果の保存中にエラーが発生: {str(e)}")
            logger.error(traceback.format_exc())
            return ""
    
    def batch_analyze_html_files(self, html_dir: str, task_type: str = "extract_elements", 
                                file_pattern: str = "*.html") -> List[Dict[str, Any]]:
        """
        ディレクトリ内の複数のHTMLファイルをバッチ分析
        
        Args:
            html_dir: HTMLファイルを含むディレクトリ
            task_type: 分析タスクの種類
            file_pattern: 分析対象ファイルのパターン
            
        Returns:
            分析結果のリスト
        """
        import glob
        
        # HTMLファイルのパスを取得
        pattern = os.path.join(html_dir, file_pattern)
        html_files = glob.glob(pattern)
        
        if not html_files:
            logger.warning(f"指定されたパターンに一致するHTMLファイルが見つかりません: {pattern}")
            return []
        
        logger.info(f"{len(html_files)}個のHTMLファイルを分析します")
        
        # 各ファイルを分析
        results = []
        for html_file in html_files:
            logger.info(f"ファイルを分析中: {os.path.basename(html_file)}")
            
            result = self.analyze_html_file(html_file, task_type=task_type)
            results.append(result)
            
            # ファイル間に少し待機（APIレート制限を避けるため）
            if len(html_files) > 1:
                import time
                time.sleep(1)
        
        # 成功・失敗の数をカウント
        success_count = sum(1 for r in results if r.get("success", False))
        
        logger.info(f"バッチ分析完了: {success_count}/{len(results)}ファイルが成功")
        
        return results


# コマンドラインから実行する場合のエントリーポイント
if __name__ == "__main__":
    import argparse
    
    # ロギングの設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description='OpenAI APIを使用してHTMLを分析')
    parser.add_argument('--file', '-f', help='分析するHTMLファイルのパス')
    parser.add_argument('--dir', '-d', help='分析するHTMLファイルを含むディレクトリ')
    parser.add_argument('--pattern', '-p', default='*.html', help='分析対象ファイルのパターン（--dirと共に使用）')
    parser.add_argument('--task', '-t', default='extract_elements', 
                        choices=['extract_elements', 'analyze_ui', 'find_buttons', 'find_links', 
                                'find_forms', 'find_japanese_text', 'analyze_dashboard', 'analyze_login'],
                        help='分析タスクの種類')
    parser.add_argument('--model', '-m', default='gpt-3.5-turbo',
                        choices=['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo'],
                        help='使用するOpenAIモデル')
    parser.add_argument('--instructions', '-i', help='追加の指示')
    
    args = parser.parse_args()
    
    # 分析器の初期化
    analyzer = OpenAIHTMLAnalyzer(model=args.model)
    
    if args.file:
        # 単一ファイルの分析
        logger.info(f"ファイル {args.file} の分析を開始")
        result = analyzer.analyze_html_file(
            args.file, 
            task_type=args.task, 
            additional_instructions=args.instructions
        )
        
        if result.get("success", False):
            print(f"\n=== 分析結果（{args.task}） ===")
            print(f"ファイル: {args.file}")
            print(f"モデル: {result.get('model', args.model)}")
            print(f"方法: {result.get('method', '')}")
            print("\n結果:")
            print(result.get("response", ""))
        else:
            print(f"\n=== 分析エラー ===")
            print(f"ファイル: {args.file}")
            print(f"エラー: {result.get('error', '不明なエラー')}")
            
    elif args.dir:
        # ディレクトリ内の複数ファイルを分析
        logger.info(f"ディレクトリ {args.dir} 内のファイルの分析を開始")
        results = analyzer.batch_analyze_html_files(
            args.dir, 
            task_type=args.task, 
            file_pattern=args.pattern
        )
        
        if results:
            success_count = sum(1 for r in results if r.get("success", False))
            print(f"\n=== バッチ分析結果 ===")
            print(f"タスク: {args.task}")
            print(f"成功: {success_count}/{len(results)}")
        else:
            print("\n=== バッチ分析エラー ===")
            print("分析対象ファイルが見つかりませんでした")
    
    else:
        parser.print_help() 