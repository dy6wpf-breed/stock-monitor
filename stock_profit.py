# -*- coding: utf-8 -*-
"""
股票盈利监控系统 - GitHub Actions v7.3 (精准对账对齐版)
(修正：总持仓 40.09 万股，成本对齐最新截图)
"""

import requests
import os
from datetime import datetime, timedelta

# ================== 💰 已落袋收益统计 ==================
# 包含历次清仓损益：大唐(+77.4万)、全聚德(-3.7万)、中铁(-3.2万)、中化(-9.4万)等
REALIZED_PROFIT = 609633 

# ================== 📌 现有持仓配置 (依据最新截图精准修正) ==================
STOCKS = {
    '601669': {'name': '中国电建', 'prefix': 'sh', 'holdings': {
        '中信建投': {'shares': 191600, 'cost': 5.938}, 
        '国信证券': {'shares': 209300, 'cost': 5.963}
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

# ================== 📊 计算盈利 ==================
def calc_profit():
    stock_details = [] 
    holdings_cost = 0
    holdings_profit = 0
    total_today_profit = 0
    total_market_value = 0
    
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
        total_market_value += value

        emoji = "🔺" if daily >= 0 else "🔹"
        stock_details.append(
            f"### {emoji} {cfg['name']} ({code})\n"
            f"- **当前盈亏**: `{profit:+,.0f}` ({ (profit/cost*100):+.2f}%)\n"
            f"- **今日变动**: `{daily:+,.0f}` ({pct:+.2f}%)\n"
            f"- **价格信息**: 现价 `{price:.3f}` / 摊薄成本 `{cost/shares:.3f}`\n"
            f"- **最新规模**: `{shares:,}` 股 / `{value:,.0f}` 元\n\n"
        )

    return stock_details, holdings_profit + REALIZED_PROFIT, total_today_profit, holdings_profit, total_market_value

# ================== 🏁 主程序 ==================
if __name__ == "__main__":
    details, final_tot, day_prof, float_prof, total_mv = calc_profit()
    time_str = (datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')
    
    # 标题显示总盈亏
    title = f"📈 修正日报: {final_tot:+,.0f} | 今日 {day_prof:+,.0f}"
    
    content = f"""
## 💰 账户资产概览 (修正版)
- **总损益 (含落袋)**: **{final_tot:+,.2f}** 元
- **持仓总市值**: **{total_mv:,.0f}** 元
- **今日总变动**: **{day_prof:+,.2f}** 元

> **明细拆解**
- 历史已实现收益: `{REALIZED_PROFIT:+,.0f}`
- 现有持仓浮动: `{float_prof:+,.0f}`

---
## 👜 现有持仓清单
{''.join(details)}

📅 数据同步时间: {time_str}
    """
    send_wechat(title, content)
