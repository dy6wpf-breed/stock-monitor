# -*- coding: utf-8 -*-
"""
股票盈利监控系统 - GitHub Actions v8.2 (三账户全齐：电建 40.24 万股)
"""

import requests
import os
from datetime import datetime, timedelta

# ================== 💰 核心财务基准 ==================
REALIZED_PROFIT = 609633 

# ================== 📌 持仓配置 (三账户对齐) ==================
STOCKS = {
    '601669': {'name': '中国电建', 'prefix': 'sh', 'holdings': {
        '中信建投': {'shares': 191600, 'cost': 5.938}, 
        '国信证券': {'shares': 209300, 'cost': 5.963},
        '东方财富': {'shares': 1500,   'cost': 6.073}  # <-- 新增
    }}
}

# ================== 📱 推送逻辑 ==================
def send_wechat(title, content):
    key = os.getenv("SERVERCHAN_KEY") or "sctp19090tnwug12v5ljfqyvsgugxfrv"
    url = f"https://19090.push.ft07.com/send/{key}.send" if key.startswith("sctp") else f"https://sctapi.ftqq.com/{key}"
    try:
        requests.post(url, data={'title': title, 'desp': content}, timeout=15)
    except: pass

# ================== 🌐 获取行情逻辑 ==================
def get_stock_data(code, prefix):
    url = f"http://qt.gtimg.cn/q={prefix}{code}"
    try:
        res = requests.get(url, timeout=10)
        data = res.text.split('~')
        if len(data) > 32:
            return float(data[3]), float(data[4]), float(data[32])
    except: pass
    return 0.0, 0.0, 0.0

# ================== 📊 核心计算逻辑 ==================
def calc_profit():
    price_now, price_last, pct = get_stock_data('601669', 'sh')
    if price_now == 0: return None
    
    cfg = STOCKS['601669']['holdings']
    zx, gx, df = cfg['中信建投'], cfg['国信证券'], cfg['东方财富']
    
    zx_prof = zx['shares'] * (price_now - zx['cost'])
    gx_prof = gx['shares'] * (price_now - gx['cost'])
    df_prof = df['shares'] * (price_now - df['cost'])
    
    total_shares = zx['shares'] + gx['shares'] + df['shares']
    total_mv = total_shares * price_now
    total_floating = zx_prof + gx_prof + df_prof
    final_total_profit = total_floating + REALIZED_PROFIT
    daily_change = (price_now - price_last) * total_shares

    content = f"""
## 💰 账户资产概览 (GitHub v8.2)
- **总损益 (含落袋)**: **{final_total_profit:+,.2f}** 元
- **持仓总市值**: **{total_mv:,.0f}** 元
- **今日总变动**: **{daily_change:+,.2f}** 元 ({pct:+.2f}%)

> **资产明细**
- 历史落袋盈亏: `{REALIZED_PROFIT:+,.0f}`
- 现有持仓浮盈: `{total_floating:+,.0f}`

---
## 👜 分账户对账
- **中信建投**: `{zx_prof:+,.0f}` ({zx['shares']:,}股)
- **国信证券**: `{gx_prof:+,.0f}` ({gx['shares']:,}股)
- **东方财富**: `{df_prof:+,.0f}` ({df['shares']:,}股)

📅 同步时间: {(datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')}
"""
    return final_total_profit, daily_change, content

if __name__ == "__main__":
    result = calc_profit()
    if result:
        tot, day, body = result
        send_wechat(f"🚀 资产日报: {tot:+,.0f} | 变动 {day:+,.0f}", body)
