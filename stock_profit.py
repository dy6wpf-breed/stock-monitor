# -*- coding: utf-8 -*-
"""
股票盈利监控系统 - GitHub Actions 无状态优化版 (人保清仓，加仓新筑)
"""

import requests
import os
from datetime import datetime, timedelta

# ================== 📌 股票配置 ==================
STOCKS = {
    '601991': {'name': '大唐发电', 'prefix': 'sh', 'holdings': {
        '中信': {'shares': 186700, 'cost': 3.272},
        '国信': {'shares': 43300, 'cost': 3.507},
        '东方': {'shares': 163600, 'cost': 2.926}
    }},
    '000767': {'name': '晋控电力', 'prefix': 'sz', 'holdings': {
        '中信': {'shares': 30100, 'cost': 2.998},
        '国信': {'shares': 11600, 'cost': 3.042}
    }},
    # === 中国人保已清仓 ===
    
    # === 新筑股份 (含加仓) ===
    '002480': {'name': '新筑股份', 'prefix': 'sz', 'holdings': {
        '底仓1': {'shares': 16000, 'cost': 6.290},
        '底仓2': {'shares': 16100, 'cost': 6.300},
        '加仓1': {'shares': 18700, 'cost': 6.350},
        '加仓2': {'shares': 17400, 'cost': 6.350}
    }}
}

# ================== 📱 Server 酱推送 ==================
def send_wechat(title, content):
    # GitHub Actions 中需在 Settings -> Secrets 配置 SERVERCHAN_KEY
    key = os.getenv("SERVERCHAN_KEY")
    if not key:
        print("❌ 未设置 SERVERCHAN_KEY，跳过推送")
        return
    url = f"https://sctapi.ftqq.com/{key}.send"
    try:
        data = {'title': title, 'desp': content}
        res = requests.post(url, data=data)
        if res.status_code == 200:
            print("✅ 微信推送成功")
        else:
            print(f"❌ 推送失败: {res.text}")
    except Exception as e:
        print(f"❌ 发送微信出错: {e}")

# ================== 🌐 获取股价数据 ==================
def get_stock_data(code, prefix):
    """
    返回: (当前价格, 昨日收盘价)
    """
    url = f"http://qt.gtimg.cn/q={prefix}{code}"
    try:
        res = requests.get(url, timeout=10)
        res.encoding = 'gbk'
        # 数据格式: 名字~代码~当前价~昨收~开盘~成交量...
        # 索引: 0:未知, 1:名字, 2:代码, 3:当前价, 4:昨收价
        data = res.text.split('~')
        if len(data) > 4:
            current_price = float(data[3])
            yesterday_close = float(data[4])
            return current_price, yesterday_close
    except Exception as e:
        print(f"获取 {code} 失败: {e}")
    return 0.0, 0.0

# ================== 📊 计算盈利 ==================
def calc_profit():
    stock_details = [] 
    total_cost = 0
    total_profit = 0
    total_today_profit = 0
    
    for code, cfg in STOCKS.items():
        # 1. 计算持仓
        holdings = cfg['holdings']
        shares = sum(h['shares'] for h in holdings.values())
        cost = sum(h['shares'] * h['cost'] for h in holdings.values())
        
        # 2. 获取行情
        price, yesterday_price = get_stock_data(code, cfg['prefix'])
        
        if price == 0: 
            stock_details.append(f"⚠️ **{cfg['name']}** 获取数据失败\n")
            continue

        # 3. 计算指标
        value = shares * price
        profit = value - cost
        profit_rate = (profit / cost) * 100 if cost else 0
        
        today_diff = price - yesterday_price
        today_profit = today_diff * shares
        today_pct = (today_diff / yesterday_price) * 100 if yesterday_price else 0

        # 4. 汇总
        total_cost += cost
        total_profit += profit
        total_today_profit += today_profit

        # 5. 生成单只股票文本
        emoji = "🔴" if today_profit >= 0 else "🟢"
        
        detail = (
            f"{emoji} **{cfg['name']}**\n"
            f"- 累计盈利: `{profit:+,.0f}` ({profit_rate:+.2f}%)\n"
            f"- 当日盈亏: `{today_profit:+,.0f}`\n"
            f"- 现价/昨收: {price:.2f} / {yesterday_price:.2f}\n"
            f"- 今日涨跌: {today_diff:+.2f} ({today_pct:+.2f}%)\n"
            f"- 持仓/成本: {shares:,} / {cost/shares:.3f}\n"
            f"\n"
        )
        stock_details.append(detail)

    # 计算总指标
    total_rate = (total_profit / total_cost) * 100 if total_cost else 0
    total_today_rate = (total_today_profit / total_cost) * 100 if total_cost else 0

    return stock_details, total_profit, total_rate, total_today_profit, total_today_rate

# ================== 🏁 主程序 ==================
if __name__ == "__main__":
    print("🔍 开始计算...")
    
    details, tot_prof, tot_rate, day_prof, day_rate = calc_profit()
    
    beijing_time = (datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')
    
    title = f"📊 盈亏日报 | 总{tot_prof:+,.0f} | 今日{day_prof:+,.0f}"
    
    content = f"""
📅 {beijing_time}

🔥 **账户总览**
- 累计总盈亏: **{tot_prof:+,.2f}** 元
- 累计收益率: **{tot_rate:+.2f}%**
- 今日总盈亏: **{day_prof:+,.2f}** 元
- 今日收益率: **{day_rate:+.2f}%**

---
{''.join(details)}
    """
    
    print(content)
    send_wechat(title, content)
