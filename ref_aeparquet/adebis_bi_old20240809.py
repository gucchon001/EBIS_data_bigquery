from datetime import datetime,timedelta
import time
from selenium import webdriver
import chromedriver_binary #環境変数通さなくてもできるように
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from datetime import datetime, date, timedelta
from gspread_dataframe import get_as_dataframe, set_with_dataframe
import os
import glob
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
import shutil

# ブラウザを開く ダウンロード先のフォルダ指定
options = webdriver.ChromeOptions()
#options.add_argument('--headless')
options.add_experimental_option('prefs', {
'download.prompt_for_download': False,
'download.directory_upgrade': True,
'safebrowsing.enabled': True
})
driver = webdriver.Chrome(chrome_options=options)

driver.command_executor._commands["send_command"] = (
  'POST',
  '/session/$sessionId/chromium/send_command'
)
driver.execute(
  "send_command",
  params={
    'cmd': 'Page.setDownloadBehavior',
    'params': { 'behavior': 'allow', 'downloadPath': r'C:\Users\tmnk013\Downloads' }
  }
)

"""---------ログイン---------"""
# アドエビスログイン画面を開く。
driver.get("https://id.ebis.ne.jp/")

#指定した要素が表示されるまで、明示的に30秒待機する
account_key = WebDriverWait(driver, 30).until(
	EC.visibility_of_element_located((By.NAME, 'account_key'))
)
account_key.send_keys('tomonokai01')

username = driver.find_element_by_name("username")
username.send_keys("tomonokai01")

password = driver.find_element_by_name("password")
password.send_keys("$8DfW_hv47jq")

login_btn = driver.find_element_by_name("login")
login_btn.submit()

print("ログインしました")
time.sleep(5)

"""---------詳細分析に入ってSSとCVが一緒になったデータを落とす---------"""

# 新管理画面対応
#詳細分析ページに入る（ポップアップが出てくるので直で飛ばす
driver.get("https://bishamon.ebis.ne.jp/details-analysis")

print("詳細分析に入りました")

#集計期間指定をクリック
date_set = WebDriverWait(driver, 30).until(
	EC.visibility_of_element_located((By.XPATH, '//*[@id="common-bar"]/div[2]/nav/div[2]/div[1]/div/div[1]/div[2]/input'))
)
date_set.click()

#昨日を選ぶ
yesterday_btn = WebDriverWait(driver, 30).until(
	EC.visibility_of_element_located((By.XPATH, '//*[@id="common-bar"]/div[2]/nav/div[2]/div[1]/div/div[2]/div[1]/div[2]'))
)
yesterday_btn.click()

#適用を押す
set_btn = WebDriverWait(driver, 30).until(
	EC.visibility_of_element_located((By.XPATH, '//*[@id="common-bar"]/div[2]/nav/div[2]/div[1]/div/div[2]/div[2]/div[2]/div[2]/button[2]'))
)
set_btn.click()

time.sleep(5)

#インポートを押す
ex = WebDriverWait(driver, 30).until(
	EC.visibility_of_element_located((By.XPATH, '//*[@id="common-bar"]/div[2]/nav/div[2]/div[4]'))
)
ex.click()

#ダウンロードを押す
ex_btn = WebDriverWait(driver, 30).until(
	EC.visibility_of_element_located((By.XPATH, '//*[@id="common-bar"]/div[2]/nav/div[2]/div[4]/div[2]/a'))
)
ex_btn.click()

time.sleep(30)

print("SSとCVのデータダウンロードが完了しました。")


"""---------SSとCVが一緒になったデータを加工して張り付ける---------"""

#日付データ作成
today = datetime.today()
yesterday = today - timedelta(days=1)

passdate = datetime.strftime(today, '%Y%m%d')
passdate2 = datetime.strftime(today, '%Y/%m/%d')
yesterday = today - timedelta(days=1)
passdate_past = str(datetime.strftime(yesterday, '%Y/%m/%d'))
passdate_past2 = str(datetime.strftime(yesterday, '%Y%m%d'))

#ファイルパス指定
path = r"C:\Users\tmnk015\Downloads"
moveto = r"\\nas\public\事務業務資料\300_講師求人部門\81講師求人DB\BPR用\元データ\06.アドエビス\加工前"
conecter = '\\'
new_path = moveto + conecter + passdate_past2 + "_ebis_SS_CV.csv"

