import json

# โหลดข้อมูล JSON จากแหล่งที่คุณมีอยู่
try:
    with open('final_github_data.json', 'r', encoding='utf-8') as f:
        json_data = json.load(f)
except Exception as e:
    json_data = {"days": [], "stations": [], "past_5_days": [], "sounding_history": []}

json_str = json.dumps(json_data, ensure_ascii=False)

html_template = """<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ระบบติดตามการเข้าสู่ฤดูหนาวของประเทศไทย (Winter Onset Intelligence)</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
  <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
  <style>
    body { font-family: 'Prompt', sans-serif; }
    .scrollbar-thin::-webkit-scrollbar { height: 6px; width: 6px; }
    .scrollbar-thin::-webkit-scrollbar-track { background: #0f172a; }
    .scrollbar-thin::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
  </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen p-3 md:p-6 antialiased">
  <div id="root"></div>

  <script type="text/babel">
    const DATA = __DATA_PLACEHOLDER__;
    const { useState, useMemo } = React;

    function App() {
      const [activeTab, setActiveTab] = useState('TEMP');
      const [windMode, setWindMode] = useState('NORTH');
      const [regionFilter, setRegionFilter] = useState('ALL');

      const isWindPassing = (deg) => {
        if (deg === null || deg === undefined) return false;
        if (windMode === 'NE') return (deg >= 0 && deg <= 90);
        return ((deg >= 270 && deg <= 360) || (deg >= 0 && deg <= 90));
      };

      const getCompassText = (deg) => {
        if (deg === null || deg === undefined) return 'ไม่มีรายงาน';
        if (deg >= 0 && deg <= 90) return `NE (${deg}°)`;
        if (deg > 90 && deg <= 180) return `SE (${deg}°)`;
        if (deg > 180 && deg < 270) return `SW (${deg}°)`;
        return `NW/N (${deg}°)`;
      };

      const dailyAnalysis = useMemo(() => {
        return DATA.days.map((day, idx) => {
          const validT = DATA.stations.map(s => s.temps[idx]).filter(t => t !== null);
          
          // แก้ไขเกณฑ์อุณหภูมิเป็น "ต่ำกว่า 23 องศาเซลเซียส" (< 23.0) ตามระเบียบราชการอย่างถูกต้อง
          const coolCount = validT.filter(t => t < 23.0).length;
          const pctT = validT.length > 0 ? Math.round((coolCount / validT.length * 100) * 10) / 10 : null;
          
          const validW = DATA.stations.map(s => s.winds[idx]).filter(w => w !== null);
          const isPendingW = validW.length === 0;
          const passingW = validW.filter(w => isWindPassing(w)).length;
          const pctW = !isPendingW ? Math.round((passingW / validW.length * 100) * 10) / 10 : null;

          const validR = DATA.stations.map(s => s.rains[idx]).filter(r => r.is_free !== null);
          const isPendingR = validR.length === 0;
          const freeCount = validR.filter(r => r.is_free === true).length;
          const pctFreeR = !isPendingR ? Math.round((freeCount / validR.length * 100) * 10) / 10 : null;

          const regRain = {};
          ['N', 'NE', 'C', 'E'].forEach(reg => {
            const stInReg = DATA.stations.filter(s => s.region === reg).map(s => s.rains[idx]).filter(r => r.is_free !== null);
            if (stInReg.length === 0) regRain[reg] = null;
            else {
              const f = stInReg.filter(r => r.is_free === true).length;
              regRain[reg] = Math.round((f / stInReg.length * 100) * 10) / 10;
            }
          });

          return {
            day, pctT, coolCount, totalT: validT.length,
            pctW, isPendingW,
            pctFreeR, isPendingR, freeCount, totalR: validR.length,
            regRain
          };
        });
      }, [windMode]);

      const statsWithStreak = useMemo(() => {
        let streak = 0;
        return dailyAnalysis.map(row => {
          const iconPassT = row.pctT !== null && row.pctT >= 60.0;
          const iconPassW = row.pctW !== null && row.pctW >= 60.0;
          const iconPassR = row.pctFreeR !== null && row.pctFreeR >= 60.0;
          const isFullyReady = (row.pctT !== null && row.pctW !== null && row.pctFreeR !== null);
          const passCount = (iconPassT ? 1 : 0) + (iconPassW ? 1 : 0) + (iconPassR ? 1 : 0);
          const allPass = isFullyReady ? (passCount === 3) : false;

          if (isFullyReady) {
            if (allPass) streak += 1;
            else streak = 0;
          }
          return { ...row, iconPassT, iconPassW, iconPassR, isFullyReady, passCount, allPass, streak };
        });
      }, [dailyAnalysis]);

      const completedDays = statsWithStreak.filter(d => d.isFullyReady);
      const evalDay = completedDays[completedDays.length - 1] || statsWithStreak[0];
      const todayPending = statsWithStreak[statsWithStreak.length - 1];

      const filteredStations = useMemo(() => {
        if (regionFilter === 'ALL') return DATA.stations;
        return DATA.stations.filter(s => s.region === regionFilter);
      }, [regionFilter]);

      const getTempColor = (t) => {
        if (t === null || t === undefined) return 'bg-slate-800 text-slate-500';
        if (t <= 20.0) return 'bg-blue-600 text-white font-bold';
        if (t < 23.0) return 'bg-cyan-300 text-slate-950 font-bold border border-cyan-400';
        if (t <= 24.5) return 'bg-amber-100 text-slate-900';
        return 'bg-orange-500 text-white';
      };

      return (
        <div className="max-w-5xl mx-auto space-y-5 pb-16">
          
          <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl shadow-xl">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pb-4 border-b border-slate-800">
              <div>
                <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-[11px] font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 mb-1.5">
                  WINTER ONSET INTELLIGENCE • การประเมินผลทางการ
                </div>
                <h1 className="text-xl md:text-2xl font-bold text-white tracking-tight flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-amber-400 animate-pulse"></span>
                  ยังไม่เข้าเกณฑ์ฤดูหนาว (ระยะเปลี่ยนผ่าน)
                </h1>
                <p className="text-xs text-slate-400 mt-1">
                  ตัดสินจากวันที่มีข้อมูลครบ 3 เกณฑ์ล่าสุด: <b>{evalDay.day} ตุลาคม 2569</b> (เกณฑ์ &ge;60% พร้อมกันต่อเนื่อง 3–4 วัน)
                </p>
              </div>

              <div className="bg-slate-800/90 border border-slate-700/80 px-5 py-3 rounded-xl flex items-center gap-4 shrink-0 shadow-lg">
                <div>
                  <div className="text-[10px] text-slate-400 uppercase tracking-wider">Streak สะสมล่าสุด</div>
                  <div className="text-3xl font-black text-amber-400 mt-0.5 font-mono">
                    {evalDay.streak} <span className="text-sm font-normal text-slate-400">/ 4 วัน</span>
                  </div>
                </div>
                <div className="h-9 w-px bg-slate-700"></div>
                <div>
                  <div className="text-[10px] text-slate-400 uppercase tracking-wider">ผลการตัดสิน ({evalDay.day} ต.ค.)</div>
                  <div className={`text-xs font-bold mt-0.5 ${evalDay.streak >= 3 ? 'text-emerald-400' : 'text-amber-400'}`}>
                    ผ่าน {evalDay.passCount}/3 เกณฑ์ ⏳
                  </div>
                </div>
              </div>
            </div>

            <div className="space-y-2 mt-4">
              <div className="flex justify-between items-center text-xs text-slate-400 px-1">
                <span>สถานะของทั้ง 3 เกณฑ์หลัก ({evalDay.day} ต.ค.):</span>
                {todayPending.day !== evalDay.day && (
                  <span className="text-cyan-400 text-[11px] font-mono">
                    * ข้อมูลเช้าวันที่ {todayPending.day} ต.ค. อุณหภูมิ &lt;23°C อยู่ที่ {todayPending.pctT}% (รอข้อมูลลม-ฝนรอบวัน)
                  </span>
                )}
              </div>

              <div className="grid grid-cols-3 gap-2.5">
                <div className="bg-slate-950/70 border border-slate-800/80 p-3 rounded-xl text-center">
                  <div className="text-[11px] text-slate-400">🌡️ 1. อุณหภูมิ &lt;23°C</div>
                  <div className={`text-xl md:text-2xl font-black mt-1 ${evalDay.iconPassT ? 'text-cyan-400' : 'text-slate-200'}`}>
                    {evalDay.pctT}%
                  </div>
                  <span className={`inline-block mt-1 text-[10px] px-2 py-0.5 rounded-full font-bold ${evalDay.iconPassT ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-800 text-slate-400'}`}>
                    {evalDay.iconPassT ? 'ผ่านเกณฑ์ 60% ✅' : `ไม่ถึง 60% (${evalDay.coolCount}/99) ❌`}
                  </span>
                </div>

                <div className="bg-slate-950/70 border border-slate-800/80 p-3 rounded-xl text-center">
                  <div className="text-[11px] text-slate-400">💨 2. ลมผิวพื้นฝ่ายเหนือ</div>
                  <div className={`text-xl md:text-2xl font-black mt-1 ${evalDay.iconPassW ? 'text-indigo-400' : 'text-slate-200'}`}>
                    {evalDay.pctW}%
                  </div>
                  <span className={`inline-block mt-1 text-[10px] px-2 py-0.5 rounded-full font-bold ${evalDay.iconPassW ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-800 text-slate-400'}`}>
                    {evalDay.iconPassW ? 'ผ่านเกณฑ์ ✅' : 'ไม่ถึง 60% ❌'}
                  </span>
                </div>

                <div className="bg-slate-950/70 border border-slate-800/80 p-3 rounded-xl text-center">
                  <div className="text-[11px] text-slate-400">☀️ 3. ปลอดฝน (-)</div>
                  <div className={`text-xl md:text-2xl font-black mt-1 ${evalDay.iconPassR ? 'text-emerald-400' : 'text-slate-200'}`}>
                    {evalDay.pctFreeR}%
                  </div>
                  <span className={`inline-block mt-1 text-[10px] px-2 py-0.5 rounded-full font-bold ${evalDay.iconPassR ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-800 text-slate-400'}`}>
                    {evalDay.iconPassR ? 'ผ่านเกณฑ์ ✅' : `ไม่ถึง 60% (${evalDay.freeCount}/99) ❌`}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl shadow-xl space-y-5">
            <div>
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 mb-3">
                <div>
                  <h2 className="text-base font-bold text-white">แนวโน้มสัดส่วนพื้นที่ผ่านเกณฑ์ย้อนหลัง (1 - {evalDay.day} ต.ค.)</h2>
                  <p className="text-xs text-slate-400">เปรียบเทียบสัดส่วนสถานีที่ผ่านเกณฑ์ทั้ง 3 ข้อเทียบกับเส้นตัดสิน 60%</p>
                </div>
                <div className="flex items-center gap-3 text-[11px]">
                  <span className="flex items-center gap-1 text-cyan-400"><span className="w-2.5 h-2.5 bg-cyan-400 rounded-full inline-block"></span> 🌡️ อุณหภูมิ &lt;23°C</span>
                  <span className="flex items-center gap-1 text-indigo-400"><span className="w-2.5 h-2.5 bg-indigo-500 rounded-full inline-block"></span> 💨 ลมฝ่ายเหนือ</span>
                  <span className="flex items-center gap-1 text-emerald-400"><span className="w-2.5 h-2.5 bg-emerald-500 rounded-full inline-block"></span> ☀️ ปลอดฝน</span>
                </div>
              </div>

              <div className="w-full bg-slate-950 rounded-xl p-3 border border-slate-800 space-y-2">
                <div className="relative w-full h-32 flex items-end justify-between border-b border-slate-800">
                  <div className="absolute left-0 right-0 bottom-[60%] border-b border-dashed border-amber-400 z-0 flex justify-end pr-2 pointer-events-none">
                    <span className="text-[10px] text-amber-400 bg-slate-950 px-1 font-mono -mt-2">เกณฑ์ตัดสิน 60%</span>
                  </div>

                  {statsWithStreak.map(d => (
                    <div key={d.day} className="flex-1 flex flex-col items-center gap-1 h-full justify-end group relative z-10">
                      <div className="hidden group-hover:flex absolute bottom-full mb-1 flex-col bg-slate-800 border border-slate-700 text-[10px] p-2 rounded shadow-lg z-20 pointer-events-none whitespace-nowrap">
                        <span className="font-bold text-slate-200">วันที่ {d.day} ต.ค. (ผ่าน {d.passCount}/3)</span>
                        <span className="text-cyan-400">🌡️ อุณหภูมิ: {d.pctT !== null ? d.pctT+'%' : '-'} {d.iconPassT ? '✅' : '❌'}</span>
                        <span className="text-indigo-400">💨 ลมฝ่ายเหนือ: {d.pctW !== null ? d.pctW+'%' : 'รอข้อมูล'} {d.iconPassW ? '✅' : '❌'}</span>
                        <span className="text-emerald-400">☀️ ปลอดฝน: {d.pctFreeR !== null ? d.pctFreeR+'%' : 'รอข้อมูล'} {d.iconPassR ? '✅' : '❌'}</span>
                      </div>

                      <div className="w-full flex items-end justify-center gap-0.5 h-full">
                        {d.pctT !== null && <div className="w-1.5 bg-cyan-400 rounded-t" style={{ height: `${d.pctT}%` }}></div>}
                        {d.pctW !== null && <div className="w-1.5 bg-indigo-500 rounded-t" style={{ height: `${d.pctW}%` }}></div>}
                        {d.pctFreeR !== null && <div className="w-1.5 bg-emerald-500 rounded-t" style={{ height: `${d.pctFreeR}%` }}></div>}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="flex justify-between px-1">
                  {statsWithStreak.map(d => (
                    <div key={d.day} className="flex-1 text-center">
                      <span className="text-[9px] font-mono text-slate-400">{d.day}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-800">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-1 mb-3">
                <div>
                  <h3 className="text-sm font-bold text-white">ไทม์ไลน์สัญลักษณ์การผ่านเกณฑ์รายวัน (1 - ปัจจุบัน)</h3>
                  <p className="text-[11px] text-slate-400">ไอคอนผูกกับความสูงของแท่งกราฟที่ผ่าน &ge; 60% โดยตรงอย่างไร้รอยต่อ</p>
                </div>
                <div className="flex items-center gap-2 text-[10px]">
                  <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">ครบ 3/3</span>
                  <span className="px-2 py-0.5 rounded bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">ผ่าน 2/3</span>
                  <span className="px-2 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30">ผ่าน 1/3</span>
                  <span className="px-2 py-0.5 rounded bg-slate-900 text-slate-500 border border-slate-800">0/3</span>
                </div>
              </div>

              <div className="grid grid-cols-5 sm:grid-cols-8 md:grid-cols-15 gap-1.5">
                {statsWithStreak.map(d => {
                  let cardStyle = 'bg-slate-950 border-slate-800 text-slate-500';
                  if (!d.isFullyReady) {
                    cardStyle = 'bg-slate-950/60 border-dashed border-slate-700 text-amber-400';
                  } else if (d.passCount === 3) {
                    cardStyle = 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300 shadow-md shadow-emerald-500/10';
                  } else if (d.passCount === 2) {
                    cardStyle = 'bg-cyan-500/15 border-cyan-500/40 text-cyan-200';
                  } else if (d.passCount === 1) {
                    cardStyle = 'bg-amber-500/10 border-amber-500/30 text-amber-200';
                  }

                  return (
                    <div key={d.day} className={`p-2 rounded-xl border text-center flex flex-col items-center justify-between ${cardStyle}`}>
                      <div className="text-[10px] font-mono font-bold">{d.day} ต.ค.</div>
                      
                      {!d.isFullyReady ? (
                        <div className="my-1 text-[10px] text-amber-400 font-medium">รอข้อมูล</div>
                      ) : (
                        <div className="flex items-center justify-center gap-0.5 my-1 text-xs">
                          <span className={d.iconPassT ? 'opacity-100 scale-110' : 'opacity-20 grayscale'} title="เกณฑ์อุณหภูมิ">🌡️</span>
                          <span className={d.iconPassW ? 'opacity-100 scale-110' : 'opacity-20 grayscale'} title="เกณฑ์ลม">💨</span>
                          <span className={d.iconPassR ? 'opacity-100 scale-110' : 'opacity-20 grayscale'} title="เกณฑ์ปลอดฝน">☀️</span>
                        </div>
                      )}

                      <div className="text-[9px] font-mono opacity-80">
                        {!d.isFullyReady ? '⏳' : `${d.passCount}/3 ข้อ`}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl shadow-xl space-y-4">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-slate-800 pb-3">
              <div>
                <span className="text-[11px] font-bold px-2.5 py-1 bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 rounded-full">
                  การตรวจอากาศชั้นบน • UPPER-AIR SOUNDING (00 UTC)
                </span>
                <h2 className="text-base font-bold text-white mt-1.5">
                  สรุปทิศทางลมชั้นบน 200 hPa (บน) และ 850 hPa (ล่าง) • 8 สถานีหลัก (ย้อนหลัง 5 วัน)
                </h2>
              </div>
              <a href="https://weather.uwyo.edu/upperair/sounding.shtml" target="_blank" className="text-xs text-cyan-400 hover:underline shrink-0">
                Univ. of Wyoming ↗
              </a>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {DATA.sounding_history.map(st => {
                const latestValid = [...st.history].reverse().find(h => h.d850 !== null || h.d200 !== null) || st.history[st.history.length - 1];
                const is850NE = latestValid.d850 !== null && ((latestValid.d850 >= 0 && latestValid.d850 <= 110) || latestValid.d850 >= 330);

                return (
                  <div key={st.stnm} className="bg-slate-950 border border-slate-800/90 rounded-xl p-3.5 space-y-2.5">
                    <div className="flex justify-between items-center border-b border-slate-900 pb-2">
                      <div>
                        <div className="text-xs font-bold text-white flex items-center gap-1.5">
                          <span>{st.name}</span>
                          <span className="text-[10px] font-mono text-slate-500">#{st.stnm}</span>
                        </div>
                        <div className="text-[10px] text-slate-400">ภูมิภาค: {st.reg}</div>
                      </div>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${is850NE ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' : 'bg-slate-800 text-slate-400'}`}>
                        850 ล่าสุด: {getCompassText(latestValid.d850)}
                      </span>
                    </div>

                    <div className="grid grid-cols-6 gap-1 text-center text-[11px] items-center">
                      <div className="text-left text-[10px] text-slate-500 font-mono">วันที่</div>
                      {st.history.map(h => (
                        <div key={h.day} className="text-[10px] text-slate-400 font-mono">{h.day} ต.ค.</div>
                      ))}

                      <div className="text-left font-bold text-indigo-400 text-[10px] bg-indigo-950/30 px-1.5 py-1 rounded">200 hPa</div>
                      {st.history.map(h => (
                        <div key={h.day} className="bg-slate-900/70 py-1 rounded border border-slate-800/60 flex flex-col items-center justify-center min-h-[36px]">
                          {h.d200 !== null ? (
                            <>
                              <span className="text-indigo-400 text-xs leading-none" style={{ display: 'inline-block', transform: `rotate(${(h.d200 + 180) % 360}deg)` }}>↑</span>
                              <span className="font-mono text-[10px] text-slate-300 mt-0.5">{h.d200}°</span>
                            </>
                          ) : <span className="text-slate-600 text-[10px]">-</span>}
                        </div>
                      ))}

                      <div className="text-left font-bold text-cyan-400 text-[10px] bg-cyan-950/30 px-1.5 py-1 rounded">850 hPa</div>
                      {st.history.map(h => {
                        const passNE = h.d850 !== null && ((h.d850 >= 0 && h.d850 <= 110) || h.d850 >= 330);
                        return (
                          <div key={h.day} className={`py-1 rounded border flex flex-col items-center justify-center min-h-[36px] ${passNE ? 'bg-cyan-950/30 border-cyan-500/40' : 'bg-slate-900/70 border-slate-800/60'}`}>
                            {h.d850 !== null ? (
                              <>
                                <span className={`text-xs leading-none ${passNE ? 'text-cyan-300 font-bold' : 'text-slate-400'}`} style={{ display: 'inline-block', transform: `rotate(${(h.d850 + 180) % 360}deg)` }}>↑</span>
                                <span className={`font-mono text-[10px] mt-0.5 ${passNE ? 'text-cyan-300 font-bold' : 'text-slate-300'}`}>{h.d850}°</span>
                              </>
                            ) : <span className="text-slate-600 text-[10px]">-</span>}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl shadow-xl space-y-4">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">ข้อมูลเชิงลึกรายสถานี (Deep-Dive Explorer)</h3>
                <p className="text-xs text-slate-400">เลือกดูม่านคลื่นความเย็น 99 สถานี ลมผิวพื้น หรือแถบสเกลสัดส่วนฝน</p>
              </div>

              <div className="flex gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs">
                <button onClick={() => setActiveTab('TEMP')} className={`px-3 py-1 rounded-lg font-medium transition ${activeTab === 'TEMP' ? 'bg-cyan-500 text-slate-950 font-bold' : 'text-slate-400'}`}>อุณหภูมิต่ำสุด</button>
                <button onClick={() => setActiveTab('WIND_SURF')} className={`px-3 py-1 rounded-lg font-medium transition ${activeTab === 'WIND_SURF' ? 'bg-indigo-600 text-white font-bold' : 'text-slate-400'}`}>ลมผิวพื้น</button>
                <button onClick={() => setActiveTab('RAIN')} className={`px-3 py-1 rounded-lg font-medium transition ${activeTab === 'RAIN' ? 'bg-emerald-600 text-white font-bold' : 'text-slate-400'}`}>สัดส่วนฝน</button>
              </div>
            </div>

            {activeTab === 'TEMP' && (
              <div className="space-y-3">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400">ม่านความเย็น 99 สถานี (&lt;23°C)</span>
                  <div className="flex gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
                    {['ALL', 'N', 'NE', 'C', 'E'].map(reg => (
                      <button key={reg} onClick={() => setRegionFilter(reg)} className={`px-2.5 py-0.5 rounded transition ${regionFilter === reg ? 'bg-cyan-500 text-slate-950 font-bold' : 'text-slate-400'}`}>{reg}</button>
                    ))}
                  </div>
                </div>

                <div className="overflow-x-auto max-h-[460px] border border-slate-800 rounded-xl bg-slate-950/70 text-xs scrollbar-thin">
                  <table className="w-full border-collapse">
                    <thead className="sticky top-0 bg-slate-900 text-slate-300 border-b border-slate-800 z-10">
                      <tr>
                        <th className="p-2 text-left sticky left-0 bg-slate-900 border-r border-slate-800 w-44">สถานีตรวจวัด ({filteredStations.length})</th>
                        {DATA.days.map(d => <th key={d} className="p-2 text-center w-11">{d} ต.ค.</th>)}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {filteredStations.map(st => (
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
            )}

            {activeTab === 'WIND_SURF' && (
              <div className="space-y-3">
                <div className="flex justify-between items-center text-xs text-slate-400">
                  <span>ก้านศรลมหมุนตามทิศการเคลื่อนที่เข้าหาสถานี (deg + 180°)</span>
                  <div className="flex gap-2">
                    <button onClick={() => setWindMode('NE')} className={`px-2 py-0.5 rounded text-[11px] ${windMode === 'NE' ? 'bg-indigo-600 text-white font-bold' : 'text-slate-400'}`}>เกณฑ์ NE (0-90°)</button>
                    <button onClick={() => setWindMode('NORTH')} className={`px-2 py-0.5 rounded text-[11px] ${windMode === 'NORTH' ? 'bg-indigo-600 text-white font-bold' : 'text-slate-400'}`}>เกณฑ์ลมฝ่ายเหนือ (270-90°)</button>
                  </div>
                </div>

                <div className="overflow-x-auto max-h-[460px] border border-slate-800 rounded-xl bg-slate-950/70 text-xs scrollbar-thin">
                  <table className="w-full border-collapse">
                    <thead className="sticky top-0 bg-slate-900 text-slate-400 border-b border-slate-800 z-10">
                      <tr>
                        <th className="p-2 text-left sticky left-0 bg-slate-900 border-r border-slate-800 w-44">สถานี ({filteredStations.length})</th>
                        {DATA.days.map(d => <th key={d} className="p-2 text-center w-11">{d} ต.ค.</th>)}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {filteredStations.map(st => (
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
                                  <div className={`w-7 h-6 mx-auto flex items-center justify-center text-sm ${pass ? 'text-cyan-300 font-bold drop-shadow-[0_0_6px_rgba(6,182,212,0.6)]' : 'text-slate-600'}`}>
                                    <span style={{ display: 'inline-block', transform: `rotate(${arrowRotation}deg)` }}>↑</span>
                                  </div>
                                ) : <span className="text-slate-700 text-[10px]">-</span>}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {activeTab === 'RAIN' && (
              <div className="space-y-3">
                <div className="flex justify-between items-center text-xs text-slate-400">
                  <span>สัดส่วนสถานีปลอดฝน (-) แยก 4 ภาค</span>
                  <span>เกณฑ์ผ่านภาพรวม &ge; 60% (คิดจาก 99 สถานี)</span>
                </div>

                <div className="space-y-2.5">
                  {statsWithStreak.map(d => {
                    if (d.pctFreeR === null) return null;
                    return (
                      <div key={d.day} className="flex flex-col sm:flex-row sm:items-center gap-2 text-xs py-2 px-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
                        <span className="w-12 text-slate-300 font-mono font-bold shrink-0">{d.day} ต.ค.</span>
                        <div className="flex items-center gap-2 text-[11px] flex-1">
                          <span className="px-2 py-0.5 rounded bg-slate-900 text-slate-300">เหนือ: <b className="text-cyan-400">{d.regRain.N}%</b></span>
                          <span className="px-2 py-0.5 rounded bg-slate-900 text-slate-300">อีสาน: <b className="text-cyan-400">{d.regRain.NE}%</b></span>
                        </div>
                        <div className="flex items-center gap-2 shrink-0 w-56 justify-end">
                          <div className="w-24 h-3 bg-slate-800 rounded-full overflow-hidden flex">
                            <div className={`h-full ${d.iconPassR ? 'bg-emerald-500' : 'bg-amber-400'}`} style={{ width: `${d.pctFreeR}%` }} />
                          </div>
                          <span className={`font-mono font-bold w-16 text-right ${d.iconPassR ? 'text-emerald-400' : 'text-slate-400'}`}>{d.pctFreeR}%</span>
                          <span className="text-[10px]">{d.iconPassR ? '✅' : '❌'}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

          </div>

        </div>
      );
    }

    ReactDOM.render(<App />, document.getElementById('root'));
  </script>
</body>
</html>
"""

# เขียนข้อมูลลงใน index.html ทันที
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html_template)

print("อัปเดตเกณฑ์อุณหภูมิเป็น < 23.0 และสร้าง index.html สำเร็จแล้ว!")
