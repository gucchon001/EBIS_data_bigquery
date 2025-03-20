#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep 23 10:04:48 2020



@author: suzuki
"""

import time
from selenium import webdriver
import chromedriver_binary #環境変数通さなくてもできるように
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from datetime import datetime, date, timedelta
from gspread_dataframe import get_as_dataframe, set_with_dataframe
import os
import glob
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials 
# ブラウザを開く ダウンロード先のフォルダ指定
options = webdriver.ChromeOptions()
options.add_argument('--headless')
#options.add_argument('--start-maximized')
options.add_experimental_option('prefs', {
#'download.default_directory': r'\\nas\public\事務業務資料\300_講師求人部門\81講師求人DB\BPR用\元データ\06.アドエビス',
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
    'params': { 'behavior': 'allow', 'downloadPath': r'C:\Users\tmnk015\Desktop\adebis加工用' }
  }
)
# アドエビスログイン画面を開く。
driver.get("https://id.ebis.ne.jp/")
# 3秒待機
time.sleep(3)
# ログイン処理
account_key = driver.find_element_by_name("account_key")
account_key.send_keys("tomonokai01")
username = driver.find_element_by_name("username")
username.send_keys("tomonokai01")
password = driver.find_element_by_name("password")
password.send_keys("$8DfW_hv47jq")
login_btn = driver.find_element_by_name("login")
login_btn.submit()
#3秒待機
time.sleep(3)

# アドエビスクロス集計を開く。
driver.get("https://hotei.ebis.ne.jp/ad/cross/")
#集計期間をクリック
daterange_btn = driver.find_element_by_id("daterange_btn")
daterange_btn.submit()
# 1秒待機
time.sleep(1)
# 昨日をクリック
yesterday_btn = driver.find_element_by_xpath('//*[@id="form1"]/div[2]/div[1]/ul/li[2]')
yesterday_btn.submit()
time.sleep(1)
#適用をクリック
apply_btn = driver.find_element_by_xpath('//*[@id="form1"]/div[2]/div[5]/button')
apply_btn.submit()
time.sleep(1)
# 縦軸の選択
index1 = driver.find_element_by_name("index1")
index1_select = Select(index1)
index1_select.select_by_value("1-4")
# 横軸の選択
index2 = driver.find_element_by_name("index2")
index2_select = Select(index2)
index2_select.select_by_value("2-1")
# 集計値の選択
count = driver.find_element_by_name("count")
count_select = Select(count)
count_select.select_by_value("1")
print('条件選択完了')
time.sleep(3)
# SS_CSVダウンロード
submit_btn = driver.find_element_by_xpath('//*[@id="form1"]/table[2]/tbody/tr/td/table/tbody/tr/td[2]/table/tbody/tr[3]/td/table[1]/tbody/tr/td/table/tbody/tr[6]/td/input')
submit_btn.click()
#6秒待機
time.sleep(10)
print('SSCSVダウンロード完了')

# 最新のファイルを取得
A = glob.glob(r'C:\Users\tmnk015\Desktop\adebis加工用\*') # 対象ディレクトリを指定
#print(A)
nf = max(A, key = os.path.getctime) # 対象ディレクトリ内の最新の更新ファイルを取得
#print(nf)
# ファイル名とパスを変更
today = datetime.today()
yesterday = today - timedelta(days=1)
yd = datetime.strftime(yesterday, '%Y%m%d')
path1 = nf
path2 = (r'C:\Users\tmnk015\Desktop\adebis加工用\加工後' + '\\'+yd+'_adebis_ss.csv')
os.rename(path1,path2)
print('SSファイル移動完了')


# CSV二つ目集計値の選択
count = driver.find_element_by_name("count")
count_select = Select(count)
count_select.select_by_value("2")
# CV_CSVダウンロード
submit_btn = driver.find_element_by_xpath('//*[@id="form1"]/table[2]/tbody/tr/td/table/tbody/tr/td[2]/table/tbody/tr[3]/td/table[1]/tbody/tr/td/table/tbody/tr[6]/td/input').submit()
#6秒待機
time.sleep(10)
print('CVCSVダウンロード完了')

# 最新のファイルを取得
B = glob.glob(r'C:\Users\tmnk015\Desktop\adebis加工用\*') # 対象ディレクトリを指定
nf2 = max(B, key = os.path.getctime) # 対象ディレクトリ内の最新の更新ファイルを取得
#print(nf2)
# ファイル名とパスを変更
today2 = datetime.today()
yesterday2 = today2 - timedelta(days=1)
yd2 = datetime.strftime(yesterday2, '%Y%m%d')
path3 = nf2
path4 = (r'C:\Users\tmnk015\Desktop\adebis加工用\加工後' + '\\'+yd2+'_adebis_cv.csv')
os.rename(path3,path4)
print('CVファイル移動完了')


"""
#CV属性_旧管理画面
driver.get("https://hotei.ebis.ne.jp/traffic/attribute/")
#10秒待機
time.sleep(10)
# 条件選択
label = driver.find_element_by_xpath('//*[@id="traffic_search_button"]/div[1]/div/div/div[2]/label[2]').submit()
label2 = driver.find_element_by_xpath('//*[@id="search_name_166"]').submit()
# 適用クリック
cnf = driver.find_element_by_xpath('//*[@id="js-search-by-id"]').submit()
#10秒待機
time.sleep(10)
# 属性レポート_CSVダウンロード
csv_btn = driver.find_element_by_xpath('//*[@id="csv_btn"]/img').click()
#10秒待機
time.sleep(10)
print('CV属性ファイルダウンロード完了')
"""

# 新管理画面対応
# アドエビスコンバージョン属性を開く。
driver.get("https://bishamon.ebis.ne.jp/cv-attribute")
#10秒待機
time.sleep(10)
# 全トラフィックタブを選択
tab = driver.find_element_by_xpath('//*[@id="navbar"]/nav/a[2]').click()
#10秒待機
time.sleep(5)
# 期間選択
daterange_btn = driver.find_element_by_xpath('//*[@id="common-bar"]/div[2]/nav/div[2]/div[1]/div/div[1]/div[2]/input').click()
yesterday_btn = driver.find_element_by_xpath('//*[@id="common-bar"]/div[2]/nav/div[2]/div[1]/div/div[2]/div[1]/div[2]').click()
cnf = driver.find_element_by_xpath('//*[@id="common-bar"]/div[2]/nav/div[2]/div[1]/div/div[2]/div[2]/div[2]/div[2]/button[2]').click()
#5秒待機
time.sleep(10)
# 属性レポート_CSVダウンロード
csv_btn = driver.find_element_by_xpath('//*[@id="common-bar"]/div[2]/nav/div[2]/div[4]/div[1]').click()
csv_btn2 = driver.find_element_by_xpath('//*[@id="common-bar"]/div[2]/nav/div[2]/div[4]/div[2]/a').click()
#60秒待機
time.sleep(60)
print('CV属性ファイルダウンロード完了')

# 最新のファイルを取得
C = glob.glob(r'C:\Users\tmnk015\Desktop\adebis加工用\*') # 対象ディレクトリを指定
nf3 = max(C, key = os.path.getctime) # 対象ディレクトリ内の最新の更新ファイルを取得
print(nf3)
# ファイル名とパスを変更
today3 = datetime.today()
yesterday3 = today3 - timedelta(days=1)
yd3 = datetime.strftime(yesterday3, '%Y%m%d')
path5 = nf3
path6 = (r'C:\Users\tmnk015\Desktop\adebis加工用\加工後' + '\\'+yd3+'_adebis_attribute.csv')
os.rename(path5,path6)
print('属性ファイル移動完了')

# ブラウザを終了する。
driver.close()


# --------------------SSデータ加工してスプレッドシートへ反映------------------------

#2つのAPIを記述しないとリフレッシュトークンを3600秒毎に発行し続けなければならない
scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
#認証情報設定
#ダウンロードしたjsonファイル名をクレデンシャル変数に設定（秘密鍵、Pythonファイルから読み込みしやすい位置に置く）
credentials = ServiceAccountCredentials.from_json_keyfile_name(r'\\nas\public\事務業務資料\100000管理部門\101000システム\事業部プログラム\講師求人部門\adebis_program\prime-freedom-288406-4ef65d06d8d0.json', scope)
#OAuth2の資格情報を使用してGoogle APIにログインします。
gc = gspread.authorize(credentials)
#共有設定したスプレッドシートキーを変数[SPREADSHEET_KEY]に格納する。
SPREADSHEET_KEY = '1n8TVv2aKV3jz-pd6aB3LPwe-NCvh22PEnyj6W5MNGfc' # 本番用
# SPREADSHEET_KEY = '1qhKrAUp-hwY1FnjTi003rT_UFY1ilHRaVJF0-2b8hzQ' テスト用

# スプレッドシート を開く
workbook = gc.open_by_key(SPREADSHEET_KEY)
# 新規ワークシートを作成
# 昨日の日付を取得
today = datetime.today()
yesterday = today - timedelta(days=1)
yd = datetime.strftime(yesterday, '%Y%m%d')

worksheet = workbook.add_worksheet(title=yd, rows="500", cols="3")
# adebisのクリック数CSVの処理

data = pd.read_csv(path2, encoding='cp932')
dataExchange = data.rename(columns={'日付':'日付', '広告名':'広告名', 'クリック数':'セッション数'})
df = dataExchange.loc[:, ['日付', '広告名', 'セッション数']]
df = df.astype('object')
# print(df.dtypes)

df_rows = len(df)
df_columns = len(df.columns)
cell_list = worksheet.range(1,1,df_rows,df_columns)
for cell in cell_list:
    if cell.row == 0:
        val = df.columns[cell.col-1]
    else:
        val = df.iloc[cell.row-1][cell.col-1]
    cell.value = val
worksheet.update_cells(cell_list)
# print(cell_list)

# 指定したワークシートを削除する
dl = workbook.get_worksheet(0)
workbook.del_worksheet(dl)
print('ss作業終了')
# --------------------SSデータスプレッドシートへ反映完了------------------------

    # クリック数CSV ファイル出力する場合用
    #now = datetime.datetime.now()
    #df.to_csv(now.strftime('%Y%m%d%H%M') + '_adebis_ss.csv', encoding='cp932', index=False)

# --------------------CVデータを加工してスプレッドシートへ反映------------------------

#2つのAPIを記述しないとリフレッシュトークンを3600秒毎に発行し続けなければならない
scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
#認証情報設定
#ダウンロードしたjsonファイル名をクレデンシャル変数に設定（秘密鍵、Pythonファイルから読み込みしやすい位置に置く）
credentials = ServiceAccountCredentials.from_json_keyfile_name(r'\\nas\public\事務業務資料\100000管理部門\101000システム\事業部プログラム\講師求人部門\adebis_program\prime-freedom-288406-4ef65d06d8d0.json', scope)
#OAuth2の資格情報を使用してGoogle APIにログインします。
gc = gspread.authorize(credentials)
#共有設定したスプレッドシートキーを変数[SPREADSHEET_KEY]に格納する。
SPREADSHEET_KEY2 = '12g_E2bBfpWgGwLN18hUH9o5-aUUQwlaMuMKqcBFnu7s' #本番用
# SPREADSHEET_KEY = '1qhKrAUp-hwY1FnjTi003rT_UFY1ilHRaVJF0-2b8hzQ' テスト用

# スプレッドシート を開く
workbook2 = gc.open_by_key(SPREADSHEET_KEY2)
# 新規ワークシートを作成
# 昨日の日付を取得
today2 = datetime.today()
yesterday2 = today2 - timedelta(days=1)
yd2 = datetime.strftime(yesterday2, '%Y%m%d')

worksheet2 = workbook2.add_worksheet(title=yd2, rows="500", cols="3")

# adebisのクリック数CSVの処理
data2 = pd.read_csv(path4, encoding='cp932')
df2 = data2.loc[:, ['日付', '広告名', 'CV']]
df2 = df2.astype('object')
# print(df.dtypes)

df_rows2 = len(df2)
df_columns2 = len(df2.columns)
cell_list2 = worksheet2.range(1,1,df_rows2,df_columns2)
for cell in cell_list2:
    if cell.row == 0:
        val = df2.columns[cell.col-1]
    else:
        val = df2.iloc[cell.row-1][cell.col-1]
    cell.value = val
worksheet2.update_cells(cell_list2)
# print(cell_list)

# 指定したワークシートを削除する
dl2 = workbook2.get_worksheet(0)
workbook2.del_worksheet(dl2)
print('cv作業終了')
# --------------------CVデータスプレッドシートへ反映完了------------------------

    # CV数CSV ファイル出力
    #df.to_csv(now.strftime('%Y%m%d%H%M') + '_adebis_CV.csv', encoding='cp932', index=False)
# --------------------属性レポートを加工してスプレッドシートへ反映------------------------

#2つのAPIを記述しないとリフレッシュトークンを3600秒毎に発行し続けなければならない
scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
#認証情報設定
#ダウンロードしたjsonファイル名をクレデンシャル変数に設定（秘密鍵、Pythonファイルから読み込みしやすい位置に置く）
credentials = ServiceAccountCredentials.from_json_keyfile_name(r'\\nas\public\事務業務資料\100000管理部門\101000システム\事業部プログラム\講師求人部門\adebis_program\prime-freedom-288406-4ef65d06d8d0.json', scope)
#OAuth2の資格情報を使用してGoogle APIにログインします。
gc = gspread.authorize(credentials)
#共有設定したスプレッドシートキーを変数[SPREADSHEET_KEY]に格納する。
SPREADSHEET_KEY3 = '1bIbb5rmtqlh8vfVJhE3jGSl0FoH5lmX-HP-j7wENbw0' #本番用
# SPREADSHEET_KEY = '1qhKrAUp-hwY1FnjTi003rT_UFY1ilHRaVJF0-2b8hzQ' テスト用

# スプレッドシート を開く
workbook3 = gc.open_by_key(SPREADSHEET_KEY3)
# 新規ワークシートを作成
# 昨日の日付を取得
today = datetime.today()
yesterday = today - timedelta(days=1)
yd = datetime.strftime(yesterday, '%Y%m%d')

worksheet = workbook3.add_worksheet(title=yd, rows="500", cols="91")

# adebisの属性レポートCSVの処理
data = pd.read_csv(path6, encoding='cp932')
df2 = data.fillna('')
df3 = df2.astype('object')
#print(df3.dtypes)

df_rows = len(df3)
df_columns = len(df3.columns)

cell_list = worksheet.range(1,1,df_rows+1,df_columns)
for cell in cell_list:
    if cell.row == 1:
        val = df3.columns[cell.col-1]
    else:
        val = df3.iloc[cell.row-2][cell.col-1]
    cell.value = val
worksheet.update_cells(cell_list)
# print(cell_list)

# 指定したワークシートを削除する
dl3 = workbook3.get_worksheet(0)
workbook3.del_worksheet(dl3)
print('属性作業終了')
# --------------------属性レポートスプレッドシートへ反映完了------------------------

    # CV数CSV ファイル出力
    #df2.to_csv(now.strftime('%Y%m%d%H%M') + '_adebis_CV.csv', encoding='cp932', index=False)
