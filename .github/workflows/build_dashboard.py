import pandas as pd
import numpy as np
import json
import gdown
import os

# รหัสโฟลเดอร์ Google Drive ของคุณ
FOLDER_ID = os.environ.get("GDRIVE_FOLDER_ID", "1vpzd1i-zq9RScZBiSeJO4lupPguAWl5h")

# ดาวน์โหลดไฟล์จาก Google Drive
print("กำลังดึงข้อมูลล่าสุดจาก Google Drive...")
gdown.download_folder(id=FOLDER_ID, quiet=False, use_cookies=False)

# โหลดข้อมูล
df_min = pd.read_excel('min.xlsx', header=None)
df_rain = pd.read_excel('Rain.xlsx', header=None)
xls_wind = pd.ExcelFile('850hPa.xlsx')

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

json_str = json.dumps({'days': days, 'stations': stations}, ensure_ascii=False)

# อ่านเทมเพลต HTML และประกอบเป็น index.html
with open('winter_dashboard_template.html', 'r', encoding='utf-8') as f:
    html_template = f.read()

full_html = html_template.replace("__RAW_DATA__", json_str)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(full_html)

print("✅ อัปเดต index.html สำหรับ GitHub Pages สำเร็จเรียบร้อย!")