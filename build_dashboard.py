import os
import shutil
import json
import urllib.request
import ssl
import gdown
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

FOLDER_ID = os.environ.get("GDRIVE_FOLDER_ID", "")
try:
    gdown.download_folder(id=FOLDER_ID, quiet=False, use_cookies=False)
except Exception as e:
    print(f"คำเตือน: {e}")

for root, dirs, files in os.walk('.'):
    if '.git' in root: continue
    for file in files:
        if file.endswith('.xlsx'):
            src = os.path.join(root, file)
            dst = os.path.join('.', file)
            if src != dst: shutil.copy(src, dst)

def find_file(target_name):
    for f in os.listdir('.'):
        if f.lower() == target_name.lower(): return f
    raise FileNotFoundError(f"ไม่พบไฟล์ {target_name}")

file_min = find_file('min.xlsx')
file_rain = find_file('Rain.xlsx')
file_wind = find_file('850hPa.xlsx')

df_min = pd.read_excel(file_min, header=None)
df_rain = pd.read_excel(file_rain, header=None)
xls_wind = pd.ExcelFile(file_wind)

station_rows = list(range(2, 32)) + list(range(33, 64)) + list(range(65, 87)) + list(range(88, 104))
df_wind_all = pd.concat([pd.read_excel(xls_wind, sheet_name=s) for s in ['N', 'NE', 'C', 'E']], ignore_index=True)

days = [d for d in range(1, 32) if (d+1) < df_min.shape[1] and pd.to_numeric(df_min.iloc[station_rows, d+1], errors='coerce').notna().sum() > 10]

stations = []
for idx in station_rows:
    st_name = str(df_min.iloc[idx, 1]).strip()
    reg = 'N' if idx < 32 else ('NE' if idx < 64 else ('C' if idx < 87 else 'E'))
    t_list, r_list, w_list = [], [], []
    for d in days:
        vt = pd.to_numeric(df_min.iloc[idx, d+1], errors='coerce')
        t_list.append(None if pd.isna(vt) else round(float(vt), 1))
        
        vr = str(df_rain.iloc[idx, d+1]).strip()
        if vr in ['nan', 'None', '']: r_free, r_raw = None, None
        elif vr in ['-', '0']: r_free, r_raw = True, '-'
        else: r_free, r_raw = False, vr
        r_list.append({'is_free': r_free, 'raw': r_raw})
        
        if d in df_wind_all.columns:
            vw = pd.to_numeric(df_wind_all.iloc[len(stations), d], errors='coerce')
            w_list.append(None if pd.isna(vw) else int(vw))
        else:
            w_list.append(None)
            
    stations.append({'name': st_name, 'region': reg, 'temps': t_list, 'rains': r_list, 'winds': w_list})

sounding_stations = [
    {'stnm': '48327', 'name': 'Chiang Mai (เชียงใหม่)', 'reg': 'เหนือ'},
    {'stnm': '48378', 'name': 'Phitsanulok (พิษณุโลก)', 'reg': 'เหนือล่าง'},
    {'stnm': '48381', 'name': 'Khon Kaen (ขอนแก่น)', 'reg': 'อีสานบน'},
    {'stnm': '48407', 'name': 'Ubon Ratchathani (อุบลฯ)', 'reg': 'อีสานล่าง'},
    {'stnm': '48431', 'name': 'Nakhon Ratchasima (โคราช)', 'reg': 'อีสานล่าง'},
    {'stnm': '48453', 'name': 'Bangna, BKK (บางนา)', 'reg': 'กลาง'},
    {'stnm': '48480', 'name': 'Chanthaburi (จันทบุรี)', 'reg': 'ตะวันออก'},
    {'stnm': '48500', 'name': 'Prachuap Khiri Khan (ประจวบฯ)', 'reg': 'ประจวบฯ'}
]

current_ref_day = days[-1]
past_5_days = [current_ref_day - i for i in range(4, -1, -1) if (current_ref_day - i) > 0]

def fetch_wyoming_exact(task):
    stnm, day = task
    url = f"https://weather.uwyo.edu/wsgi/sounding?src=FM35&datetime=2026-10-{day:02d}%2000:00:00&id={stnm}&type=TEXT:LIST"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    d850, d200 = None, None
    try:
        with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
            text = response.read().decode('utf-8', errors='ignore')
            for line in text.splitlines():
                if len(line) >= 49:
                    p_str = line[0:7].strip()
                    drct_str = line[42:49].strip()
                    if p_str == '850.0' and drct_str != '': d850 = int(float(drct_str))
                    elif p_str == '200.0' and drct_str != '': d200 = int(float(drct_str))
    except Exception:
        pass
    return (stnm, day, d850, d200)

tasks = [(st['stnm'], d) for st in sounding_stations for d in past_5_days]
results_map = {}
with ThreadPoolExecutor(max_workers=10) as executor:
    for stnm, day, d850, d200 in executor.map(fetch_wyoming_exact, tasks):
        results_map[(stnm, day)] = {'d850': d850, 'd200': d200}

sounding_history = []
for st in sounding_stations:
    day_series = []
    l850, l200 = 85, 260
    for d in past_5_days:
        res = results_map.get((st['stnm'], d), {'d850': None, 'd200': None})
        d850 = res['d850'] if res['d850'] is not None else l850
        if res['d850'] is not None: l850 = res['d850']
        d200 = res['d200'] if res['d200'] is not None else l200
        if res['d200'] is not None: l200 = res['d200']
        day_series.append({'day': d, 'd850': d850, 'd200': d200})
    sounding_history.append({'stnm': st['stnm'], 'name': st['name'], 'reg': st['reg'], 'history': day_series})

print("✅ สรุปการทำงาน build_dashboard.py เสร็จสิ้นสมบูรณ์")
