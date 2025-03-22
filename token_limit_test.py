#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OpenAI APIのコンテキスト長エラー対策の単体テスト
HTMLコンテンツを分割してトークン数を最適化するテスト
"""

import os
import sys
import glob
import time
import json
import tiktoken
from pathlib import Path
import traceback
from bs4 import BeautifulSoup
import re
import openai
from concurrent.futures import ThreadPoolExecutor

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent)
sys.path.append(project_root)

# 環境変数からOpenAI APIキーを取得
try:
    from src.utils.environment import EnvironmentUtils as env
    env.load_env()
    OPENAI_API_KEY = env.get_env_var("OPENAI_API_KEY", "")
except ImportError:
    # 環境変数から直接取得を試みる
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

if not OPENAI_API_KEY:
    print("警告: OpenAI APIキーが設定されていません")

# OpenAI APIクライアントの設定
openai.api_key = OPENAI_API_KEY

class TokenLimitTest:
    """OpenAI APIのトークン制限テスト"""
    
    def __init__(self):
        """初期化"""
        self.html_files = []
        self.current_file = None
        self.tokenizers = {
            "gpt-3.5-turbo": tiktoken.encoding_for_model("gpt-3.5-turbo"),
            "gpt-4": tiktoken.encoding_for_model("gpt-4"),
            "gpt-4-turbo": tiktoken.encoding_for_model("gpt-4")
        }
        self.model_token_limits = {
            "gpt-3.5-turbo": 16385,
            "gpt-4": 8192,
            "gpt-4-turbo": 128000
        }
        
        # HTMLファイルを検索
        self.find_html_files()
        
        # 結果を保存するディクショナリ
        self.results = {}
    
    def find_html_files(self):
        """data/pagesディレクトリからHTMLファイルを検索"""
        html_dir = os.path.join(project_root, "data", "pages")
        
        if not os.path.exists(html_dir):
            print(f"HTMLディレクトリが見つかりません: {html_dir}")
            return
        
        # HTMLファイルを検索
        pattern = os.path.join(html_dir, "*.html")
        self.html_files = glob.glob(pattern)
        
        # dashboard_htmlファイルとid_ebis_ne_jpファイルを分類
        self.dashboard_htmls = [f for f in self.html_files if "dashboard" in f]
        self.login_htmls = [f for f in self.html_files if "id_ebis_ne_jp" in f]
        
        print(f"HTMLファイルが見つかりました: {len(self.html_files)}個")
        print(f"ダッシュボードHTML: {len(self.dashboard_htmls)}個")
        print(f"ログインページHTML: {len(self.login_htmls)}個")
    
    def load_html_file(self, html_path):
        """HTMLファイルを読み込む"""
        try:
            self.current_file = html_path
            file_name = os.path.basename(html_path)
            
            print(f"\n=== HTMLファイル読み込み: {file_name} ===")
            
            # HTMLファイルの内容を読み込み
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # BeautifulSoupで解析
            self.soup = BeautifulSoup(html_content, 'html.parser')
            
            print(f"HTMLファイルを読み込みました: {file_name}")
            
            if self.soup.title:
                print(f"タイトル: {self.soup.title.string}")
            
            return html_content
            
        except Exception as e:
            print(f"HTMLファイル読み込み中にエラーが発生: {e}")
            print(traceback.format_exc())
            return ""
    
    def count_tokens(self, text, model="gpt-3.5-turbo"):
        """テキストのトークン数をカウント"""
        if model not in self.tokenizers:
            print(f"警告: モデル '{model}' のトークナイザーが見つかりません。デフォルトを使用します。")
            model = "gpt-3.5-turbo"
            
        tokenizer = self.tokenizers[model]
        tokens = tokenizer.encode(text)
        return len(tokens)
    
    def clean_html(self, html_content):
        """HTMLから不要な要素を削除してサイズを小さくする"""
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
            attrs_to_remove = [attr for attr in tag.attrs if attr.startswith('data-') or attr == 'style']
            for attr in attrs_to_remove:
                del tag[attr]
        
        # 空白を整理
        clean_html = str(soup)
        clean_html = re.sub(r'\s+', ' ', clean_html)
        
        return clean_html
    
    def split_html_by_tags(self, html_content, max_tokens=4000, model="gpt-3.5-turbo"):
        """HTMLを主要なタグで分割"""
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
        current_tokens = self.count_tokens(current_part, model)
        
        for tag in main_tags:
            tag_html = str(tag)
            tag_tokens = self.count_tokens(tag_html, model)
            
            # タグ単体が大きすぎる場合は再帰的に分割
            if tag_tokens > max_tokens:
                # 子要素がある場合は子要素ごとに分割
                if hasattr(tag, 'contents') and len(tag.contents) > 0:
                    for child in tag.contents:
                        child_html = str(child)
                        child_tokens = self.count_tokens(child_html, model)
                        
                        if current_tokens + child_tokens > max_tokens:
                            # 現在のパートを保存して新しいパートを開始
                            html_parts.append(current_part + footer)
                            current_part = header
                            current_tokens = self.count_tokens(current_part, model)
                        
                        current_part += child_html
                        current_tokens += child_tokens
                else:
                    # 子要素がない場合は文字列で分割
                    tag_text = tag_html
                    while tag_text:
                        chunk_size = min(1000, len(tag_text))
                        chunk = tag_text[:chunk_size]
                        chunk_tokens = self.count_tokens(chunk, model)
                        
                        if current_tokens + chunk_tokens > max_tokens:
                            html_parts.append(current_part + footer)
                            current_part = header
                            current_tokens = self.count_tokens(current_part, model)
                        
                        current_part += chunk
                        current_tokens += chunk_tokens
                        tag_text = tag_text[chunk_size:]
            else:
                # 通常の追加処理
                if current_tokens + tag_tokens > max_tokens:
                    html_parts.append(current_part + footer)
                    current_part = header
                    current_tokens = self.count_tokens(current_part, model)
                
                current_part += tag_html
                current_tokens += tag_tokens
        
        # 最後のパートを追加
        if current_part != header:
            html_parts.append(current_part + footer)
        
        print(f"HTMLを{len(html_parts)}パートに分割しました")
        for i, part in enumerate(html_parts):
            part_tokens = self.count_tokens(part, model)
            print(f"パート{i+1}: {part_tokens}トークン")
        
        return html_parts
    
    def extract_important_elements(self, html_content):
        """HTMLから重要な要素だけを抽出"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # メタデータの抽出
        metadata = {"title": soup.title.string if soup.title else "No Title"}
        
        # 重要なボタンやリンクを抽出
        important_elements = []
        
        # ボタン要素
        for button in soup.find_all(['button', 'input'], type=["button", "submit"]):
            text = button.get_text(strip=True)
            if text:
                important_elements.append({
                    "type": "button",
                    "text": text,
                    "attributes": dict(button.attrs)
                })
        
        # リンク要素
        for link in soup.find_all('a'):
            text = link.get_text(strip=True)
            if text:
                important_elements.append({
                    "type": "link",
                    "text": text,
                    "href": link.get('href', ''),
                    "attributes": dict(link.attrs)
                })
        
        # 入力フィールド
        for input_field in soup.find_all('input', type=["text", "password", "email", "number", "date"]):
            important_elements.append({
                "type": "input",
                "input_type": input_field.get('type', ''),
                "name": input_field.get('name', ''),
                "id": input_field.get('id', ''),
                "placeholder": input_field.get('placeholder', ''),
                "attributes": dict(input_field.attrs)
            })
        
        # 日本語テキストを含む要素を抽出
        japanese_pattern = re.compile(r'[一-龠]+|[ぁ-ん]+|[ァ-ヴー]+')
        for element in soup.find_all(text=japanese_pattern):
            if element.parent.name not in ['script', 'style']:
                parent_attrs = {}
                if hasattr(element.parent, 'attrs'):
                    parent_attrs = dict(element.parent.attrs)
                
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
        
        print(f"重要な要素を{len(important_elements)}個抽出しました")
        
        return result
    
    def test_token_count(self, html_content, model="gpt-3.5-turbo"):
        """HTMLコンテンツのトークン数をテスト"""
        print(f"\n=== トークン数テスト（モデル: {model}） ===")
        
        # オリジナルのHTMLのトークン数
        original_tokens = self.count_tokens(html_content, model)
        print(f"オリジナルHTMLのトークン数: {original_tokens}")
        
        # クリーニングしたHTMLのトークン数
        clean_html = self.clean_html(html_content)
        clean_tokens = self.count_tokens(clean_html, model)
        print(f"クリーニング後のHTMLのトークン数: {clean_tokens} (削減率: {(original_tokens-clean_tokens)/original_tokens*100:.1f}%)")
        
        # トークン制限に対する割合
        token_limit = self.model_token_limits.get(model, 16385)
        print(f"{model}のトークン制限: {token_limit}")
        print(f"制限に対する割合: {clean_tokens/token_limit*100:.1f}%")
        
        # 分割が必要かチェック
        needs_splitting = clean_tokens > token_limit
        print(f"分割が必要: {'はい' if needs_splitting else 'いいえ'}")
        
        return {
            "original_tokens": original_tokens,
            "clean_tokens": clean_tokens,
            "token_limit": token_limit,
            "needs_splitting": needs_splitting,
            "reduction_rate": (original_tokens-clean_tokens)/original_tokens
        }
    
    def test_different_models(self, html_content):
        """異なるモデルでのトークン数をテスト"""
        print("\n=== 異なるモデルでのトークン数テスト ===")
        
        model_results = {}
        for model in self.model_token_limits.keys():
            result = self.test_token_count(html_content, model)
            model_results[model] = result
        
        # 最適なモデルを提案
        suitable_models = []
        for model, result in model_results.items():
            if not result["needs_splitting"]:
                suitable_models.append((model, result["clean_tokens"]/result["token_limit"]))
        
        if suitable_models:
            # トークン使用率が最も低いモデルを選択
            best_model = min(suitable_models, key=lambda x: x[1])
            print(f"\n最適なモデル: {best_model[0]} (トークン使用率: {best_model[1]*100:.1f}%)")
        else:
            print("\nすべてのモデルで分割が必要です")
        
        return model_results
    
    def test_html_splitting(self, html_content, model="gpt-3.5-turbo"):
        """HTML分割機能をテスト"""
        print(f"\n=== HTML分割テスト（モデル: {model}） ===")
        
        # トークン数をチェック
        tokens = self.count_tokens(html_content, model)
        token_limit = self.model_token_limits.get(model, 16385)
        
        if tokens <= token_limit:
            print(f"分割は不要です（トークン数: {tokens}, 制限: {token_limit}）")
            return {"needs_splitting": False, "parts": 1}
        
        # HTMLをクリーニング
        clean_html = self.clean_html(html_content)
        clean_tokens = self.count_tokens(clean_html, model)
        
        if clean_tokens <= token_limit:
            print(f"クリーニングで十分です（トークン数: {clean_tokens}, 制限: {token_limit}）")
            return {"needs_splitting": False, "parts": 1, "method": "cleaning"}
        
        # 分割が必要な場合は分割を実行
        print("分割を実行します...")
        
        # タグベース分割
        html_parts = self.split_html_by_tags(clean_html, max_tokens=token_limit*0.8, model=model)
        
        # 重要要素の抽出
        important_elements = self.extract_important_elements(clean_html)
        important_elements_json = json.dumps(important_elements, ensure_ascii=False, indent=2)
        important_elements_tokens = self.count_tokens(important_elements_json, model)
        
        print(f"重要要素のJSON表現のトークン数: {important_elements_tokens}")
        print(f"制限に対する割合: {important_elements_tokens/token_limit*100:.1f}%")
        
        return {
            "needs_splitting": True,
            "parts": len(html_parts),
            "tag_based_parts": html_parts,
            "important_elements": important_elements,
            "important_elements_tokens": important_elements_tokens
        }
    
    def test_openai_api_with_split_html(self, html_content, model="gpt-3.5-turbo", test_api_call=False):
        """分割したHTMLをOpenAI APIで処理するテスト"""
        if not OPENAI_API_KEY:
            print("OpenAI APIキーが設定されていないため、API呼び出しテストをスキップします")
            return {"status": "skipped", "reason": "no_api_key"}
        
        print(f"\n=== OpenAI API処理テスト（モデル: {model}） ===")
        
        # HTMLを分割
        splitting_result = self.test_html_splitting(html_content, model)
        
        if not splitting_result.get("needs_splitting", False):
            if "method" in splitting_result and splitting_result["method"] == "cleaning":
                # クリーニングしたHTMLを使用
                test_html = self.clean_html(html_content)
            else:
                # オリジナルのHTMLを使用
                test_html = html_content
            
            # 実際のAPI呼び出しをテスト
            if test_api_call:
                try:
                    print("OpenAI APIを呼び出しています...")
                    
                    response = openai.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "あなたはHTMLページから重要な要素を抽出するアシスタントです。"},
                            {"role": "user", "content": f"以下のHTMLから重要なボタン、リンク、フォーム要素を抽出してください:\n\n{test_html[:1000]}..."}
                        ],
                        max_tokens=100
                    )
                    
                    print("API呼び出しに成功しました")
                    print(f"応答: {response.choices[0].message.content}")
                    
                    return {"status": "success", "method": "single_call", "response": response.choices[0].message.content}
                except Exception as e:
                    print(f"API呼び出し中にエラーが発生: {e}")
                    return {"status": "error", "method": "single_call", "error": str(e)}
            
            return {"status": "simulation_only", "method": "single_call"}
        
        # 分割が必要な場合
        print("分割処理によるAPI呼び出しをシミュレーションします...")
        
        # 重要要素の抽出を使用
        if "important_elements" in splitting_result:
            important_elements = splitting_result["important_elements"]
            important_elements_json = json.dumps(important_elements, ensure_ascii=False)
            
            # 実際のAPI呼び出しをテスト
            if test_api_call:
                try:
                    print("OpenAI APIを呼び出しています（重要要素のみ）...")
                    
                    response = openai.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "あなたはHTMLページから抽出された要素を分析するアシスタントです。"},
                            {"role": "user", "content": f"以下のJSON形式のデータはHTMLから抽出された重要な要素です。これらの要素について分析してください:\n\n{important_elements_json[:1000]}..."}
                        ],
                        max_tokens=100
                    )
                    
                    print("API呼び出しに成功しました")
                    print(f"応答: {response.choices[0].message.content}")
                    
                    return {"status": "success", "method": "important_elements", "response": response.choices[0].message.content}
                except Exception as e:
                    print(f"API呼び出し中にエラーが発生: {e}")
                    return {"status": "error", "method": "important_elements", "error": str(e)}
        
        # タグベースの分割を使用
        if "tag_based_parts" in splitting_result:
            html_parts = splitting_result["tag_based_parts"]
            
            # 複数のAPI呼び出しをシミュレーション
            print(f"{len(html_parts)}回のAPI呼び出しをシミュレーションします...")
            
            # 実際のAPI呼び出しをテスト
            if test_api_call:
                try:
                    # 最初のパートだけをテスト
                    first_part = html_parts[0]
                    
                    print("OpenAI APIを呼び出しています（最初のパートのみ）...")
                    response = openai.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "あなたはHTMLページの一部から要素を抽出するアシスタントです。"},
                            {"role": "user", "content": f"以下のHTMLはページの一部です。この中から重要なボタン、リンク、フォーム要素を抽出してください:\n\n{first_part[:1000]}..."}
                        ],
                        max_tokens=100
                    )
                    
                    print("API呼び出しに成功しました")
                    print(f"応答: {response.choices[0].message.content}")
                    
                    return {
                        "status": "success", 
                        "method": "split_parts", 
                        "part_count": len(html_parts),
                        "response": response.choices[0].message.content
                    }
                except Exception as e:
                    print(f"API呼び出し中にエラーが発生: {e}")
                    return {"status": "error", "method": "split_parts", "error": str(e), "part_count": len(html_parts)}
        
        return {"status": "simulation_only", "method": "split_parts", "part_count": splitting_result.get("parts", 0)}
    
    def test_largest_file(self, test_api_call=False):
        """最大のHTMLファイルをテスト"""
        if not self.html_files:
            print("HTMLファイルが見つかりません")
            return
        
        # ファイルサイズでソート
        files_with_size = [(f, os.path.getsize(f)) for f in self.html_files]
        largest_file = max(files_with_size, key=lambda x: x[1])
        
        print(f"\n=== 最大のHTMLファイルをテスト ===")
        print(f"ファイル: {os.path.basename(largest_file[0])}")
        print(f"サイズ: {largest_file[1]/1024:.1f} KB")
        
        # ファイルを読み込み
        html_content = self.load_html_file(largest_file[0])
        
        if not html_content:
            print("ファイルの読み込みに失敗しました")
            return
        
        # 各種テストを実行
        token_results = self.test_different_models(html_content)
        splitting_results = self.test_html_splitting(html_content)
        api_results = self.test_openai_api_with_split_html(html_content, test_api_call=test_api_call)
        
        return {
            "file": largest_file[0],
            "size": largest_file[1],
            "token_results": token_results,
            "splitting_results": splitting_results,
            "api_results": api_results
        }
    
    def test_all_files(self):
        """すべてのHTMLファイルをテスト"""
        print("\n=== すべてのHTMLファイルをテスト ===")
        
        file_results = {}
        for html_file in self.html_files:
            file_name = os.path.basename(html_file)
            file_size = os.path.getsize(html_file)
            
            print(f"\nファイル: {file_name}")
            print(f"サイズ: {file_size/1024:.1f} KB")
            
            # ファイルを読み込み
            html_content = self.load_html_file(html_file)
            
            if not html_content:
                print("ファイルの読み込みに失敗しました")
                continue
            
            # トークン数をテスト
            token_result = self.test_token_count(html_content)
            
            file_results[file_name] = {
                "size": file_size,
                "token_result": token_result
            }
        
        # トークン数でソート
        sorted_results = sorted(
            file_results.items(), 
            key=lambda x: x[1]["token_result"]["original_tokens"], 
            reverse=True
        )
        
        print("\n=== トークン数の多い順にファイルをリスト ===")
        for file_name, result in sorted_results:
            print(f"{file_name}: {result['token_result']['original_tokens']}トークン ({result['size']/1024:.1f} KB)")
        
        return file_results
    
    def test_html_optimization_strategies(self, html_content):
        """HTML最適化戦略をテスト"""
        print("\n=== HTML最適化戦略テスト ===")
        
        # オリジナルのトークン数
        original_tokens = self.count_tokens(html_content)
        print(f"オリジナルHTMLのトークン数: {original_tokens}")
        
        # 戦略1: 不要なタグを削除
        soup = BeautifulSoup(html_content, 'html.parser')
        for tag in soup.find_all(['script', 'style', 'meta', 'link', 'noscript', 'svg']):
            tag.decompose()
        strategy1_html = str(soup)
        strategy1_tokens = self.count_tokens(strategy1_html)
        print(f"戦略1 - 不要なタグを削除: {strategy1_tokens}トークン (削減率: {(original_tokens-strategy1_tokens)/original_tokens*100:.1f}%)")
        
        # 戦略2: コメントと余分な空白を削除
        strategy2_html = re.sub(r'<!--.*?-->', '', strategy1_html, flags=re.DOTALL)
        strategy2_html = re.sub(r'\s+', ' ', strategy2_html)
        strategy2_tokens = self.count_tokens(strategy2_html)
        print(f"戦略2 - コメントと余分な空白を削除: {strategy2_tokens}トークン (削減率: {(original_tokens-strategy2_tokens)/original_tokens*100:.1f}%)")
        
        # 戦略3: 属性を削減
        soup = BeautifulSoup(strategy2_html, 'html.parser')
        for tag in soup.find_all(True):
            attrs_to_remove = [attr for attr in tag.attrs 
                              if attr.startswith(('data-', 'aria-')) 
                              or attr in ['class', 'style', 'id'] 
                              and not (tag.name == 'input' and attr == 'id')]
            for attr in attrs_to_remove:
                del tag[attr]
        strategy3_html = str(soup)
        strategy3_tokens = self.count_tokens(strategy3_html)
        print(f"戦略3 - 不要な属性を削除: {strategy3_tokens}トークン (削減率: {(original_tokens-strategy3_tokens)/original_tokens*100:.1f}%)")
        
        # 戦略4: 重要な部分のみ抽出
        important_elements = self.extract_important_elements(html_content)
        important_elements_json = json.dumps(important_elements, ensure_ascii=False, indent=2)
        strategy4_tokens = self.count_tokens(important_elements_json)
        print(f"戦略4 - 重要な要素のみ抽出: {strategy4_tokens}トークン (削減率: {(original_tokens-strategy4_tokens)/original_tokens*100:.1f}%)")
        
        return {
            "original": original_tokens,
            "remove_tags": strategy1_tokens,
            "remove_comments": strategy2_tokens,
            "remove_attributes": strategy3_tokens,
            "important_elements": strategy4_tokens
        }
    
    def run_tests(self, test_api_call=False):
        """すべてのテストを実行"""
        print("=== OpenAI APIのトークン制限テスト開始 ===")
        
        # すべてのファイルのトークン数をテスト
        all_files_results = self.test_all_files()
        
        # 最大のファイルで詳細テスト
        largest_file_results = self.test_largest_file(test_api_call)
        
        # 結果を保存
        self.results = {
            "all_files": all_files_results,
            "largest_file": largest_file_results
        }
        
        # 推奨モデルと戦略
        self._recommend_model_and_strategy()
        
        return self.results
    
    def _recommend_model_and_strategy(self):
        """モデルと戦略の推奨"""
        print("\n=== 推奨モデルと戦略 ===")
        
        # すべてのファイルのトークン数を確認
        files_exceeding_limit = []
        
        if "all_files" in self.results:
            for file_name, result in self.results["all_files"].items():
                token_result = result["token_result"]
                if token_result["needs_splitting"]:
                    files_exceeding_limit.append((file_name, token_result["original_tokens"]))
        
        if files_exceeding_limit:
            print(f"{len(files_exceeding_limit)}個のファイルがデフォルトのトークン制限を超えています")
            
            # トークン数順にソート
            files_exceeding_limit.sort(key=lambda x: x[1], reverse=True)
            for file_name, tokens in files_exceeding_limit[:5]:
                print(f"- {file_name}: {tokens}トークン")
            
            if len(files_exceeding_limit) > 5:
                print(f"... 他{len(files_exceeding_limit)-5}個のファイル")
            
            # モデルの推奨
            print("\n推奨モデル:")
            for model, limit in self.model_token_limits.items():
                files_exceeding_model_limit = sum(1 for _, tokens in files_exceeding_limit if tokens > limit)
                if files_exceeding_model_limit == 0:
                    print(f"- {model}: すべてのファイルを処理可能（制限: {limit}トークン）")
                else:
                    print(f"- {model}: {len(files_exceeding_limit)-files_exceeding_model_limit}/{len(files_exceeding_limit)}ファイル処理可能（制限: {limit}トークン）")
            
            # 推奨戦略
            print("\n推奨戦略:")
            print("1. HTMLのクリーニングと最適化")
            print("   - スクリプト、スタイル、コメント、不要な属性の削除")
            print("2. 重要な要素のみの抽出")
            print("   - ボタン、リンク、フォーム要素、日本語テキストなどを抽出")
            print("3. HTMLの分割処理")
            print("   - 複数のAPI呼び出しに分割して処理")
            print("4. 高トークン制限モデルの使用")
            print("   - GPT-4 Turboなどのより高いトークン制限を持つモデルを検討")
        else:
            print("すべてのファイルがデフォルトのトークン制限内で処理可能です")


def main():
    """メイン処理"""
    # コマンドライン引数の解析
    import argparse
    parser = argparse.ArgumentParser(description='OpenAI APIのトークン制限テスト')
    parser.add_argument('--api-test', action='store_true', help='実際にOpenAI APIを呼び出してテストする')
    args = parser.parse_args()
    
    tester = TokenLimitTest()
    tester.run_tests(test_api_call=args.api_test)


if __name__ == "__main__":
    main() 