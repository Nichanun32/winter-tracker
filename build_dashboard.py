import os
import shutil
import json
import gdown
import pandas as pd
import numpy as np

FOLDER_ID = os.environ.get("GDRIVE_FOLDER_ID", "")

print(f"กำลังดาวน์โหลดไฟล์จาก Google Drive (Folder ID: {FOLDER_ID})...")
try:
    gdown.download_folder(id=FOLDER_ID, quiet=False, use_cookies=False)
except Exception as e:
    print(f"คำเตือนในการดาวน์โหลด: {e}")

# ย้ายไฟล์ทั้งหมดที่โหลดมาในโฟลเดอร์ย่อย (เช่น Winter69) ขึ้นมาไว้ที่โฟลเดอร์หลัก
for root, dirs, files in os.walk('.'):
    if '.git' in root:
        continue
    for file in files:
        if file.endswith('.xlsx'):
            src = os.path.join(root, file)
            dst = os.path.join('.', file)
            if src != dst:
                print(f"ย้ายไฟล์: {src} -> {dst}")
                shutil.copy(src, dst)

print("รายชื่อไฟล์ Excel ที่พบในโฟลเดอร์ปัจจุบัน:", [f for f in os.listdir('.') if f.endswith('.xlsx')])

# ฟังก์ชันช่วยค้นหาไฟล์แบบไม่สนตัวพิมพ์เล็ก-ใหญ่
def find_file(target_name):
    for f in os.listdir('.'):
        if f.lower() == target_name.lower():
            return f
    raise FileNotFoundError(f"ไม่พบไฟล์ {target_name} ในโฟลเดอร์ กรุณาตรวจสอบว่ามีไฟล์นี้ใน Google Drive หรือไม่")

file_min = find_file('min.xlsx')
file_rain = find_file('Rain.xlsx')
file_wind = find_file('850hPa.xlsx')

# โหลดข้อมูล Excel ทั้ง 3 ไฟล์
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

json_str = json.dumps({'days': days, 'stations': stations}, ensure_ascii=False)

