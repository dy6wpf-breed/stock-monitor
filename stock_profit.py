# -*- coding: utf-8 -*-
"""
股票盈利监控系统 - GitHub Actions v7.0 (极致孤注一掷：全仓电建版)
"""

import requests
import os
from datetime import datetime, timedelta

# ================== 💰 已落袋收益统计 ==================
# 包含历次清仓损益，本次扣除中化国际全额割肉约 9.47 万
REALIZED_PROFIT = 609633 

# ================== 📌 现有持仓配置 (极致集中) ==================
STOCKS = {
    '601669': {'name': '中国电建', 'prefix': 'sh', 'holdings': {
        '中信建投': {'shares': 191600, 'cost': 5.938}, 
        '国信证券': {'shares': 145700, 'cost': 5.951},
        '东方财富': {'shares': 1500,   'cost': 6.070}
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
            f"- **当前浮盈**: `{profit:+,.0f}` ({ (profit/cost*100):+.2f}%)\n"
            f"- **今日变动**: `{daily:+,.0f}` ({pct:+.2f}%)\n"
            f"- **价格**: `{price:.2f}` / 摊薄成本 `{cost/shares:.3f}`\n\n"
        )

    return stock_details, holdings_profit + REALIZED_PROFIT, total_today_profit, holdings_profit

if __name__ == "__main__":
    details, final_tot, day_prof, float_prof = calc_profit()
    time_str = (datetime.utcnow() + timedelta(hours=8)).strftime('%m-%d %H:%M')
    
    title = f"📈 绝地反击: {final_tot:+,.0f} | 今日 {day_prof:+,.0f}"
    content = f"""
## 📊 极致持仓概览
- **总盈亏 (含落袋)**: **{final_tot:+,.2f}** 元
- **持仓总市值**: { (final_tot - REALIZED_PROFIT + sum(sum(h['shares']*h['cost'] for h in v['holdings'].values()) for v in STOCKS.values())):+,.0f} 元
- 累计落袋收益: {REALIZED_PROFIT:+,.0f} 元

---
## 👜 现有持仓清单 (全仓电建)
{''.join(details)}

📅 更新时间: {time_str}
    """
    send_wechat(title, content)
