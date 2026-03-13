# -*- coding: utf-8 -*-
"""
股票盈利监控系统 - GitHub Actions v5.0 (大唐清仓/换仓爱尔+中化)
"""

import requests
import os
from datetime import datetime, timedelta

# ================== 💰 已落袋收益统计 (大唐发电清仓后) ==================
# 1. 历史落袋: 138,576
# 2. 大唐发电清仓盈利: +625,941
REALIZED_PROFIT = 764517 

# ================== 📌 现有持仓配置 ==================
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
    # === 新成员: 爱尔眼科 (创业板 sz) ===
    '300015': {'name': '爱尔眼科', 'prefix': 'sz', 'holdings': {
        '国信证券': {'shares': 5900,   'cost': 10.190}
    }},
    # === 新成员: 中化国际 (沪市 sh) ===
    '600500': {'name': '中化国际', 'prefix': 'sh', 'holdings': {
        '中信建投': {'shares': 84200,  'cost': 4.973},
        '国信证券': {'shares': 41200,  'cost': 4.970}
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
            f"- **当前浮盈**: `{profit:+,.0f}` ({ (profit/cost*100):+.2f}%)\n"
            f"- **今日变动**: `{daily:+,.0f}` ({pct:+.2f}%)\n"
            f"- **行情**: 现价 `{price:.2f}` / 成本 `{cost/shares:.3f}`\n\n"
        )

    return stock_details, holdings_profit + REALIZED_PROFIT, total_today_profit, holdings_profit

# ================== 🏁 主程序 ==================
if __name__ == "__main__":
    details, final_tot, day_prof, float_prof = calc_profit()
    time_str = (datetime.utcnow() + timedelta(hours=8)).strftime('%m-%d %H:%M')
    
    title = f"📈 换仓日报: {final_tot:+,.0f} | 盈: {final_tot-764247:+,.0f}" # 这里的盈是以昨日总额为基准
    content = f"""
## 📊 账户核心概览
- **总盈亏 (含落袋)**: **{final_tot:+,.2f}** 元
- **今日浮动变动**: **{day_prof:+,.2f}** 元
- 历史落袋总额: {REALIZED_PROFIT:+,.0f} 元

---
## 👜 新持仓清单
{''.join(details)}

📅 生成时间: {time_str}
    """
    send_wechat(title, content)