dl_files = os.listdir(path)
dl_files_file = [f for f in dl_files if os.path.isfile(os.path.join(path, f))]

SS_CV_csv = [s for s in dl_files_file if 'detail_analyze' in s]
#SS_CV_csv = [k for k in SS_CV_csv if passdate in k]

SS_CV_csv_path = path + conecter + SS_CV_csv[len(SS_CV_csv)-1]

new_move = shutil.move(SS_CV_csv_path, new_path)

print("DLしたデータを所定のフォルダに移動させました")

"""---------SSとCVのDLデータを加工して切り分ける---------"""

SSCV_df = pd.read_csv(new_path,encoding='cp932',
                       usecols=['広告名','クリック数','応募完了（CV）'])

set_folder = r"\\nas\public\事務業務資料\300_講師求人部門\81講師求人DB\BPR用\元データ\06.アドエビス\加工後"

set_file_name = passdate_past2 + "_SSCV.csv"
set_path = set_folder + conecter + set_file_name
SSCV_df['日付'] = passdate_past
SSCV_df.to_csv(set_path, encoding='cp932',float_format='%.0f',index=False)

#SSとCVのファイルを作成
SS_df = SSCV_df.drop('応募完了（CV）',axis=1).reindex(columns=['日付','広告名','クリック数'])
#SS_df['クリック数'] = SS_df['クリック数'].astype('int')
SS_path = set_folder + conecter +passdate_past2 + "_SS.csv"

CV_df = SSCV_df.drop('クリック数',axis=1).reindex(columns=['日付','広告名','応募完了（CV）'])
#CV_df['応募完了（CV）'] = CV_df['応募完了（CV）'].astype('int')
CV_path = set_folder + conecter +passdate_past2 + "_CV.csv"

SS_df.to_csv(SS_path, encoding='cp932',float_format='%.0f',index=False)
CV_df.to_csv(CV_path, encoding='cp932',float_format='%.0f',index=False)

print("SSとCVのデータを作成しました。")

"""CV属性レポートをDL"""
# 新管理画面対応
# アドエビスコンバージョン属性を開く。
driver.get("https://bishamon.ebis.ne.jp/cv-attribute")

# 全トラフィックタブを選択
tab = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH,'//*[@id="navbar"]/nav/a[2]'))).click()

# 期間選択
daterange_btn = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH,'//*[@id="common-bar"]/div[2]/nav/div[2]/div[1]/div/div[1]/div[2]/input'))).click()
yesterday_btn = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH,'//*[@id="common-bar"]/div[2]/nav/div[2]/div[1]/div/div[2]/div[1]/div[2]'))).click()
cnf = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH,'//*[@id="common-bar"]/div[2]/nav/div[2]/div[1]/div/div[2]/div[2]/div[2]/div[2]/button[2]'))).click()

# 属性レポート_CSVダウンロード
csv_btn = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH,'//*[@id="common-bar"]/div[2]/nav/div[2]/div[4]/div[1]'))).click()
csv_btn2 = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH,'//*[@id="common-bar"]/div[2]/nav/div[2]/div[4]/div[2]/a'))).click()

time.sleep(90)
print('CV属性ファイルダウンロード完了')

# 最新のファイルを取得
dl_files = os.listdir(path)
dl_files_file = [f for f in dl_files if os.path.isfile(os.path.join(path, f))]

CVrepo_csv = [s for s in dl_files_file if 'cv_attr' in s]
#SS_CV_csv = [k for k in SS_CV_csv if passdate in k]

CVrepo_path = path + conecter + CVrepo_csv[len(CVrepo_csv)-1]

new_path2 = set_folder + conecter + passdate_past2 + "_ebis_CVrepo.csv"
new_move = shutil.move(CVrepo_path, new_path2)

print('CV属性ファイル移動完了')

CVrepo_df = pd.read_csv(new_path2,encoding='cp932')
CVrepo_df = CVrepo_df.fillna('')
CVrepo_df = CVrepo_df.astype('object')


# ブラウザを終了する。
driver.close()

"""------------------------ここから修正必要----------------------"""


