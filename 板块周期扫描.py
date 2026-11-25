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

# 一级 31 个 + 二级重点（用户 2026-11-25 要求：芯片/PCB/消费电子要分开看）
L1 = pro.index_classify(level='L1', src='SW2021')
L2_ALL = pro.index_classify(level='L2', src='SW2021')
L2_KEEP = ['半导体','元件','消费电子','光学光电子','电子化学品Ⅱ','通信设备','计算机设备',
           '软件开发','IT服务Ⅱ','电网设备','光伏设备','电池','风电设备','医疗器械',
           '医疗服务','化学制药','中药Ⅱ','白酒Ⅱ','食品加工','饮料乳品','银行','保险Ⅱ',
           '证券Ⅱ','房地产','建筑装饰','汽车零部件','通用设备','自动化设备','军工电子Ⅱ','航空装备Ⅱ']
idx = pd.concat([
    L1.assign(level_tag='一级'),
    L2_ALL[L2_ALL['industry_name'].isin(L2_KEEP)].assign(level_tag='二级')
], ignore_index=True)
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
        rows.append(dict(层级=r['level_tag'], 行业=name.replace('Ⅱ',''), 近5年=r5, 近3年=r3, 近1年=r1, 距5年高=dd5,
                        日期=d['trade_date'].iloc[-1], 收盘=float(c.iloc[-1])))
        # 归一化净值（以 5 年前为 1）
        base = c.iloc[0]
        step = max(1, n // 240)
        series[name] = [[d['trade_date'].iloc[i], round(float(c.iloc[i] / base), 4)]
                        for i in range(0, n, step)]
    except Exception:
        continue

df = pd.DataFrame(rows).sort_values(['层级','近3年'], ascending=[True,False])
df.to_csv(f'板块周期扫描_{TODAY}.csv', index=False, encoding='utf-8-sig')
print(df.round(4).to_string(index=False))
print(f'\n已保存 板块周期扫描_{TODAY}.csv（{len(df)} 个行业）')

# ---------- 生成 HTML 工作台 ----------
l1 = df[df['层级']=='一级'].copy()
l2 = df[df['层级']=='二级'].copy()

def pack(d):
    return dict(cat=d['行业'].tolist(),
                r5=[None if pd.isna(x) else round(x*100,2) for x in d['近5年']],
                r3=[None if pd.isna(x) else round(x*100,2) for x in d['近3年']],
                r1=[None if pd.isna(x) else round(x*100,2) for x in d['近1年']],
                dd5=[None if pd.isna(x) else round(x*100,2) for x in d['距5年高']])

payload = {'date': df['日期'].iloc[0] if len(df) else TODAY,
           'l1': pack(l1), 'l2': pack(l2), 'series': series}

html = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>板块周期工作台</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
body{font-family:-apple-system,"PingFang SC",sans-serif;background:#0f1115;color:#d7dae0;margin:0;padding:10px}
h2{font-size:15px;margin:6px 0 2px}
h3{font-size:13px;margin:0 0 6px;color:#9aa3b2}
.card{background:#171a21;border-radius:10px;padding:10px;margin-bottom:12px}
.chart{height:520px}
.chart-sm{height:420px}
.sub{color:#8a919e;font-size:11px}
table{width:100%;border-collapse:collapse;font-size:11px}
th,td{padding:3px 5px;border-bottom:1px solid #242833;text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left}
.tabs{display:flex;gap:6px;margin-bottom:8px}
.tab{padding:4px 10px;border-radius:6px;background:#222733;font-size:12px;cursor:pointer}
.tab.on{background:#3a6ea5}
</style></head><body>
<h2>板块周期工作台 <span class="sub">数据日 __DATE__</span></h2>

<div class="card"><h3>一级行业（31）· 近5/3/1年涨幅</h3><div id="c1" class="chart"></div></div>
<div class="card"><h3>一级行业 · 距5年高回撤</h3><div id="c2" class="chart-sm"></div></div>
<div class="card"><h3>二级行业（27）· 近5/3/1年涨幅</h3><div id="c3" class="chart"></div></div>
<div class="card"><h3>二级行业 · 距5年高回撤</h3><div id="c4" class="chart-sm"></div></div>
<div class="card"><h3>归一化净值（2021-01-01 = 1）</h3><div id="c5" class="chart"></div></div>
<div class="card"><h3>明细表</h3><div id="tbl"></div></div>

<script>
const D = __DATA__;
const AX={axisLine:{lineStyle:{color:'#3a3f4b'}},axisLabel:{color:'#9aa3b2',fontSize:10},splitLine:{lineStyle:{color:'#242833'}}};
function hbar(id,obj){
  const c=echarts.init(document.getElementById(id));
  const data=obj.cat.map((n,i)=>({name:n, r5:obj.r5[i], r3:obj.r3[i], r1:obj.r1[i]}));
  data.sort((a,b)=>(b.r3??-999)-(a.r3??-999));
  c.setOption({tooltip:{trigger:'axis',axisPointer:{type:'shadow'}},legend:{data:['近5年','近3年','近1年'],textStyle:{color:'#d7dae0'},top:0},
    grid:{left:70,right:40,top:34,bottom:20},
    xAxis:{type:'value',name:'%',...AX},
    yAxis:{type:'category',data:data.map(d=>d.name),axisLabel:{color:'#c9ced8',fontSize:11},...AX},
    series:[
      {name:'近5年',type:'bar',data:data.map(d=>d.r5),itemStyle:{color:'#4c78a8'}},
      {name:'近3年',type:'bar',data:data.map(d=>d.r3),itemStyle:{color:'#f58518'}},
      {name:'近1年',type:'bar',data:data.map(d=>d.r1),itemStyle:{color:'#54a24b'}}]});
  return c;
}
function dbar(id,obj){
  const c=echarts.init(document.getElementById(id));
  const data=obj.cat.map((n,i)=>({name:n,dd:obj.dd5[i]})).sort((a,b)=>(b.dd??-999)-(a.dd??-999));
  c.setOption({tooltip:{trigger:'axis'},grid:{left:70,right:40,top:10,bottom:20},
    xAxis:{type:'value',name:'%',max:0,...AX},
    yAxis:{type:'category',data:data.map(d=>d.name),axisLabel:{color:'#c9ced8',fontSize:11},...AX},
    series:[{type:'bar',data:data.map(d=>d.dd),itemStyle:{color:'#e45756'}}]});
  return c;
}
const c1=hbar('c1',D.l1), c2=dbar('c2',D.l1), c3=hbar('c3',D.l2), c4=dbar('c4',D.l2);
const names=Object.keys(D.series);
const c5=echarts.init(document.getElementById('c5'));
const sel={}; names.forEach(n=>sel[n]=['通信','电子','银行','食品饮料','医药生物','房地产','半导体','元件'].includes(n.replace('二级·','')));
c5.setOption({tooltip:{trigger:'axis'},legend:{type:'scroll',data:names,selected:sel,textStyle:{color:'#d7dae0'},top:0},
  grid:{left:60,right:20,top:40,bottom:20},
  xAxis:{type:'category',...AX},yAxis:{type:'value',name:'净值',...AX},
  series:names.map(n=>({name:n,type:'line',showSymbol:false,data:D.series[n],lineStyle:{width:1.3}}))});
window.addEventListener('resize',()=>{c1.resize();c2.resize();c3.resize();c4.resize();c5.resize();});
let h='<table><tr><th>行业</th><th>近5年%</th><th>近3年%</th><th>近1年%</th><th>距5年高%</th></tr>';
for(const g of [D.l1,D.l2]){for(let i=0;i<g.cat.length;i++){h+=`<tr><td>${g.cat[i]}</td><td>${g.r5[i]??'-'}</td><td>${g.r3[i]??'-'}</td><td>${g.r1[i]??'-'}</td><td>${g.dd5[i]??'-'}</td></tr>`;}}
document.getElementById('tbl').innerHTML=h+'</table>';
</script></body></html>"""
html = html.replace('__DATE__', payload['date']).replace('__DATA__', json.dumps(payload, ensure_ascii=False))
open('板块周期工作台.html', 'w', encoding='utf-8').write(html)
print('已生成 板块周期工作台.html（一级/二级分区，横向柱状图）')
