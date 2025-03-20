from datetime import datetime, timedelta
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import os
import traceback
import socket
import pandas as pd
import shutil
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException
import configparser
from my_logging import setup_department_logger

# ロガーを設定
LOGGER = setup_department_logger('main')
config = configparser.ConfigParser()
config.read('settings.ini', encoding='utf-8')

#ポップアップ対処用関数
def handle_popup(driver, LOGGER):
    try:
        # ポップアップのOKボタンをクリック可能になるまで待機
        ok_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/div[3]/div/div/div[3]/button'))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", ok_button)
        ok_button.click()
        LOGGER.debug("ポップアップ消去完了")
    except TimeoutException:
        LOGGER.error("ポップアップは表示されませんでした")
    except ElementClickInterceptedException as e:
        LOGGER.error(f"ポップアップのOKボタンがクリックできませんでした: {e}")

#要素がポップアップとかで見えない時にJavascriptで強制クリックする
def wait_and_click(driver, by, value, timeout=30):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
        driver.execute_script("arguments[0].click();", element)
        time.sleep(2)
        return True
    except (TimeoutException, ElementClickInterceptedException):
        LOGGER.error(f"要素をクリックできませんでした: {by}={value}")
        return False

#詳細分析ページとかで日付選択をするための関数
def select_and_input_date(driver, start_date_str, end_date_str):
    try:
        # 日付カレンダーを開くトリガーをクリック
        LOGGER.debug(f"日付カレンダーを開くボタンを探しています")
        start_date_picker_trigger = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[1]/div[2]/nav/div[2]/div[1]/div/div[1]/div[2]/input'))
        )
        start_date_picker_trigger.click()  # カレンダーを開く
        LOGGER.debug(f"日付カレンダーをクリックしました: {start_date_picker_trigger.get_attribute('outerHTML')}")
        time.sleep(3)

        # 「いつから」の日付入力フィールドに指定された日付をsend_keysで設定
        LOGGER.debug(f"開始日フィールドを探しています")
        start_date_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[1]/div[2]/nav/div[2]/div[1]/div/div[2]/div[2]/div[2]/div[1]/div[1]/input[1]'))
        )

        # フィールドを完全にクリア
        driver.execute_script("arguments[0].value = '';", start_date_input)
        time.sleep(1)  # 短い待機時間を追加
        start_date_input.send_keys(start_date_str)
        LOGGER.debug(f"開始日フィールドに {start_date_str} を入力しました: {start_date_input.get_attribute('outerHTML')}")
        time.sleep(1)

        # 「いつまで」の日付入力フィールドに指定された日付をsend_keysで設定
        LOGGER.debug(f"終了日フィールドを探しています")
        end_date_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[1]/div[2]/nav/div[2]/div[1]/div/div[2]/div[2]/div[2]/div[1]/div[1]/input[2]'))
        )

        # フィールドを完全にクリア
        driver.execute_script("arguments[0].value = '';", end_date_input)
        time.sleep(1)  # 短い待機時間を追加
        end_date_input.send_keys(end_date_str)
        LOGGER.debug(f"終了日フィールドに {end_date_str} を入力しました: {end_date_input.get_attribute('outerHTML')}")
        time.sleep(1)

        # 日付フィールドの最終確認（値が正しく反映されているか）
        start_date_final = driver.execute_script("return arguments[0].value;", start_date_input)
        end_date_final = driver.execute_script("return arguments[0].value;", end_date_input)
        LOGGER.debug(f"最終確認: 開始日 {start_date_final}, 終了日 {end_date_final}")

        if start_date_final != start_date_str or end_date_final != end_date_str:
            LOGGER.error(f"日付が反映されていません。開始日: {start_date_final}, 終了日: {end_date_final}")
            return False  # 日付が正しく設定されていない場合は停止
        time.sleep(10)

        # 適用ボタンをクリック
        LOGGER.debug("適用ボタンを探しています")
        apply_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[1]/div[2]/nav/div[2]/div[1]/div/div[2]/div[2]/div[2]/div[2]/button[2]'))
        )
        LOGGER.debug(f"適用ボタンを見つけました: {apply_button.get_attribute('outerHTML')}")

        apply_button.click()
        LOGGER.debug(f"適用ボタンをクリックしました: {apply_button.get_attribute('outerHTML')}")

    except TimeoutException:
        LOGGER.error("日付選択画面を表示できませんでした")
    except NoSuchElementException as e:
        LOGGER.error(f"日付入力フィールドが見つかりませんでした: {e}")

