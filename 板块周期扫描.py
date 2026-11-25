#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""板块周期扫描 + 可视化工作台。

出生证明：
  为什么建 = 2026-11-25 用户指出"只看科技和红利"视野窄；且要"3-5 年长周期"和"可视化工作台定期更新"。
  谁消费 = 用户直接看 `板块周期工作台.html`；`板块周期扫描_YYYYMMDD.csv` 供复盘引用。
  退役条件 = 若板块轮动不再作为决策依据，转归档。

输出：
  - 板块周期扫描_YYYYMMDD.csv（31 个申万 L1 行业指标）
  - 板块周期工作台.html（ECharts 可视化，双击打开）

口径：
  - 数据：Tushare `sw_daily` 申万一级行业指数，20210101 起
  - 近N年 = 收盘价 / N 年前收盘 - 1
  - 距5年高 = 当前 / 近5年最高收盘 - 1
"""
import json
import datetime as dt
import pandas as pd
import tushare_utils as tu

pro = tu.get_pro()
TODAY = dt.date.today().strftime('%Y%m%d')
START = '20210101'
END = TODAY

idx = pro.index_classify(level='L1', src='SW2021')
rows, series = [], {}
for _, r in idx.iterrows():
    code, name = r['index_code'], r['industry_name']
    try:
        d = pro.sw_daily(ts_code=code, start_date=START, end_date=END)
        if d is None or len(d) < 500:
            continue
        d = d.sort_values('trade_date')
        c = d['close'].reset_index(drop=True)
        n = len(c)
        r5 = c.iloc[-1] / c.iloc[0] - 1 if n >= 1100 else None
        r3 = c.iloc[-1] / c.iloc[-750] - 1 if n >= 750 else None
        r1 = c.iloc[-1] / c.iloc[-250] - 1 if n >= 250 else None
        dd5 = c.iloc[-1] / c.max() - 1
        rows.append(dict(行业=name, 近5年=r5, 近3年=r3, 近1年=r1, 距5年高=dd5,
                        日期=d['trade_date'].iloc[-1], 收盘=float(c.iloc[-1])))
        # 归一化净值（以 5 年前为 1）
        base = c.iloc[0]
        step = max(1, n // 240)
        series[name] = [[d['trade_date'].iloc[i], round(float(c.iloc[i] / base), 4)]
                        for i in range(0, n, step)]
    except Exception:
        continue

df = pd.DataFrame(rows).sort_values('近3年', ascending=False)
df.to_csv(f'板块周期扫描_{TODAY}.csv', index=False, encoding='utf-8-sig')
print(df.round(4).to_string(index=False))
print(f'\n已保存 板块周期扫描_{TODAY}.csv（{len(df)} 个行业）')

# ---------- 生成 HTML 工作台 ----------
payload = {
    'date': df['日期'].iloc[0] if len(df) else TODAY,
    'cat': df['行业'].tolist(),
    'r5': [None if pd.isna(x) else round(x * 100, 2) for x in df['近5年']],
    'r3': [None if pd.isna(x) else round(x * 100, 2) for x in df['近3年']],
    'r1': [None if pd.isna(x) else round(x * 100, 2) for x in df['近1年']],
    'dd5': [None if pd.isna(x) else round(x * 100, 2) for x in df['距5年高']],
    'series': series,
}

html = '''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>板块周期工作台</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
body{font-family:-apple-system,"PingFang SC",sans-serif;background:#0f1115;color:#d7dae0;margin:0;padding:10px;-webkit-text-size-adjust:100%}
h2{font-size:16px;margin:8px 0 4px}
.wrap{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.card{background:#171a21;border-radius:10px;padding:10px}
#chart1,#chart2{height:420px}
#chart3{height:460px}
.sub{color:#8a919e;font-size:12px;margin-bottom:6px}
table{width:100%;border-collapse:collapse;font-size:12px}
th,td{padding:4px 6px;border-bottom:1px solid #242833;text-align:right}
th:first-child,td:first-child{text-align:left}
@media(max-width:820px){.wrap{grid-template-columns:1fr}body{padding:8px}h2{font-size:15px}#chart1,#chart2{height:320px}#chart3{height:360px}table{font-size:11px}th,td{padding:3px 4px}.card{padding:8px}}
</style></head><body>
<h2>板块周期工作台 <span class="sub">数据日：__DATE__ ｜ 申万一级 31 行业 ｜ 自动生成</span></h2>
<div class="wrap">
  <div class="card"><div class="sub">① 近5年 / 近3年 / 近1年 涨幅（%）</div><div id="chart1"></div></div>
  <div class="card"><div class="sub">② 距5年高回撤（%，越靠右越接近高点）</div><div id="chart2"></div></div>
</div>
<div class="card" style="margin-top:14px"><div class="sub">③ 归一化净值（2021-01-01 = 1）——勾选对比</div><div id="chart3"></div></div>
<div class="card" style="margin-top:14px"><div class="sub">④ 明细表</div><div id="tbl"></div></div>
<script>
const D = __DATA__;
const dark={backgroundColor:'transparent',textStyle:{color:'#d7dae0'},
 axisLine:{lineStyle:{color:'#3a3f4b'}},splitLine:{lineStyle:{color:'#242833'}}};
// ① 三周期柱状
const c1=echarts.init(document.getElementById('chart1'),null,{renderer:'canvas'});
c1.setOption({tooltip:{trigger:'axis'},legend:{data:['近5年','近3年','近1年'],textStyle:{color:'#d7dae0'}},
 grid:{left:80,right:20,top:40,bottom:60},
 xAxis:{type:'category',data:D.cat,axisLabel:{rotate:60,fontSize:10}},
 yAxis:{type:'value',name:'%'},...dark,
 series:[
  {name:'近5年',type:'bar',data:D.r5,itemStyle:{color:'#4c78a8'}},
  {name:'近3年',type:'bar',data:D.r3,itemStyle:{color:'#f58518'}},
  {name:'近1年',type:'bar',data:D.r1,itemStyle:{color:'#54a24b'}}]});
// ② 距高
const c2=echarts.init(document.getElementById('chart2'));
const sorted=D.cat.map((n,i)=>[n,D.dd5[i]]).sort((a,b)=>b[1]-a[1]);
c2.setOption({tooltip:{trigger:'axis'},grid:{left:80,right:30,top:20,bottom:60},...dark,
 xAxis:{type:'category',data:sorted.map(x=>x[0]),axisLabel:{rotate:60,fontSize:10}},
 yAxis:{type:'value',name:'%',max:0},
 series:[{type:'bar',data:sorted.map(x=>x[1]),itemStyle:{color:'#e45756'}}]});
// ③ 净值
const names=Object.keys(D.series);
const c3=echarts.init(document.getElementById('chart3'));
const legendSel={}; names.forEach(n=>legendSel[n]=['通信','电子','银行','食品饮料','医药生物','房地产'].includes(n));
c3.setOption({tooltip:{trigger:'axis'},legend:{type:'scroll',data:names,selected:legendSel,textStyle:{color:'#d7dae0'},top:0},
 grid:{left:60,right:20,top:50,bottom:40},...dark,
 xAxis:{type:'category'},yAxis:{type:'value',name:'净值'},
 series:names.map(n=>({name:n,type:'line',showSymbol:false,data:D.series[n],lineStyle:{width:1.4}}))});
window.addEventListener('resize',()=>{c1.resize();c2.resize();c3.resize();});
// ④ 表格
let html='<table><tr><th>行业</th><th>近5年%</th><th>近3年%</th><th>近1年%</th><th>距5年高%</th></tr>';
for(let i=0;i<D.cat.length;i++){html+=`<tr><td>${D.cat[i]}</td><td>${D.r5[i]??'-'}</td><td>${D.r3[i]??'-'}</td><td>${D.r1[i]??'-'}</td><td>${D.dd5[i]??'-'}</td></tr>`;}
document.getElementById('tbl').innerHTML=html+'</table>';
</script></body></html>'''
html = html.replace('__DATE__', payload['date']).replace('__DATA__', json.dumps(payload, ensure_ascii=False))
open('板块周期工作台.html', 'w', encoding='utf-8').write(html)
print('已生成 板块周期工作台.html（浏览器打开即可）')
