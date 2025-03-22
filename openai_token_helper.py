#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OpenAI APIのトークン制限問題を解決するためのヘルパークラス
HTMLコンテンツを最適化し、必要に応じて分割する機能を提供します
"""

import os
import json
import tiktoken
import re
from pathlib import Path
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Any, Tuple, Optional, Union
import openai

# ロガーの設定
logger = logging.getLogger(__name__)

class OpenAITokenHelper:
    """OpenAI APIのトークン制限問題に対処するためのヘルパークラス"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        """
        初期化
        
        Args:
            api_key: OpenAI APIキー（Noneの場合は環境変数から取得）
            model: 使用するモデル名
        """
        # APIキーの設定
        if api_key:
            self.api_key = api_key
            openai.api_key = api_key
        else:
            # 環境変数から取得を試みる
            self.api_key = os.environ.get("OPENAI_API_KEY", "")
            if not self.api_key:
                logger.warning("OpenAI APIキーが設定されていません")
            else:
                openai.api_key = self.api_key
        
        # 使用するモデルを設定
        self.model = model
        
        # トークナイザーの初期化
        self.tokenizers = {
            "gpt-3.5-turbo": tiktoken.encoding_for_model("gpt-3.5-turbo"),
            "gpt-4": tiktoken.encoding_for_model("gpt-4"),
            "gpt-4-turbo": tiktoken.encoding_for_model("gpt-4")
        }
        
        # 各モデルのトークン制限
        self.model_token_limits = {
            "gpt-3.5-turbo": 16385,
            "gpt-4": 8192,
            "gpt-4-turbo": 128000
        }
        
        # 現在のモデルのトークン制限を設定
        self.token_limit = self.model_token_limits.get(model, 16385)
        
        logger.info(f"OpenAITokenHelper初期化: モデル={model}, トークン制限={self.token_limit}")
    
    def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """
        テキストのトークン数をカウント
        
        Args:
            text: トークン数を計算するテキスト
            model: 使用するモデル名（Noneの場合は初期化時のモデルを使用）
            
        Returns:
            トークン数
        """
        if not text:
            return 0
            
        use_model = model if model else self.model
        
        if use_model not in self.tokenizers:
            logger.warning(f"モデル '{use_model}' のトークナイザーが見つかりません。デフォルトを使用します。")
            use_model = "gpt-3.5-turbo"
            
        tokenizer = self.tokenizers[use_model]
        tokens = tokenizer.encode(text)
        return len(tokens)
    
    def clean_html(self, html_content: str) -> str:
        """
        HTMLから不要な要素を削除してサイズを小さくする
        
        Args:
            html_content: クリーニングするHTML
            
        Returns:
            クリーニング後のHTML
        """
        if not html_content:
            return ""
            
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # スクリプトタグを削除
        for script in soup.find_all('script'):
            script.decompose()
        
        # スタイルタグを削除
        for style in soup.find_all('style'):
            style.decompose()
        
        # コメントを削除
        for comment in soup.find_all(string=lambda text: isinstance(text, str) and text.strip().startswith('<!--')):
            comment.extract()
        
        # 特定の属性を削除（data-*属性など）
        for tag in soup.find_all(True):
            attrs_to_remove = [attr for attr in tag.attrs 
                              if attr.startswith(('data-', 'aria-')) 
                              or attr in ['style'] 
                              and not (tag.name == 'input' and attr in ['id', 'name', 'class'])]
            for attr in attrs_to_remove:
                del tag[attr]
        
        # 空白を整理
        clean_html = str(soup)
        clean_html = re.sub(r'\s+', ' ', clean_html)
        
        original_tokens = self.count_tokens(html_content)
        clean_tokens = self.count_tokens(clean_html)
        reduction = (original_tokens - clean_tokens) / original_tokens * 100 if original_tokens > 0 else 0
        
        logger.info(f"HTML最適化: {original_tokens}→{clean_tokens}トークン (削減率: {reduction:.1f}%)")
        
        return clean_html
    
    def extract_important_elements(self, html_content: str) -> Dict[str, Any]:
        """
        HTMLから重要な要素のみを抽出する
        
        Args:
            html_content: 抽出元のHTML
            
        Returns:
            抽出された重要な要素を含む辞書
        """
        if not html_content:
            return {"metadata": {}, "important_elements": [], "element_count": 0}
            
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # メタデータの抽出
        metadata = {
            "title": soup.title.string if soup.title else "No Title",
            "url": soup.find('meta', {'property': 'og:url'}).get('content', '') if soup.find('meta', {'property': 'og:url'}) else ""
        }
        
        # 重要なボタンやリンクを抽出
        important_elements = []
        
        # ボタン要素
        for button in soup.find_all(['button', 'input'], type=["button", "submit"]):
            text = button.get_text(strip=True)
            if text:
                important_elements.append({
                    "type": "button",
                    "text": text,
                    "attributes": {k: v for k, v in button.attrs.items() if k in ['id', 'name', 'class']}
                })
        
        # リンク要素
        for link in soup.find_all('a'):
            text = link.get_text(strip=True)
            if text:
                important_elements.append({
                    "type": "link",
                    "text": text,
                    "href": link.get('href', ''),
                    "attributes": {k: v for k, v in link.attrs.items() if k in ['id', 'name', 'class']}
                })
        
        # 入力フィールド
        for input_field in soup.find_all('input', type=["text", "password", "email", "number", "date"]):
            important_elements.append({
                "type": "input",
                "input_type": input_field.get('type', ''),
                "name": input_field.get('name', ''),
                "id": input_field.get('id', ''),
                "placeholder": input_field.get('placeholder', ''),
                "attributes": {k: v for k, v in input_field.attrs.items() if k in ['id', 'name', 'class', 'placeholder']}
            })
        
        # 日本語テキストを含む要素を抽出
        japanese_pattern = re.compile(r'[一-龠]+|[ぁ-ん]+|[ァ-ヴー]+')
        for element in soup.find_all(text=japanese_pattern):
            if element.parent.name not in ['script', 'style']:
                parent_attrs = {}
                if hasattr(element.parent, 'attrs'):
                    parent_attrs = {k: v for k, v in element.parent.attrs.items() if k in ['id', 'name', 'class']}
                
                important_elements.append({
                    "type": "japanese_text",
                    "text": element.strip(),
                    "parent_tag": element.parent.name,
                    "parent_attributes": parent_attrs
                })
        
        # 結果を整形
        result = {
            "metadata": metadata,
            "important_elements": important_elements,
            "element_count": len(important_elements)
        }
        
        logger.info(f"重要な要素を{len(important_elements)}個抽出しました")
        
        return result
    
    def split_html_by_tags(self, html_content: str, max_tokens: Optional[int] = None) -> List[str]:
        """
        HTMLを主要なタグで分割
        
        Args:
            html_content: 分割するHTML
            max_tokens: 分割後の各部分の最大トークン数（Noneの場合はモデルのトークン制限の80%）
            
        Returns:
            分割されたHTMLの部分のリスト
        """
        if not html_content:
            return []
            
        if max_tokens is None:
            max_tokens = int(self.token_limit * 0.8)
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # HTML構造を保持するためのヘッダー部分
        header = f"<!DOCTYPE html><html><head><title>{soup.title.string if soup.title else ''}</title></head><body>"
        footer = "</body></html>"
        
        # 分割用の主要なタグを特定（bodyの直下の要素など）
        main_tags = []
        if soup.body:
            main_tags = soup.body.find_all(recursive=False)
        
        if not main_tags:
            # 主要なタグが見つからない場合は特定のタグで探す
            main_tags = soup.find_all(['div', 'section', 'article', 'nav', 'main', 'header', 'footer'])
        
        # 分割されたHTMLを格納するリスト
        html_parts = []
        current_part = header
        current_tokens = self.count_tokens(current_part)
        
        for tag in main_tags:
            tag_html = str(tag)
            tag_tokens = self.count_tokens(tag_html)
            
            # タグ単体が大きすぎる場合は再帰的に分割
            if tag_tokens > max_tokens:
                # 子要素がある場合は子要素ごとに分割
                if hasattr(tag, 'contents') and len(tag.contents) > 0:
                    for child in tag.contents:
                        child_html = str(child)
                        child_tokens = self.count_tokens(child_html)
                        
                        if current_tokens + child_tokens > max_tokens:
                            # 現在のパートを保存して新しいパートを開始
                            html_parts.append(current_part + footer)
                            current_part = header
                            current_tokens = self.count_tokens(current_part)
                        
                        current_part += child_html
                        current_tokens += child_tokens
                else:
                    # 子要素がない場合は文字列で分割
                    tag_text = tag_html
                    while tag_text:
                        chunk_size = min(1000, len(tag_text))
                        chunk = tag_text[:chunk_size]
                        chunk_tokens = self.count_tokens(chunk)
                        
                        if current_tokens + chunk_tokens > max_tokens:
                            html_parts.append(current_part + footer)
                            current_part = header
                            current_tokens = self.count_tokens(current_part)
                        
                        current_part += chunk
                        current_tokens += chunk_tokens
                        tag_text = tag_text[chunk_size:]
            else:
                # 通常の追加処理
                if current_tokens + tag_tokens > max_tokens:
                    html_parts.append(current_part + footer)
                    current_part = header
                    current_tokens = self.count_tokens(current_part)
                
                current_part += tag_html
                current_tokens += tag_tokens
        
        # 最後のパートを追加
        if current_part != header:
            html_parts.append(current_part + footer)
        
        logger.info(f"HTMLを{len(html_parts)}パートに分割しました")
        for i, part in enumerate(html_parts):
            part_tokens = self.count_tokens(part)
            logger.debug(f"パート{i+1}: {part_tokens}トークン")
        
        return html_parts
    
    def optimize_html_for_openai(self, html_content: str) -> Dict[str, Any]:
        """
        HTMLをOpenAI APIに最適な形式に変換する
        
        Args:
            html_content: 最適化するHTML
            
        Returns:
            最適化された結果を含む辞書
        """
        if not html_content:
            return {"success": False, "error": "HTMLコンテンツがありません"}
        
        # 元のトークン数をカウント
        original_tokens = self.count_tokens(html_content)
        logger.info(f"元のHTMLトークン数: {original_tokens}")
        
        # トークン制限内かチェック
        if original_tokens <= self.token_limit:
            logger.info(f"元のHTMLはトークン制限内です（{original_tokens} <= {self.token_limit}）")
            return {
                "success": True,
                "method": "original",
                "tokens": original_tokens,
                "content": html_content,
                "parts": [html_content],
                "needs_splitting": False
            }
        
        # HTMLをクリーニング
        clean_html_content = self.clean_html(html_content)
        clean_tokens = self.count_tokens(clean_html_content)
        logger.info(f"クリーンHTMLトークン数: {clean_tokens}")
        
        # クリーニングしたHTMLがトークン制限内かチェック
        if clean_tokens <= self.token_limit:
            logger.info(f"クリーニングしたHTMLはトークン制限内です（{clean_tokens} <= {self.token_limit}）")
            return {
                "success": True,
                "method": "cleaned",
                "tokens": clean_tokens,
                "content": clean_html_content,
                "parts": [clean_html_content],
                "needs_splitting": False
            }
        
        # 重要な要素を抽出
        important_elements = self.extract_important_elements(clean_html_content)
        important_elements_json = json.dumps(important_elements, ensure_ascii=False, indent=2)
        important_elements_tokens = self.count_tokens(important_elements_json)
        logger.info(f"重要要素のJSONトークン数: {important_elements_tokens}")
        
        # 重要要素がトークン制限内かチェック
        if important_elements_tokens <= self.token_limit:
            logger.info(f"重要要素のJSONはトークン制限内です（{important_elements_tokens} <= {self.token_limit}）")
            return {
                "success": True,
                "method": "important_elements",
                "tokens": important_elements_tokens,
                "content": important_elements_json,
                "elements": important_elements,
                "needs_splitting": False
            }
        
        # HTMLを分割
        html_parts = self.split_html_by_tags(clean_html_content)
        
        # 分割されたHTMLのトークン数をチェック
        parts_tokens = [self.count_tokens(part) for part in html_parts]
        logger.info(f"分割されたHTML: {len(html_parts)}パート")
        for i, tokens in enumerate(parts_tokens):
            logger.debug(f"パート{i+1}: {tokens}トークン")
        
        # すべてのパートがトークン制限内であることを確認
        if all(tokens <= self.token_limit for tokens in parts_tokens):
            logger.info("すべての分割パートがトークン制限内です")
            return {
                "success": True,
                "method": "split",
                "tokens": parts_tokens,
                "parts": html_parts,
                "needs_splitting": True,
                "part_count": len(html_parts)
            }
        
        # いずれの方法でも処理できない場合
        logger.warning("いずれの最適化方法でもトークン制限内に収まりませんでした")
        return {
            "success": False,
            "error": "トークン制限を超えるHTMLを処理できません",
            "tokens": original_tokens,
            "limit": self.token_limit
        }
    
    def _create_messages_for_html(self, html_content: str, system_prompt: str, user_prompt: str) -> List[Dict[str, str]]:
        """
        HTML用のメッセージを作成
        
        Args:
            html_content: HTML内容
            system_prompt: システムプロンプト
            user_prompt: ユーザープロンプト
            
        Returns:
            OpenAI APIに送信するメッセージのリスト
        """
        user_content = f"{user_prompt}\n\n{html_content}"
        
        # トークン数をチェック
        total_tokens = self.count_tokens(system_prompt) + self.count_tokens(user_content)
        if total_tokens > self.token_limit:
            # HTMLの一部を省略
            html_preview = html_content[:1000] + "..."
            user_content = f"{user_prompt}\n\n{html_preview}"
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
    
    def process_html_with_openai(self, html_content: str, system_prompt: str, user_prompt: str, 
                                max_tokens: int = 1000) -> Dict[str, Any]:
        """
        HTMLをOpenAI APIで処理する
        
        Args:
            html_content: 処理するHTML
            system_prompt: システムプロンプト
            user_prompt: ユーザープロンプト
            max_tokens: 応答の最大トークン数
            
        Returns:
            OpenAI APIの応答と処理ステータスを含む辞書
        """
        if not self.api_key:
            return {"success": False, "error": "OpenAI APIキーが設定されていません"}
        
        # HTMLを最適化
        optimization_result = self.optimize_html_for_openai(html_content)
        
        if not optimization_result.get("success", False):
            return optimization_result
        
        method = optimization_result.get("method", "")
        
        try:
            if method == "original" or method == "cleaned":
                # 元のHTMLまたはクリーニングしたHTMLを使用
                content = optimization_result.get("content", "")
                messages = self._create_messages_for_html(content, system_prompt, user_prompt)
                
                response = openai.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens
                )
                
                return {
                    "success": True,
                    "method": method,
                    "response": response.choices[0].message.content,
                    "tokens": optimization_result.get("tokens", 0)
                }
                
            elif method == "important_elements":
                # 重要要素を使用
                elements = optimization_result.get("elements", {})
                elements_json = json.dumps(elements, ensure_ascii=False)
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"{user_prompt}\n\nHTMLから抽出された重要な要素:\n{elements_json}"}
                ]
                
                response = openai.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens
                )
                
                return {
                    "success": True,
                    "method": method,
                    "response": response.choices[0].message.content,
                    "tokens": optimization_result.get("tokens", 0)
                }
                
            elif method == "split":
                # 分割されたHTMLを使用
                parts = optimization_result.get("parts", [])
                responses = []
                
                # 各パートを処理
                for i, part in enumerate(parts):
                    messages = self._create_messages_for_html(
                        part, 
                        system_prompt, 
                        f"{user_prompt}\n\n注意: これはHTMLの{i+1}/{len(parts)}パートです。"
                    )
                    
                    response = openai.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        max_tokens=max_tokens
                    )
                    
                    responses.append(response.choices[0].message.content)
                
                # 応答を結合
                combined_response = "\n\n".join([f"パート{i+1}の結果:\n{resp}" for i, resp in enumerate(responses)])
                
                # 結合した応答がトークン制限を超える場合は要約
                if self.count_tokens(combined_response) > self.token_limit:
                    summary_messages = [
                        {"role": "system", "content": "あなたは複数の分析結果を要約するアシスタントです。"},
                        {"role": "user", "content": f"以下は{len(responses)}パートに分けられたHTMLの分析結果です。これらを簡潔に要約してください。\n\n{combined_response[:2000]}..."}
                    ]
                    
                    summary_response = openai.chat.completions.create(
                        model=self.model,
                        messages=summary_messages,
                        max_tokens=max_tokens
                    )
                    
                    combined_response = summary_response.choices[0].message.content
                
                return {
                    "success": True,
                    "method": method,
                    "response": combined_response,
                    "part_responses": responses,
                    "part_count": len(parts)
                }
                
            else:
                return {"success": False, "error": f"不明な最適化方法: {method}"}
                
        except Exception as e:
            logger.error(f"OpenAI API呼び出し中にエラーが発生: {str(e)}")
            return {"success": False, "error": f"API呼び出しエラー: {str(e)}"}
    
    def get_recommended_model(self, html_content: str) -> str:
        """
        HTMLのサイズに基づいて最適なモデルを推奨する
        
        Args:
            html_content: HTML内容
            
        Returns:
            推奨モデル名
        """
        if not html_content:
            return self.model
        
        # 元のトークン数をカウント
        original_tokens = self.count_tokens(html_content)
        
        # クリーニング後のトークン数を推定
        cleaned_tokens = original_tokens * 0.6  # 経験的に約40%削減されると仮定
        
        # 各モデルと比較
        suitable_models = []
        for model, limit in self.model_token_limits.items():
            if cleaned_tokens <= limit:
                suitable_models.append((model, cleaned_tokens/limit))
        
        if suitable_models:
            # トークン使用率が最も低いモデルを選択
            best_model = min(suitable_models, key=lambda x: x[1])
            return best_model[0]
        else:
            # すべてのモデルで分割が必要な場合は最もトークン制限が大きいモデルを返す
            return max(self.model_token_limits.items(), key=lambda x: x[1])[0]
            
    def switch_model(self, model: str) -> bool:
        """
        使用するモデルを切り替える
        
        Args:
            model: 新しいモデル名
            
        Returns:
            切り替えが成功したかどうか
        """
        if model not in self.model_token_limits:
            logger.warning(f"不明なモデル: {model}")
            return False
            
        self.model = model
        self.token_limit = self.model_token_limits[model]
        logger.info(f"モデルを{model}に切り替えました（トークン制限: {self.token_limit}）")
        return True


# 使用例
if __name__ == "__main__":
    # ロギングの設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # テスト用HTMLファイルのパス
    import sys
    
    if len(sys.argv) < 2:
        print("使用法: python openai_token_helper.py <HTMLファイルパス>")
        sys.exit(1)
    
    html_file_path = sys.argv[1]
    
    try:
        # HTMLファイルを読み込み
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # ヘルパーを初期化
        helper = OpenAITokenHelper()
        
        # HTML分析
        print("\n=== HTML分析 ===")
        print(f"ファイル: {html_file_path}")
        print(f"元のトークン数: {helper.count_tokens(html_content)}")
        
        # 最適化
        print("\n=== HTML最適化 ===")
        optimization_result = helper.optimize_html_for_openai(html_content)
        
        if optimization_result.get("success", False):
            print(f"最適化方法: {optimization_result.get('method', '')}")
            if optimization_result.get("needs_splitting", False):
                print(f"分割数: {optimization_result.get('part_count', 0)}パート")
            else:
                print(f"最適化後トークン数: {optimization_result.get('tokens', 0)}")
        else:
            print(f"最適化失敗: {optimization_result.get('error', '')}")
        
        # 推奨モデル
        print("\n=== 推奨モデル ===")
        recommended_model = helper.get_recommended_model(html_content)
        print(f"推奨モデル: {recommended_model}")
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        import traceback
        traceback.print_exc() 