#ブラウザのセットアップ
def setup_browser(config):
    options = webdriver.ChromeOptions()
    username = os.getenv('USERNAME')
    download_path = f"C:\\Users\\{username}\\Downloads"
    
    if not os.path.exists(download_path):
        download_path = config['Paths']['downloads']
    
    options.add_experimental_option('prefs', {
        'download.prompt_for_download': False,
        'download.directory_upgrade': True,
        'safebrowsing.enabled': True,
        'download.default_directory': download_path
    })
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    driver.command_executor._commands["send_command"] = ("POST", '/session/$sessionId/chromium/send_command')
    driver.execute("send_command", params={
        'cmd': 'Page.setDownloadBehavior',
        'params': {'behavior': 'allow', 'downloadPath': download_path}
    })
    driver.maximize_window()
    # アドエビスログイン画面へのアクセス
    adebis_login = config.get('Credentials', 'login_url')
    driver.get(adebis_login)
    LOGGER.debug("アドエビスのログイン画面にアクセスしました")
    return driver

# ログイン処理
def login_to_adebis(driver, config):
    try:
        account_key = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.NAME, 'account_key'))
        )
        account_key.send_keys(config['Credentials']['account_key'])

        username = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.NAME, 'username'))
        )
        username.send_keys(config['Credentials']['username'])

        password = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.NAME, 'password'))
        )
        password.send_keys(config['Credentials']['password'])

        login_btn = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.NAME, 'login'))
        )
        login_btn.click()
        LOGGER.info("ログインしました")
        time.sleep(5)

        return True  # ログイン成功を返す
    except Exception as e:
        LOGGER.error(f"ログイン処理中にエラーが発生しました: {e}")
        return False  # ログイン失敗を返す

# SS_CVデータ取得
def download_ss_cv_data(driver, start_date_str, end_date_str):
    adebis_details = config.get('Credentials', 'url_details')
    driver.get(adebis_details)    
    LOGGER.info("詳細分析に入りました")

    time.sleep(5)  # ページ読み込み待機
    handle_popup(driver, LOGGER)

    # 日付選択と入力
    select_and_input_date(driver, start_date_str, end_date_str)
    time.sleep(10)  # ページ読み込み待機

    # インポートを押す
    if not wait_and_click(driver, By.XPATH, '//*[@id="common-bar"]/div[2]/nav/div[2]/div[4]/div[1]'):
        print("インポートボタンをクリックできませんでした")

    # ダウンロードを押す
    if not wait_and_click(driver, By.XPATH, '//*[@id="common-bar"]/div[2]/nav/div[2]/div[4]/div[2]/a'):
        print("ダウンロードボタンをクリックできませんでした")

    time.sleep(30)

    print("SSとCVのデータダウンロードが完了しました。")

# CV属性ファイル取得
def download_cv_attribute_report(driver, start_date_str, end_date_str):
    driver.get(config.get('Credentials', 'url_cvrepo'))
    LOGGER.debug("CV属性レポートページに入りました")

    time.sleep(5)  # ページ読み込み待機
    handle_popup(driver, LOGGER)

    # 日付選択と入力
    select_and_input_date(driver, start_date_str, end_date_str)
    
    # 全トラフィックタブを選択
    tab = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH,'//*[@id="navbar"]/nav/a[2]'))).click()

    # 属性レポート_CSVダウンロード
    if not wait_and_click(driver, By.XPATH, '//*[@id="common-bar"]/div[2]/nav/div[2]/div[4]/div[1]'):
        print("CSVボタンをクリックできませんでした")

    if not wait_and_click(driver, By.XPATH, '//*[@id="common-bar"]/div[2]/nav/div[2]/div[4]/div[2]/a'):
        print("CSVダウンロードボタンをクリックできませんでした")

    time.sleep(90)
    print('CV属性ファイルダウンロード完了')

