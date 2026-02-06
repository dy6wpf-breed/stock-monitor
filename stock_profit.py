# -*- coding: utf-8 -*-
"""
股票盈利监控系统 - GitHub Actions (全聚德建仓版)
"""

import requests
import os
from datetime import datetime, timedelta

# ================== 💰 已落袋收益 ==================
# 1. 人保(第1波): +32,942
# 2. 中航机载: +1,491
# 3. 晋控电力: -1,306
# 4. 新筑股份: -5,113 (成本6.32+，卖出6.25)
REALIZED_PROFIT = 28014 

# ================== 📌 现有持仓配置 ==================
STOCKS = {
    # 1. 大唐发电 (保持截图修正后的成本)
    '601991': {'name': '大唐发电', 'prefix': 'sh', 'holdings': {
        '中信': {'shares': 186700, 'cost': 3.217},
        '国信': {'shares': 43300, 'cost': 3.452},
        '东方': {'shares': 163600, 'cost': 2.871}
    }},
    
    # 2. 中国人保 (保持不变)
    '601319': {'name': '中国人保', 'prefix': 'sh', 'holdings': {
        '中信': {'shares': 9900, 'cost': 9.181},
        '国信': {'shares': 9500, 'cost': 9.281},
        '东方': {'shares': 1100, 'cost': 9.205}
    }},

    # 3. 全聚德 (新买入，00开头属深市 sz)
    '002186': {'name': '全聚德', 'prefix': 'sz', 'holdings': {
        '买入1': {'shares': 17000, 'cost': 12.25},
        '买入2': {'shares': 19300, 'cost': 12.25}
    }}
}

# ================== 📱 Server 酱推送 ==================
def send_wechat(title, content):
    key = os.getenv("SERVERCHAN_KEY")
    if not key:
        print("❌ 未设置 SERVERCHAN_KEY")
        return
    url = f"https://sctapi.ftqq.com/{key}.send"
    try:
        requests.post(url, data={'title': title, 'desp': content})
        print("✅ 微信推送成功")
    except Exception as e:
        print(f"❌ 推送失败: {e}")

# ================== 🌐 获取股价 ==================
def get_stock_data(code, prefix):
    try:
        url = f"http://qt.gtimg.cn/q={prefix}{code}"
        res = requests.get(url, timeout=10)
        data = res.text.split('~')
        if len(data) > 4:
            return float(data[3]), float(data[4]) # 现价, 昨收
    except:
        pass
    return 0.0, 0.0

# ================== 📊 计算盈利 ==================
def calc_profit():
    stock_details = [] 
    holdings_cost = 0   # 现有持仓成本
    holdings_profit = 0 # 现有持仓浮盈
    total_today_profit = 0
    
    for code, cfg in STOCKS.items():
        # 1. 持仓数据
        holdings = cfg['holdings']
        shares = sum(h['shares'] for h in holdings.values())
        cost = sum(h['shares'] * h['cost'] for h in holdings.values())
        
        # 2. 实时股价
        price, yesterday_price = get_stock_data(code, cfg['prefix'])
        if price == 0: continue

        # 3. 计算单只数据
        value = shares * price
        profit = value - cost
        profit_rate = (profit / cost) * 100 if cost else 0
        
        today_diff = price - yesterday_price
        today_profit = today_diff * shares
        today_pct = (today_diff / yesterday_price) * 100 if yesterday_price else 0

        # 4. 累加
        holdings_cost += cost
        holdings_profit += profit
        total_today_profit += today_profit

        # 5. 格式化输出
        emoji = "🔴" if today_profit >= 0 else "🟢"
        stock_details.append(
            f"{emoji} **{cfg['name']}**\n"
            f"- 累计盈利: `{profit:+,.0f}` ({profit_rate:+.2f}%)\n"
            f"- 当日盈亏: `{today_profit:+,.0f}`\n"
            f"- 现价: {price:.2f} ({today_pct:+.2f}%)\n"
            f"- 持仓: {shares:,}\n\n"
        )

    # === 核心逻辑：总收益 = 现有持仓浮盈 + 已落袋收益 ===
    final_total_profit = holdings_profit + REALIZED_PROFIT
    
    # 现有持仓收益率
    current_yield = (holdings_profit / holdings_cost * 100) if holdings_cost else 0

    return stock_details, final_total_profit, holdings_profit, current_yield, total_today_profit

# ================== 🏁 主程序 ==================
if __name__ == "__main__":
    details, final_tot, float_prof, yield_rate, day_prof = calc_profit()
    
    time_str = (datetime.utcnow() + timedelta(hours=8)).strftime('%m-%d %H:%M')
    
    # 标题
    title = f"📊 账户日报 | 总{final_tot:+,.0f} | 今日{day_prof:+,.0f}"
    
    # 内容
    content = f"""
📅 {time_str}

💰 **资金总览**
- **账户总盈亏: {final_tot:+,.0f} 元** (含落袋)
- 现有持仓浮盈: {float_prof:+,.0f} 元
- 现有持仓收益率: {yield_rate:+.2f}%
- 今日浮动盈亏: {day_prof:+,.0f} 元

👜 **已落袋收益 (+{REALIZED_PROFIT:,})**
- 人保(1波)/中航: 赚
- 晋控/新筑: 亏

---
{''.join(details)}
    """
    
    print(content)
    send_wechat(title, content)