# เทมเพลต HTML สมบูรณ์
html_content = """<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ระบบติดตามเกณฑ์การเข้าสู่ฤดูหนาวของประเทศไทย</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
  <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
  <style> body { font-family: 'Prompt', sans-serif; } </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen p-3 md:p-6">
  <div id="root"></div>

  <script type="text/babel">
    const RAW_DATA = """ + json_str + """;
    const { useState, useMemo } = React;

    function App() {
      const tempThreshold = 60;
      const rainThreshold = 60;
      const [windMode, setWindMode] = useState('NORTH');
      const [tempRegionFilter, setTempRegionFilter] = useState('ALL');
      const [windRegionFilter, setWindRegionFilter] = useState('ALL');

      const isWindPassing = (deg) => {
        if (deg === null || deg === undefined) return false;
        if (windMode === 'NE') return (deg >= 0 && deg <= 90);
        return ((deg >= 270 && deg <= 360) || (deg >= 0 && deg <= 90));
      };

      const dailyStats = useMemo(() => {
        return RAW_DATA.days.map((day, idx) => {
          const validTemps = RAW_DATA.stations.map(s => s.temps[idx]).filter(t => t !== null);
          const coolCount = validTemps.filter(t => t <= 23.0).length;
          const pctT = validTemps.length > 0 ? (coolCount / validTemps.length * 100) : null;
          const passT = pctT !== null ? pctT >= tempThreshold : null;

          const validWinds = RAW_DATA.stations.map(s => s.winds[idx]).filter(w => w !== null);
          const isPendingW = validWinds.length === 0;
          const passingW = validWinds.filter(w => isWindPassing(w)).length;
          const pctW = !isPendingW ? (passingW / validWinds.length * 100) : null;
          const passW = pctW !== null ? pctW >= 60.0 : null;

          const validRains = RAW_DATA.stations.map(s => s.rains[idx]).filter(r => r.is_free !== null);
          const isPendingR = validRains.length === 0;
          const freeCount = validRains.filter(r => r.is_free === true).length;
          const pctFreeR = !isPendingR ? (freeCount / validRains.length * 100) : null;
          const passR = pctFreeR !== null ? pctFreeR >= rainThreshold : null;

          const regRain = {};
          ['N', 'NE', 'C', 'E'].forEach(reg => {
            const stInReg = RAW_DATA.stations.filter(s => s.region === reg).map(s => s.rains[idx]).filter(r => r.is_free !== null);
            if (stInReg.length === 0) regRain[reg] = null;
            else {
              const f = stInReg.filter(r => r.is_free === true).length;
              regRain[reg] = Math.round((f / stInReg.length * 100) * 10) / 10;
            }
          });

          const isFullyReady = (pctT !== null && pctW !== null && pctFreeR !== null);
          const allPass = isFullyReady ? (passT && passW && passR) : false;

          return {
            day,
            pctT: pctT !== null ? Math.round(pctT * 10) / 10 : null,
            coolCount, totalT: validTemps.length, passT,
            pctW: pctW !== null ? Math.round(pctW * 10) / 10 : null, passW, isPendingW,
            pctFreeR: pctFreeR !== null ? Math.round(pctFreeR * 10) / 10 : null, passR, isPendingR, freeCount, totalR: validRains.length,
            regRain,
            isFullyReady, allPass
          };
        });
      }, [windMode]);

      const statsWithStreak = useMemo(() => {
        let streak = 0;
        return dailyStats.map(row => {
          if (row.isFullyReady && row.allPass) streak += 1;
          else if (row.isFullyReady && !row.allPass) streak = 0;
          return { ...row, streak };
        });
      }, [dailyStats]);

      const tempFilteredStations = useMemo(() => {
        if (tempRegionFilter === 'ALL') return RAW_DATA.stations;
        return RAW_DATA.stations.filter(s => s.region === tempRegionFilter);
      }, [tempRegionFilter]);

      const windFilteredStations = useMemo(() => {
        if (windRegionFilter === 'ALL') return RAW_DATA.stations;
        return RAW_DATA.stations.filter(s => s.region === windRegionFilter);
      }, [windRegionFilter]);

      const latestCompleted = statsWithStreak.filter(d => d.isFullyReady).slice(-1)[0] || statsWithStreak[0];
      const today14 = statsWithStreak.find(d => d.day === 14) || {};

      const completedDays = statsWithStreak.filter(d => d.pctT !== null);
      const totalDaysOver60 = completedDays.filter(d => d.pctT >= tempThreshold).length;
      const last3Days = completedDays.slice(-3);
      const last4Days = completedDays.slice(-4);
      const is3Pass = last3Days.length === 3 && last3Days.every(d => d.pctT >= tempThreshold);
      const is4Pass = last4Days.length === 4 && last4Days.every(d => d.pctT >= tempThreshold);

      const getTempColor = (t) => {
        if (t === null || t === undefined) return 'bg-slate-800 text-slate-500';
        if (t <= 20.0) return 'bg-blue-600 text-white font-bold';
        if (t <= 23.0) return 'bg-cyan-300 text-slate-950 font-bold border border-cyan-400';
        if (t <= 24.5) return 'bg-amber-100 text-slate-900';
        return 'bg-orange-500 text-white';
      };

      return (
        <div className="max-w-6xl mx-auto space-y-6 pb-12">
          
          {/* ส่วนที่ 1 */}
          <section className="bg-slate-900 border border-slate-800 p-5 md:p-6 rounded-2xl shadow-xl">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pb-4 border-b border-slate-800">
              <div>
                <span className="text-[11px] font-bold px-2.5 py-1 bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 rounded-full">
                  ส่วนที่ 1 • สรุปภาพรวม 3 เกณฑ์
                </span>
                <h1 className="text-xl md:text-2xl font-bold text-white mt-1.5">
                  ระบบติดตามการเข้าสู่ฤดูหนาวของประเทศไทย (99 สถานีไทยตอนบน)
                </h1>
                <p className="text-xs text-slate-400">เกณฑ์: อุณหภูมิ &le;23°C (&ge;60%) + ลมฝ่ายเหนือ (&ge;60%) + ปลอดฝน (&ge;60%) ต่อเนื่อง &ge;3-4 วัน</p>
              </div>

              <div className="flex items-center gap-4 bg-slate-800/90 px-5 py-3 rounded-xl border border-slate-700">
                <div>
                  <div className="text-[10px] text-slate-400 uppercase">Streak สะสมล่าสุด</div>
                  <div className="text-3xl font-black text-amber-400">{latestCompleted.streak} <span className="text-sm font-normal text-slate-400">/ 4 วัน</span></div>
                </div>
                <div className="h-8 w-px bg-slate-700" />
                <div className="text-xs">
                  <div className="text-slate-400 text-[10px]">สถานะ ณ วันที่ {latestCompleted.day} ต.ค.</div>
                  <span className={`font-bold ${latestCompleted.streak >= 3 ? 'text-emerald-400' : 'text-amber-400'}`}>
                    {latestCompleted.streak >= 3 ? 'เข้าสู่ฤดูหนาวแล้ว ❄️' : 'ช่วงเปลี่ยนผ่าน (รอความต่อเนื่อง) ⏳'}
                  </span>
                </div>
              </div>
            </div>

            <div className="overflow-x-auto mt-4">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="p-2.5">วันที่</th>
                    <th className="p-2.5 text-center">1. อุณหภูมิ &le;23°C (&ge;60%)</th>
                    <th className="p-2.5 text-center">2. ลม 850 hPa ({windMode === 'NE' ? '0-90°' : '270-90°'} &ge;60%)</th>
                    <th className="p-2.5 text-center">3. ปลอดฝน (&ge;60%)</th>
                    <th className="p-2.5 text-center">ผ่านครบ 3 ข้อ?</th>
                    <th className="p-2.5 text-center">Streak สะสม</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {statsWithStreak.map(row => (
                    <tr key={row.day} className="hover:bg-slate-800/40">
                      <td className="p-2 font-semibold text-slate-200">{row.day} ต.ค.</td>
                      <td className="p-2 text-center">
                        <span className={row.passT ? 'text-emerald-400 font-bold' : 'text-slate-300'}>
                          {row.pctT}% ({row.coolCount}/{row.totalT}) {row.passT ? '✅' : '❌'}
                        </span>
                      </td>
                      <td className="p-2 text-center">
                        {row.isPendingW ? (
                          <span className="text-amber-400/80 italic font-medium px-2 py-0.5 rounded bg-amber-400/10 border border-amber-400/20">Pending ⏳</span>
                        ) : (
                          <span className={row.passW ? 'text-emerald-400 font-bold' : 'text-slate-300'}>
                            {row.pctW}% {row.passW ? '✅' : '❌'}
                          </span>
                        )}
                      </td>
                      <td className="p-2 text-center">
                        {row.isPendingR ? (
                          <span className="text-amber-400/80 italic font-medium px-2 py-0.5 rounded bg-amber-400/10 border border-amber-400/20">Pending ⏳</span>
                        ) : (
                          <span className={row.passR ? 'text-emerald-400 font-bold' : 'text-slate-300'}>
                            ปลอดฝน {row.pctFreeR}% ({row.freeCount}/{row.totalR}) {row.passR ? '✅' : '❌'}
                          </span>
                        )}
                      </td>
                      <td className="p-2 text-center">
                        {!row.isFullyReady ? (
                          <span className="text-slate-500 text-[11px]">รอข้อมูลครบ</span>
                        ) : (
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${row.allPass ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-slate-800 text-slate-400'}`}>
                            {row.allPass ? 'ผ่านครบ ✅' : 'ไม่ผ่าน'}
                          </span>
                        )}
                      </td>
                      <td className="p-2 text-center font-bold text-slate-300">
                        {!row.isFullyReady ? '-' : `${row.streak} วัน`}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* ส่วนที่ 2 */}
          <section className="bg-slate-900 border border-slate-800 p-5 md:p-6 rounded-2xl shadow-xl space-y-5">
            <div>
              <span className="text-[11px] font-bold px-2.5 py-1 bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded-full">
                ส่วนที่ 2 • เกณฑ์อุณหภูมิต่ำสุด (&le; 23.0°C)
              </span>
              <h2 className="text-lg font-bold text-white mt-1">วิเคราะห์ความเย็น & การกระจายตัวรายสถานี</h2>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="bg-slate-800/60 p-4 rounded-xl border border-slate-700">
                <div className="text-[10px] text-slate-400 uppercase">สัดส่วนวันล่าสุด (14 ต.ค.)</div>
                <div className={`text-2xl font-black mt-1 ${today14.passT ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {today14.pctT}%
                </div>
                <div className="text-[11px] text-slate-400 mt-1">
                  {today14.coolCount} จาก {today14.totalT} สถานี ({today14.passT ? 'ผ่านเกณฑ์ 60%' : 'ยังไม่ถึงเกณฑ์ 60%'})
                </div>
              </div>

              <div className="bg-slate-800/60 p-4 rounded-xl border border-slate-700">
                <div className="text-[10px] text-slate-400 uppercase">3 WINDOWS DAYS ล่าสุด (12-14 ต.ค.)</div>
                <div className="flex items-center gap-1.5 mt-1.5">
                  {last3Days.map(d => (
                    <span key={d.day} className={`px-2 py-0.5 rounded text-xs font-bold font-mono ${d.pctT >= tempThreshold ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40' : 'bg-slate-700 text-slate-300'}`}>
                      {d.pctT}%
                    </span>
                  ))}
                </div>
                <div className="text-[11px] mt-2">
                  {is3Pass ? <span className="text-emerald-400 font-semibold">🟢 ผ่านต่อเนื่อง 3 วัน</span> : <span className="text-amber-400/90 font-medium">🟡 ยังไม่ผ่านต่อเนื่องทั้ง 3 วัน</span>}
                </div>
              </div>

              <div className="bg-slate-800/60 p-4 rounded-xl border border-slate-700">
                <div className="text-[10px] text-slate-400 uppercase">4 WINDOWS DAYS ล่าสุด (11-14 ต.ค.)</div>
                <div className="flex items-center gap-1 mt-1.5">
                  {last4Days.map(d => (
                    <span key={d.day} className={`px-1.5 py-0.5 rounded text-[11px] font-bold font-mono ${d.pctT >= tempThreshold ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40' : 'bg-slate-700 text-slate-300'}`}>
                      {d.pctT}%
                    </span>
                  ))}
                </div>
                <div className="text-[11px] mt-2">
                  {is4Pass ? <span className="text-emerald-400 font-semibold">🟢 ผ่านต่อเนื่อง 4 วัน</span> : <span className="text-amber-400/90 font-medium">🟡 ยังไม่ผ่านต่อเนื่องทั้ง 4 วัน</span>}
                </div>
              </div>

              <div className="bg-slate-800/60 p-4 rounded-xl border border-slate-700">
                <div className="text-[10px] text-slate-400 uppercase">จำนวนวันทั้งหมดที่เกิน 60%</div>
                <div className="text-2xl font-black text-cyan-400 mt-1">
                  {totalDaysOver60} <span className="text-sm font-normal text-slate-400">วัน</span>
                </div>
                <div className="text-[11px] text-slate-400 mt-1">ในรอบ {completedDays.length} วันที่ผ่านมา</div>
              </div>
            </div>

            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
              <div className="flex justify-between items-center text-xs text-slate-400 mb-2">
                <span>แนวโน้มสัดส่วนสถานี &le;23°C รายวัน (%)</span>
                <span className="text-amber-400 font-semibold">--- เส้นเกณฑ์ 60%</span>
              </div>
              <div className="flex items-end gap-1.5 h-28 pt-2">
                {dailyStats.map(d => {
                  const isOver = d.pctT >= tempThreshold;
                  return (
                    <div key={d.day} className="flex-1 flex flex-col items-center gap-1 h-full justify-end">
                      <span className="text-[9px] text-slate-400">{d.pctT}%</span>
                      <div 
                        className={`w-full rounded-t transition-all ${isOver ? 'bg-cyan-400 shadow-md shadow-cyan-500/20' : 'bg-slate-700'}`}
                        style={{ height: `${Math.min(100, (d.pctT / 70) * 100)}%` }}
                        title={`วันที่ ${d.day} ต.ค. : ${d.pctT}%`}
                      />
                      <span className="text-[9px] text-slate-500">{d.day}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="space-y-3 pt-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-sm font-bold text-white flex items-center gap-2">
                  <span>🗺️ ม่านคลื่นความเย็น 99 สถานี (เหนือ ➔ อีสาน ➔ กลาง ➔ ตะวันออก)</span>
                </div>
                <div className="flex gap-1 bg-slate-950 p-1 rounded-lg text-xs border border-slate-800">
                  {['ALL', 'N', 'NE', 'C', 'E'].map(reg => (
                    <button
                      key={reg}
                      onClick={() => setTempRegionFilter(reg)}
                      className={`px-2.5 py-0.5 rounded transition ${tempRegionFilter === reg ? 'bg-cyan-500 text-slate-950 font-bold' : 'text-slate-400'}`}
                    >
                      {reg}
                    </button>
                  ))}
                </div>
              </div>

              <div className="overflow-x-auto max-h-[540px] border border-slate-800 rounded-xl bg-slate-950/70 text-xs scrollbar-thin scrollbar-thumb-slate-700">
                <table className="w-full border-collapse">
                  <thead className="sticky top-0 bg-slate-900 text-slate-300 border-b border-slate-800 z-10">
                    <tr>
                      <th className="p-2 text-left sticky left-0 bg-slate-900 border-r border-slate-800 w-44">สถานีตรวจวัด</th>
                      {RAW_DATA.days.map(d => (
                        <th key={d} className="p-2 text-center w-11">{d} ต.ค.</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {tempFilteredStations.map(st => (
                      <tr key={st.name} className="hover:bg-slate-800/40">
                        <td className="p-1.5 px-2 font-medium text-slate-300 sticky left-0 bg-slate-950 border-r border-slate-800 flex justify-between">
                          <span className="truncate max-w-[130px]">{st.name}</span>
                          <span className="text-[9px] text-slate-500">{st.region}</span>
                        </td>
                        {st.temps.map((temp, idx) => (
                          <td key={idx} className="p-1 text-center">
                            <div className={`w-8 h-6 mx-auto rounded flex items-center justify-center font-mono text-[10px] ${getTempColor(temp)}`}>
                              {temp !== null ? temp.toFixed(1) : '-'}
                            </div>
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </section>

          {/* ส่วนที่ 3 */}
          <section className="bg-slate-900 border border-slate-800 p-5 md:p-6 rounded-2xl shadow-xl space-y-4">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
              <div>
                <span className="text-[11px] font-bold px-2.5 py-1 bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 rounded-full">
                  ส่วนที่ 3 • ทิศทางลมระดับล่าง 850 hPa
                </span>
                <h2 className="text-lg font-bold text-white mt-1">ก้านลูกศรลมรายสถานี (ศรลมมุ่งหน้าเข้าสู่สถานี)</h2>
              </div>

              <div className="flex items-center gap-2 bg-slate-950 p-1.5 rounded-xl border border-slate-800 text-xs">
                <span className="text-slate-400 pl-1 text-[11px]">เลือกเกณฑ์ลม:</span>
                <button
                  onClick={() => setWindMode('NE')}
                  className={`px-3 py-1 rounded-lg transition font-medium ${windMode === 'NE' ? 'bg-indigo-600 text-white font-bold' : 'text-slate-400'}`}
                >
                  1. ลม NE (0° - 90°)
                </button>
                <button
                  onClick={() => setWindMode('NORTH')}
                  className={`px-3 py-1 rounded-lg transition font-medium ${windMode === 'NORTH' ? 'bg-indigo-600 text-white font-bold' : 'text-slate-400'}`}
                >
                  2. ลมฝ่ายเหนือ (270° &rarr; 90°)
                </button>
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
              <div className="text-xs text-slate-400">
                หัวลูกศร <b>ชี้ตามทิศการเคลื่อนที่ของลมเข้าสู่สถานี</b> (เช่น ลมเหนือ 0° ลูกศรชี้ลงใต้ &darr;)
              </div>
              <div className="flex gap-1 bg-slate-950 p-1 rounded-lg text-xs border border-slate-800">
                {['ALL', 'N', 'NE', 'C', 'E'].map(reg => (
                  <button
                    key={reg}
                    onClick={() => setWindRegionFilter(reg)}
                    className={`px-2.5 py-0.5 rounded transition ${windRegionFilter === reg ? 'bg-indigo-600 text-white font-bold' : 'text-slate-400'}`}
                  >
                    {reg}
                  </button>
                ))}
              </div>
            </div>

            <div className="overflow-x-auto max-h-[500px] border border-slate-800 rounded-xl bg-slate-950/70 text-xs scrollbar-thin scrollbar-thumb-slate-700">
              <table className="w-full border-collapse">
                <thead className="sticky top-0 bg-slate-900 text-slate-400 border-b border-slate-800 z-10">
                  <tr>
                    <th className="p-2 text-left sticky left-0 bg-slate-900 border-r border-slate-800 w-44">สถานี ({windFilteredStations.length})</th>
                    {RAW_DATA.days.map(d => (
                      <th key={d} className="p-2 text-center w-11">{d} ต.ค.</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {windFilteredStations.map(st => (
                    <tr key={st.name} className="hover:bg-slate-800/40">
                      <td className="p-1.5 px-2 font-medium text-slate-300 sticky left-0 bg-slate-950 border-r border-slate-800 flex justify-between">
                        <span className="truncate max-w-[130px]">{st.name}</span>
                        <span className="text-[9px] text-slate-500">{st.region}</span>
                      </td>
                      {st.winds.map((deg, idx) => {
                        const pass = isWindPassing(deg);
                        const arrowRotation = deg !== null ? (deg + 180) % 360 : 0;
                        return (
                          <td key={idx} className="p-1 text-center">
                            {deg !== null ? (
                              <div 
                                className={`w-7 h-6 mx-auto flex items-center justify-center text-sm transition-transform hover:scale-125 ${pass ? 'text-cyan-300 font-bold drop-shadow-[0_0_6px_rgba(6,182,212,0.6)]' : 'text-slate-600'}`}
                                title={`${st.name}: ลมมาจากทิศ ${deg}° (พัดมุ่งหน้า ${arrowRotation}°)`}
                              >
                                <span style={{ display: 'inline-block', transform: `rotate(${arrowRotation}deg)` }}>&uarr;</span>
                              </div>
                            ) : (
                              <span className="text-slate-700 text-[10px]">-</span>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* ส่วนที่ 4 */}
          <section className="bg-slate-900 border border-slate-800 p-5 md:p-6 rounded-2xl shadow-xl space-y-4">
            <div>
              <span className="text-[11px] font-bold px-2.5 py-1 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-full">
                ส่วนที่ 4 • สัดส่วนพื้นที่ปลอดฝน (Rain-Free Area)
              </span>
              <h2 className="text-lg font-bold text-white mt-1">การถอยร่นของฝน แจกแจงรายภาค (N, NE, C, E) สู่ภาพรวม</h2>
              <p className="text-xs text-slate-400">นับเฉพาะสถานีที่ไม่มีฝนตก (-) เกณฑ์ผ่านภาพรวม: พื้นที่ปลอดฝน &ge; 60% ของไทยตอนบน (คิดรวมตรงจาก 99 สถานี)</p>
            </div>

            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3">
              <div className="flex justify-between items-center text-xs text-slate-400">
                <span>วันที่</span>
                <span className="hidden sm:inline">สัดส่วนพื้นที่ปลอดฝนรายภาค (เหนือ | อีสาน | กลาง | ตะวันออก)</span>
                <span>ภาพรวมไทยตอนบน (&ge;60%)</span>
              </div>

              <div className="space-y-2.5">
                {dailyStats.map(d => {
                  if (d.isPendingR) {
                    return (
                      <div key={d.day} className="flex items-center justify-between text-xs py-1 px-2 bg-slate-900/60 rounded border border-slate-800">
                        <span className="w-12 text-slate-400 font-mono">{d.day} ต.ค.</span>
                        <span className="text-amber-400/80 italic font-medium">Pending ⏳ ข้อมูลฝนของวันที่ 14 ยังไม่ครบวัน</span>
                        <span className="text-slate-600">-</span>
                      </div>
                    );
                  }

                  return (
                    <div key={d.day} className="flex flex-col sm:flex-row sm:items-center gap-2 text-xs py-1 border-b border-slate-900">
                      <span className="w-12 text-slate-300 font-mono shrink-0">{d.day} ต.ค.</span>
                      <div className="flex items-center gap-2 text-[11px] flex-1">
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300">เหนือ: <b className="text-cyan-400">{d.regRain.N}%</b></span>
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300">อีสาน: <b className="text-cyan-400">{d.regRain.NE}%</b></span>
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300">กลาง: <b className="text-cyan-400">{d.regRain.C}%</b></span>
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300">ตะวันออก: <b className="text-cyan-400">{d.regRain.E}%</b></span>
                      </div>
                      <div className="flex items-center gap-2 shrink-0 w-52 justify-end">
                        <div className="w-24 h-3 bg-slate-800 rounded-full overflow-hidden flex">
                          <div className={`h-full ${d.passR ? 'bg-emerald-500' : 'bg-amber-400'}`} style={{ width: `${d.pctFreeR}%` }} />
                        </div>
                        <span className={`font-mono font-bold w-16 text-right ${d.passR ? 'text-emerald-400' : 'text-slate-400'}`}>
                          {d.pctFreeR}%
                        </span>
                        <span className="text-[10px]">{d.passR ? '✅' : '❌'}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </section>

        </div>
      );
    }

    ReactDOM.render(<App />, document.getElementById('root'));
  </script>
</body>
</html>"""

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("✅ อัปเดต index.html สำเร็จเรียบร้อย!")