# データを取得する日付の指定
def process_downloaded_data(config):
    # 日数の設定を取得
    days_ago = int(config['DownloadSettings']['days_ago'])

    # 日付データ作成
    today = datetime.today()
    target_date = today - timedelta(days=days_ago)

    passdate_past = str(datetime.strftime(target_date, '%Y/%m/%d'))
    passdate_past2 = str(datetime.strftime(target_date, '%Y%m%d'))

    # デバイスのユーザー名を取得
    username = os.getenv('USERNAME')
    download_path = f"C:\\Users\\{username}\\Downloads"
    
    if not os.path.exists(download_path):
        LOGGER.error(f"警告: 生成されたダウンロードパスが存在しません: {download_path}")
        LOGGER.debug("設定ファイルのパスを使用します。")
        download_path = config['Paths']['downloads']
    
    LOGGER.debug(f"使用するダウンロードパス: {download_path}")

    # ファイルパス指定
    moveto = config['Paths']['moveto']
    conecter = '\\'

    try:
        # SSとCVのデータを処理
        new_path = moveto + conecter + passdate_past2 + "_ebis_SS_CV.csv"
        dl_files = os.listdir(download_path)
        dl_files_file = [f for f in dl_files if os.path.isfile(os.path.join(download_path, f))]
        SS_CV_csv = [s for s in dl_files_file if 'detail_analyze' in s]
        
        if not SS_CV_csv:
            LOGGER.error(f"SSとCVのデータファイルが見つかりません。ディレクトリ内のファイル: {dl_files}")
            return None, None, None

        SS_CV_csv_path = os.path.join(download_path, SS_CV_csv[-1])
        shutil.move(SS_CV_csv_path, new_path)
        LOGGER.info("DLしたデータを所定のフォルダに移動させました")

        SSCV_df = pd.read_csv(new_path, encoding='cp932', usecols=['広告名','クリック数','応募完了（CV）'])
        SSCV_df['日付'] = passdate_past

        # SSとCVのファイルを作成
        SS_df = SSCV_df.drop('応募完了（CV）', axis=1).reindex(columns=['日付','広告名','クリック数'])
        CV_df = SSCV_df.drop('クリック数', axis=1).reindex(columns=['日付','広告名','応募完了（CV）'])

        SS_path = moveto + conecter + passdate_past2 + "_SS.csv"
        CV_path = moveto + conecter + passdate_past2 + "_CV.csv"

        SS_df.to_csv(SS_path, encoding='cp932', float_format='%.0f', index=False)
        CV_df.to_csv(CV_path, encoding='cp932', float_format='%.0f', index=False)

        LOGGER.info("SSとCVのデータを作成しました。")

        # CV属性レポートを処理
        CVrepo_csv = [s for s in dl_files_file if 'cv_attr' in s]
        if not CVrepo_csv:
            LOGGER.error("CV属性レポートファイルが見つかりません")
            return SS_df, CV_df, None

        CVrepo_path = os.path.join(download_path, CVrepo_csv[-1])
        new_path2 = moveto + conecter + passdate_past2 + "_ebis_CVrepo.csv"
        shutil.move(CVrepo_path, new_path2)
        LOGGER.debug('CV属性ファイル移動完了')

        CVrepo_df = pd.read_csv(new_path2, encoding='cp932')
        CVrepo_df = CVrepo_df.fillna('')
        CVrepo_df = CVrepo_df.astype('object')

        return SS_df, CV_df, CVrepo_df

    except Exception as e:
        LOGGER.error(f"エラー: ファイルの処理中に問題が発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None, None

#ログイン→データDL→DLしたファイルの処理をまとめて実施
def perform_adebis_operations(config):
    driver = setup_browser(config)
    
    # 日付設定を取得
    days_ago = int(config['DownloadSettings']['days_ago'])
    today = datetime.today()
    target_date = today - timedelta(days=days_ago)
    passdate_past = target_date.strftime('%Y/%m/%d')

    try:
        if login_to_adebis(driver, config):
            time.sleep(5)  # ログイン後少し待機
            download_ss_cv_data(driver, passdate_past, passdate_past)
            download_cv_attribute_report(driver, passdate_past, passdate_past)
            SS_df, CV_df, CVrepo_df = process_downloaded_data(config)
            return SS_df, CV_df, CVrepo_df
        else:
            LOGGER.error("ログインに失敗しました")
            return None, None, None
    finally:
        driver.quit()