"""ここからスプレッドシートを操作しシートに張り付ける"""
#2つのAPIを記述しないとリフレッシュトークンを3600秒毎に発行し続けなければならない
scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']

#認証情報設定
#ダウンロードしたjsonファイル名をクレデンシャル変数に設定（秘密鍵、Pythonファイルから読み込みしやすい位置に置く）
json_file = r"\\nas\public\事務業務資料\100000管理部門\101000システム\事業部プログラム\講師求人部門\adebis_program\dataapp-282609-b2b0ec9574b8.json"
credentials = ServiceAccountCredentials.from_json_keyfile_name(json_file, scope)

#OAuth2の資格情報を使用してGoogle APIにログインします。
gc = gspread.authorize(credentials)

workbook = gc.open_by_key('1VATPpMmstdKpXa4PGht0weKQWufD2G62DpijtkFje1k')
worksheet = workbook.worksheet('AE_SSresult')

#既存データの数を取得
col_list = worksheet.col_values(1)
data_count = len(col_list)

#列数はいったん固定
column_count = 3

#セット範囲を作成する
base_data_length = len(SS_df)
data_range = 'A' + str((data_count+1)) + ':C' + str((data_count+base_data_length))

#後は既存のデータ数と、格納データ数を使って、A1:B10形式でデータのセット範囲を取得、
#その範囲にデータを指定（先頭列を削除）、で完了

cell_list = worksheet.range(data_range)

#int型があると貼り付けできないので変更
SS_df['クリック数'] = SS_df['クリック数'].astype(str)


for cell in cell_list:
    #print(cell.row, cell.col)
    val = SS_df.iloc[cell.row - (data_count+1)][cell.col - 1]
    cell.value = val

worksheet.update_cells(cell_list,value_input_option='USER_ENTERED')
print("SSデータの貼り付けが完了しました。")


"""CVデータの貼り付け"""
workbook2 = gc.open_by_key('1xM3DoXxfmZE5nRC-Qc50b9QOXeg_UGbZAPJxubWvaPY')
worksheet2 = workbook2.worksheet('AE_CVresult')

#既存データの数を取得
col_list2 = worksheet2.col_values(1)
data_count2 = len(col_list2)

#列数はいったん固定
column_count2 = 3

#セット範囲を作成する
base_data_length2 = len(CV_df)
data_range2 = 'A' + str((data_count2+1)) + ':C' + str((data_count2+base_data_length2))

#後は既存のデータ数と、格納データ数を使って、A1:B10形式でデータのセット範囲を取得、
#その範囲にデータを指定（先頭列を削除）、で完了

cell_list2 = worksheet2.range(data_range2)

#int型があると貼り付けできないので変更
CV_df['応募完了（CV）'] = CV_df['応募完了（CV）'].astype(str)


for cell in cell_list2:
    #print(cell.row, cell.col)
    val = CV_df.iloc[cell.row - (data_count2+1)][cell.col - 1]
    cell.value = val

worksheet2.update_cells(cell_list2,value_input_option='USER_ENTERED')
print("CVデータの貼り付けが完了しました。")


"""CVrepoを張り付けて終わり"""
workbook3 = gc.open_by_key('1POubs2rL3ujimhLeo7vGES6Cui0OIAxA05oBsipISeg')
worksheet3 = workbook3.worksheet('AE_CV属性result')

#既存データの数を取得
col_list3 = worksheet3.col_values(1)
data_count3 = len(col_list3)

#列数はいったん固定
column_count3 = 91

#セット範囲を作成する
base_data_length3 = len(CVrepo_df)
data_range3 = 'A' + str((data_count3+1)) + ':CM' + str((data_count3+base_data_length3))

#後は既存のデータ数と、格納データ数を使って、A1:B10形式でデータのセット範囲を取得、
#その範囲にデータを指定（先頭列を削除）、で完了

cell_list3 = worksheet3.range(data_range3)


for cell in cell_list3:
    #print(cell.row, cell.col)
    val = CVrepo_df.iloc[cell.row - (data_count3+1)][cell.col - 1]
    cell.value = val

worksheet3.update_cells(cell_list3,value_input_option='USER_ENTERED')
print("CV属性データの貼り付けが完了しました。")



