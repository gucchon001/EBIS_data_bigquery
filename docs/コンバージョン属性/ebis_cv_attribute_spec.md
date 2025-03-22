# AdEBiS CV属性レポートCSVダウンロード機能仕様書

## 1. 概要

### 1.1 目的
本機能は、AdEBiS管理画面のCV属性レポートページからCSVデータを自動的にダウンロードすることを目的とする。
特定の日付範囲のデータを任意のディレクトリにCSVファイルとして保存する。

### 1.2 背景
AdEBiS管理画面からのデータ取得は手作業で行われていたが、定期的なデータ取得作業を自動化し、業務効率化を図るために本機能を開発する。

### 1.3 成果物
- CV属性レポートCSVダウンロードPythonモジュール
- コマンドラインインターフェイス
- 関連ドキュメント

## 2. 機能要件

### 2.1 基本機能一覧

| ID | 機能名 | 説明 | 重要度 |
|-----|------|------|--------|
| FR-01 | ログイン処理 | AdEBiS管理画面へログインする | 必須 |
| FR-02 | CV属性レポートページ遷移 | CV属性レポートページに移動する | 必須 |
| FR-03 | 日付範囲指定 | ダウンロードするデータの日付範囲を指定する | 必須 |
| FR-04 | 全トラフィックタブ選択 | 全トラフィックタブを選択する | 必須 |
| FR-05 | CSVダウンロード | データをCSV形式でダウンロードする | 必須 |
| FR-06 | ファイル名変更 | ダウンロードしたファイルの名前を指定の形式に変更する | 必須 |
| FR-07 | エラーハンドリング | 処理中のエラーを適切に処理する | 必須 |
| FR-08 | ヘッドレスモード | ブラウザを表示せずに処理を実行する | オプション |
| FR-09 | ログ出力 | 処理内容をログファイルに出力する | 必須 |

### 2.2 入力パラメータ

| パラメータ名 | 説明 | デフォルト値 | 形式 |
|------------|------|------------|------|
| date | 取得する日付 | 前日 | YYYY-MM-DD |
| start_date | 範囲指定時の開始日 | - | YYYY-MM-DD |
| end_date | 範囲指定時の終了日 | - | YYYY-MM-DD |
| account | AdEBiSアカウント番号 | settings.iniの値 | 数値 |
| output_dir | 出力ディレクトリ | settings.iniの値 | パス文字列 |
| headless | ヘッドレスモードで実行するかどうか | False | 真偽値 |

### 2.3 出力形式

| 出力形式 | 説明 | 出力先 |
|---------|------|-------|
| CSVファイル | CV属性レポートデータ（YYYYMMDD_ebis_CVrepo.csv） | 指定ディレクトリ |
| ログファイル | 処理内容のログ | logs/ebis_cv_attribute.log |

## 3. 処理フロー

### 3.1 メインフロー

```
開始
  ↓
環境設定読込
  ↓
コマンドライン引数解析
  ↓
日付範囲の準備
  ↓
ログインページを開く
  ↓
ログイン処理実行
  ↓
CV属性レポートページに移動
  ↓
ポップアップ処理（存在する場合）
  ↓
日付範囲選択
  ↓
全トラフィックタブ選択
  ↓
CSVダウンロードボタンクリック
  ↓
ダウンロード完了待機
  ↓
ファイル名変更・移動
  ↓
ブラウザ終了
  ↓
終了
```

### 3.2 エラーハンドリングフロー

```
エラー発生
  ↓
エラーログ出力
  ↓
スクリーンショット保存（可能な場合）
  ↓
ブラウザ終了（可能な場合）
  ↓
エラーコード返却
```

## 4. 技術仕様

### 4.1 アーキテクチャ

- ランタイム: Python 3.8以上
- 依存ライブラリ:
  - Selenium
  - ChromeDriver
  - その他プロジェクト共通ライブラリ

### 4.2 クラス設計

#### 4.2.1 CVAttributePage クラス

CV属性ページのPOMパターンに基づいた操作クラス。

```python
class CVAttributePage:
    def __init__(self, browser=None)
    def navigate_to_cv_attribute()
    def handle_popup()
    def select_date_range(start_date, end_date)
    def select_all_traffic_tab()
    def download_csv()
    def wait_for_download_and_process(target_date, output_dir=None)
    def execute_download_flow(start_date, end_date=None, output_dir=None)
    def quit()
```

#### 4.2.2 メインスクリプト関数

```python
def parse_arguments()
def prepare_dates(args)
def run_cv_attribute_download(start_date, end_date, output_dir=None)
def main()
```

### 4.3 設定ファイル（settings.ini）

```ini
[AdEBIS]
url_cvrepo = https://bishamon.ebis.ne.jp/cv-attributes

[Login]
url = https://bishamon.ebis.ne.jp/login
account = [アカウント番号]
password = [パスワード]
```

### 4.4 セレクタ定義（selectors.csv）

```csv
section,name,type,value,description
cv_attribute,date_picker_trigger,css,button.date-range-picker-button,日付範囲選択ボタン
cv_attribute,start_date_input,css,input.calendar__input--start,開始日入力欄
cv_attribute,end_date_input,css,input.calendar__input--end,終了日入力欄
cv_attribute,apply_button,css,button.calendar__apply-button,日付適用ボタン
cv_attribute,all_traffic_tab,css,li.tab-nav__item:nth-child(1),全トラフィックタブ
cv_attribute,csv_button,css,button.button--csv,CSVボタン
cv_attribute,download_button,css,a.download-menu__item,ダウンロードボタン
```

## 5. エラーコード

| コード | 説明 | 対処方法 |
|-------|------|---------|
| E001 | ブラウザセットアップエラー | ChromeDriverのバージョンを確認 |
| E002 | ログインエラー | アカウント情報を確認 |
| E003 | ページ遷移エラー | URLやネットワーク接続を確認 |
| E004 | 日付選択エラー | 日付形式や範囲を確認 |
| E005 | ダウンロードエラー | 権限やディスク容量を確認 |
| E006 | ファイル処理エラー | ファイルパスやアクセス権を確認 |

## 6. ログ仕様

### 6.1 ログレベル

- DEBUG: 詳細なデバッグ情報
- INFO: 通常の処理状況
- WARNING: 警告（処理は継続）
- ERROR: エラー（処理は中断）
- CRITICAL: 致命的なエラー

### 6.2 ログフォーマット

`[日時] [レベル] [ファイル:行] メッセージ`

例: `[2023-06-01 12:34:56] [INFO] [cv_attribute_page.py:123] CV属性レポートページに移動しました`

## 7. テスト仕様

### 7.1 単体テスト

CVAttributePageクラスの各メソッドに対するテスト。

### 7.2 統合テスト

コマンドラインからの全体フロー実行テスト。

### 7.3 テストケース

| ID | テスト内容 | 期待結果 |
|----|----------|---------|
| TC-01 | 正常系: 前日データダウンロード | CSVファイルが正常に保存される |
| TC-02 | 正常系: 日付範囲指定 | 指定範囲のデータがCSVで保存される |
| TC-03 | 異常系: 不正な日付 | エラーメッセージが表示される |
| TC-04 | 異常系: ネットワークエラー | エラーログが出力され、処理が中断される |

## 8. 制約・前提条件

- AdEBiSのUI変更があった場合、セレクタの更新が必要
- ChromeDriverとGoogle Chromeのバージョンの互換性に注意
- ダウンロード完了の検出はタイムアウト方式を採用

## 9. 将来的な拡張性

- APIが提供された場合の対応
- 複数アカウント対応
- データフォーマットの拡張（CSV以外）
- 自動スケジューリング連携機能 