# -*- coding: utf-8 -*-
"""
股票盈利监控系统 - GitHub Actions 版 - 修复当日营收计算逻辑
"""

import requests
import os
from datetime import datetime

# ================== 📌 股票配置 ==================
STOCKS = {
    '601991': {'name': '大唐发电', 'prefix': 'sh', 'holdings': {
        '中信': {'shares': 186700, 'cost': 3.272},
        '国信': {'shares': 43300, 'cost': 3.507},
        '东方': {'shares': 163600, 'cost': 2.926}
    }},
    '000767': {'name': '晋控电力', 'prefix': 'sz', 'holdings': {
        '中信': {'shares': 30100, 'cost': 2.998},
        '国信': {'shares': 29600, 'cost': 3.042}
    }},
    '601319': {'name': '中国人保', 'prefix': 'sh', 'holdings': {
        '中信': {'shares': 2900, 'cost': 8.502},
        '国信': {'shares': 2300, 'cost': 8.503}
    }}
}

# ================== 🌐 获取腾讯财经股价 ==================
def get_stock_price_tencent(stock_code):
    info = STOCKS[stock_code]
    url = f"http://qt.gtimg.cn/q={info['prefix']}{stock_code}"
    print(f"🔍 正在获取 {stock_code} {info['name']} 数据...")
    
    try:
        response = requests.get(url, timeout=10)
        response.encoding = 'gbk'
        data = response.text.split('~')
        
        if len(data) > 5:
            current = float(data[3])
            yesterday_close = float(data[4])
            open_price = float(data[5])
            print(f"✓ 成功 | 现价: {current:.2f} | 昨收: {yesterday_close:.2f} | 涨幅: {((current - yesterday_close)/yesterday_close)*100:+.2f}%")
            return {'current': current, 'yesterday_close': yesterday_close, 'open': open_price}
    except Exception as e:
        print(f"⚠️  获取失败: {e}")
    
    print(f"❌ 获取{stock_code}失败，使用默认价 3.00")
    return {'current': 3.00, 'yesterday_close': None, 'open': None}

# ================== 📱 Server 酱推送 ==================
def send_wechat(title, content):
    key = os.getenv("SERVERCHAN_KEY")  # 从 Secrets 读取
    if not key:
        print("❌ 未设置 SERVERCHAN_KEY")
        return
    url = f"https://sctapi.ftqq.com/{key}.send"
    try:
        res = requests.post(url, data={'title': title, 'desp': content})
        if res.status_code == 200:
            print("✅ 微信推送成功")
        else:
            print(f"❌ 推送失败: {res.text}")
    except Exception as e:
        print(f"❌ 发送微信出错: {e}")

# ================== 📊 计算盈利 ==================
def calc_profit():
    results = {}
    total_cost = 0
    total_profit = 0
    total_daily_profit = 0  # 新增：当日总浮动盈亏

    for code, cfg in STOCKS.items():
        holdings = cfg['holdings']
        shares = sum(h['shares'] for h in holdings.values())
        cost = sum(h['shares'] * h['cost'] for h in holdings.values())
        
        # 获取股价信息，包含昨日收盘价用于计算当日浮动盈亏
        price_data = get_stock_price_tencent(code)
        current_price = price_data['current']
        yesterday_close = price_data['yesterday_close']
        
        value = shares * current_price
        profit = value - cost
        rate = (profit / cost) * 100 if cost else 0
        
        # 计算当日浮动盈亏
        daily_profit = 0
        if yesterday_close is not None:
            daily_profit = round(shares * (current_price - yesterday_close), 2)
            print(f"📊 {code} {cfg['name']} 当日浮动盈亏计算: {shares:,} 股 * ({current_price:.2f} - {yesterday_close:.2f}) = {daily_profit:+.2f} 元")
        else:
            print(f"⚠️ {code} {cfg['name']} 无法获取昨日收盘价，当日浮动盈亏计算为 0")

        results[code] = {
            'name': cfg['name'],
            'profit': profit,
            'rate': rate,
            'price': current_price,
            'shares': shares,
            'cost': cost,
            'daily_profit': daily_profit,  # 新增：当日浮动盈亏
            'yesterday_close': yesterday_close  # 新增：昨日收盘价
        }
        total_cost += cost
        total_profit += profit
        total_daily_profit += daily_profit  # 累加当日浮动盈亏

    total_rate = (total_profit / total_cost) * 100 if total_cost else 0

    return results, total_profit, total_rate, total_daily_profit

# ================== 🏁 主程序 ==================
if __name__ == "__main__":
    print("🔍 开始获取股票数据...")

    data, total_profit, total_rate, total_daily_profit = calc_profit()
    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    # 微信消息
    content = f"""
📈 **股票盈利日报**

💰 **{data['601991']['name']}**
- 累计盈利: {data['601991']['profit']:+,.2f} 元
- 当前股价: {data['601991']['price']:.2f} 元
- 涨幅: {data['601991']['rate']:+.2f}%
📅 当日盈利: {data['601991']['daily_profit']:+,.2f} 元

💡 **{data['000767']['name']}**
- 累计盈利: {data['000767']['profit']:+,.2f} 元
- 当前股价: {data['000767']['price']:.2f} 元
- 涨幅: {data['000767']['rate']:+.2f}%
📅 当日盈利: {data['000767']['daily_profit']:+,.2f} 元

🛡️ **{data['601319']['name']}**
- 累计盈利: {data['601319']['profit']:+,.2f} 元
- 当前股价: {data['601319']['price']:.2f} 元
- 涨幅: {data['601319']['rate']:+.2f}%
📅 当日盈利: {data['601319']['daily_profit']:+,.2f} 元

🔥 **合计总收益**
- 累计: {total_profit:+,.2f} 元
- 盈利率: {total_rate:+.2f}%

📅 今日浮动盈亏
🔴🟢 {total_daily_profit:+,.2f} 元

📅 {now}
    """

    title = f"📊 三股日报 | 合计{total_profit:+,.2f}元 | 当日{total_daily_profit:+,.2f}元"

    print(content)
    send_wechat(title, content)



