# -*- coding: utf-8 -*-
"""
股票盈利监控系统 - GitHub Actions v6.2 (人保全清/全仓电建最终版)
"""

import requests
import os
from datetime import datetime, timedelta

# ================== 💰 已落袋收益统计 ==================
# 包含历次清仓损益，本次扣除人保最后余仓割肉约 688 元
REALIZED_PROFIT = 704374 

# ================== 📌 现有持仓配置 ==================
STOCKS = {
    # 中国电建 (三账户全线持仓)
    '601669': {'name': '中国电建', 'prefix': 'sh', 'holdings': {
        '中信建投': {'shares': 136500, 'cost': 5.953}, 
        '国信证券': {'shares': 100000, 'cost': 5.975},
        '东方财富': {'shares': 1500,   'cost': 6.070}
    }},
    # 中化国际
    '600500': {'name': '中化国际', 'prefix': 'sh', 'holdings': {
        '中信建投': {'shares': 75000,  'cost': 5.128},
        '国信证券': {'shares': 62200,  'cost': 4.913}
    }}
}

# ================== 📱 Server 酱推送 ==================
def send_wechat(title, content):
    key = os.getenv("SERVERCHAN_KEY")
    if not key: return
    url = f"https://sctapi.ftqq.com/{key}.send"
    try:
        requests.post(url, data={'title': title, 'desp': content})
    except: pass

def get_stock_data(code, prefix):
    url = f"http://qt.gtimg.cn/q={prefix}{code}"
    try:
        res = requests.get(url, timeout=10)
        data = res.text.split('~')
        if len(data) > 32:
            return float(data[3]), float(data[4]), float(data[32])
    except: pass
    return 0.0, 0.0, 0.0

def calc_profit():
    stock_details = [] 
    holdings_cost = 0
    holdings_profit = 0
    total_today_profit = 0
    
    for code, cfg in STOCKS.items():
        shares = sum(h['shares'] for h in cfg['holdings'].values())
        cost = sum(h['shares'] * h['cost'] for h in cfg['holdings'].values())
        price, yesterday, pct = get_stock_data(code, cfg['prefix'])
        
        if price == 0: continue
        
        value = shares * price
        profit = value - cost
        daily = (price - yesterday) * shares
        
        holdings_cost += cost
        holdings_profit += profit
        total_today_profit += daily

        emoji = "🔺" if daily >= 0 else "🔹"
        stock_details.append(
            f"### {emoji} {cfg['name']} ({code})\n"
            f"- **当前盈亏**: `{profit:+,.0f}` ({ (profit/cost*100):+.2f}%)\n"
            f"- **今日变动**: `{daily:+,.0f}` ({pct:+.2f}%)\n"
            f"- **价格**: `{price:.2f}` / 成本 `{cost/shares:.3f}`\n\n"
        )

    return stock_details, holdings_profit + REALIZED_PROFIT, total_today_profit, holdings_profit

if __name__ == "__main__":
    details, final_tot, day_prof, float_prof = calc_profit()
    time_str = (datetime.utcnow() + timedelta(hours=8)).strftime('%m-%d %H:%M')
    
    title = f"🚀 全仓电建: {final_tot:+,.0f} | 盈 {final_tot-633053:+,.0f}"
    content = f"""
## 📊 账户最新概览
- **总盈亏 (含落袋)**: **{final_tot:+,.2f}** 元
- **今日总变动**: **{day_prof:+,.2f}** 元
- 现有浮动盈亏: {float_prof:+,.2f} 元
- 累计落袋收益: {REALIZED_PROFIT:+,.0f} 元

---
## 👜 现有持仓清单
{''.join(details)}

📅 更新时间: {time_str}
    """
    send_wechat(title, content)
