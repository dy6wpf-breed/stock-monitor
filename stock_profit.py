# -*- coding: utf-8 -*-
"""
股票盈利监控系统 - GitHub Actions v5.1 (补仓摊薄/新进中铁版)
"""

import requests
import os
from datetime import datetime, timedelta

# ================== 💰 已落袋收益统计 ==================
REALIZED_PROFIT = 764517 

# ================== 📌 现有持仓配置 (依据今日补仓成交更新) ==================
STOCKS = {
    '601319': {'name': '中国人保', 'prefix': 'sh', 'holdings': {
        '东方财富': {'shares': 1100,   'cost': 9.205},
        '中信建投': {'shares': 17600,  'cost': 8.918},
        '国信证券': {'shares': 21100,  'cost': 8.896}
    }},
    '601669': {'name': '中国电建', 'prefix': 'sh', 'holdings': {
        '中信建投': {'shares': 33300,  'cost': 5.731},
        '国信证券': {'shares': 37700,  'cost': 5.741}
    }},
    '300015': {'name': '爱尔眼科', 'prefix': 'sz', 'holdings': {
        '国信证券': {'shares': 15700,  'cost': 10.196} # 补仓摊平
    }},
    '600500': {'name': '中化国际', 'prefix': 'sh', 'holdings': {
        '中信建投': {'shares': 105000, 'cost': 4.939}, # 补仓摊平
        '国信证券': {'shares': 62200,  'cost': 4.913}  # 补仓摊平
    }},
    # === 新成员: 中国中铁 ===
    '601390': {'name': '中国中铁', 'prefix': 'sh', 'holdings': {
        '中信建投': {'shares': 60600,  'cost': 5.822},
        '国信证券': {'shares': 68300,  'cost': 5.835}
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
            f"- **行情**: 现价 `{price:.2f}` / 成本 `{cost/shares:.3f}`\n\n"
        )

    return stock_details, holdings_profit + REALIZED_PROFIT, total_today_profit, holdings_profit

# ================== 🏁 主程序 ==================
if __name__ == "__main__":
    details, final_tot, day_prof, float_prof = calc_profit()
    time_str = (datetime.utcnow() + timedelta(hours=8)).strftime('%m-%d %H:%M')
    
    title = f"📈 补仓日报: {final_tot:+,.0f} | 浮盈 {float_prof:+,.0f}"
    content = f"""
## 📊 账户核心概览
- **总盈亏 (含落袋)**: **{final_tot:+,.2f}** 元
- **今日浮动变动**: **{day_prof:+,.2f}** 元
- 累计落袋收益: {REALIZED_PROFIT:+,.0f} 元

---
## 👜 补仓后持仓清单
{''.join(details)}

📅 生成时间: {time_str}
    """
    send_wechat(title, content)
