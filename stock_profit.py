# -*- coding: utf-8 -*-
"""
股票盈利监控系统 - GitHub Actions v6.0 (全仓换股电建版)
"""

import requests
import os
from datetime import datetime, timedelta

# ================== 💰 已落袋收益统计 (经本次大换仓核算) ==================
# 历史落袋: 764,517
# 减去: 人保割肉(-1.4万), 中铁割肉(-3.2万), 中化部分割肉(-1.4万)
# 加上: 爱尔眼科微利(+0.1万)
REALIZED_PROFIT = 705062 

# ================== 📌 现有持仓配置 (依据最新截图) ==================
STOCKS = {
    # 1. 中国电建 (目前的绝对核心)
    '601669': {'name': '中国电建', 'prefix': 'sh', 'holdings': {
        '中信建投': {'shares': 136500, 'cost': 5.953}, 
        '国信证券': {'shares': 100000, 'cost': 5.975}
    }},
    # 2. 中化国际 (剩余持仓)
    '600500': {'name': '中化国际', 'prefix': 'sh', 'holdings': {
        '中信建投': {'shares': 75000,  'cost': 5.128},
        '国信证券': {'shares': 62200,  'cost': 4.913}
    }},
    # 3. 中国人保 (东方财富还有极少量)
    '601319': {'name': '中国人保', 'prefix': 'sh', 'holdings': {
        '东方财富': {'shares': 1100,   'cost': 9.205}
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
    
    title = f"🚀 调仓完毕: {final_tot:+,.0f} | 现盈 {float_prof:+,.0f}"
    content = f"""
## 📊 账户大换仓概览
- **总盈亏 (含落袋)**: **{final_tot:+,.2f}** 元
- **持仓浮动变动**: **{day_prof:+,.2f}** 元
- 历史落袋收益: {REALIZED_PROFIT:+,.0f} 元

---
## 👜 当前重仓清单
{''.join(details)}

📅 生成时间: {time_str}
    """
    send_wechat(title, content)
