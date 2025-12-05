# -*- coding: utf-8 -*-
"""
股票盈利监控系统 - GitHub Actions 版 (优化版)
"""

import requests
import os
import json
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
    '601319': {'name': '中国人保', 'prefix': 'sh', 'holdings': {
        '中信': {'shares': 2900, 'cost': 8.502},
        '国信': {'shares': 2300, 'cost': 8.503},
        '加仓1': {'shares': 9300, 'cost': 8.59},
        '加仓2': {'shares': 7000, 'cost': 8.58}
    }}
}

# ================== 💾 本地存储收盘价 ==================
def save_yesterday_prices(prices):
    """保存昨日收盘价到本地文件"""
    file_path = "yesterday_prices.json"
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(prices, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ 保存昨日价格失败: {e}")

def load_yesterday_prices():
    """从本地文件加载昨日收盘价"""
    file_path = "yesterday_prices.json"
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"❌ 加载昨日价格失败: {e}")
    return {}

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

# ================== 🌐 获取股价 ==================
def get_price(code):
    info = STOCKS[code]
    url = f"http://qt.gtimg.cn/q={info['prefix']}{code}"
    try:
        res = requests.get(url, timeout=10)
        res.encoding = 'gbk'
        data = res.text.split('~')
        if len(data) > 3:
            return float(data[3])
    except:
        pass
    return 3.00  # 失败返回默认价

# ================== 📊 计算盈利 ==================
def calc_profit():
    results = {}
    total_cost = 0
    total_profit = 0
    today_profit_total = 0
    
    # 获取昨日收盘价
    yesterday_prices = load_yesterday_prices()

    for code, cfg in STOCKS.items():
        holdings = cfg['holdings']
        shares = sum(h['shares'] for h in holdings.values())
        cost = sum(h['shares'] * h['cost'] for h in holdings.values())
        price = get_price(code)
        value = shares * price
        profit = value - cost
        rate = (profit / cost) * 100 if cost else 0
        
        # 计算当日盈亏
        yesterday_price = yesterday_prices.get(code, price)  # 如果没有昨日价格，则用当前价格
        today_profit = (price - yesterday_price) * shares

        results[code] = {
            'name': cfg['name'],
            'profit': profit,
            'rate': rate,
            'price': price,
            'shares': shares,
            'cost': cost,
            'today_profit': today_profit,
            'yesterday_price': yesterday_price,
            'price_change': price - yesterday_price
        }
        total_cost += cost
        total_profit += profit
        today_profit_total += today_profit

    total_rate = (total_profit / total_cost) * 100 if total_cost else 0
    today_rate = (today_profit_total / total_cost) * 100 if total_cost else 0

    return results, total_profit, total_rate, today_profit_total, today_rate

# ================== 🏁 主程序 ==================
if __name__ == "__main__":
    print("🔍 开始获取股票数据...")

    data, total_profit, total_rate, today_profit_total, today_rate = calc_profit()
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    # 更新昨日收盘价
    new_yesterday_prices = {code: stock_data['price'] for code, stock_data in data.items()}
    save_yesterday_prices(new_yesterday_prices)

    # 判断是否首次运行（所有股票的昨日价格等于当前价格）
    all_first_run = all(abs(stock['price'] - stock['yesterday_price']) < 0.01 for stock in data.values())
    first_run_note = " (首次运行，无昨日对比)" if all_first_run else ""

    # 微信消息
    content = f"""
📈 **股票盈利日报{first_run_note}**

💰 **{data['601991']['name']}**
- 累计盈利: {data['601991']['profit']:+,.2f} 元
- 当日盈亏: {data['601991']['today_profit']:+,.2f} 元
- 当前股价: {data['601991']['price']:.2f} 元
- 昨收: {data['601991']['yesterday_price']:.2f} 元
- 涨跌: {data['601991']['price_change']:+.2f} 元 ({data['601991']['price_change']/data['601991']['yesterday_price']*100:+.2f}%)
- 涨幅: {data['601991']['rate']:+.2f}%

💡 **{data['000767']['name']}**
- 累计盈利: {data['000767']['profit']:+,.2f} 元
- 当日盈亏: {data['000767']['today_profit']:+,.2f} 元
- 当前股价: {data['000767']['price']:.2f} 元
- 昨收: {data['000767']['yesterday_price']:.2f} 元
- 涨跌: {data['000767']['price_change']:+.2f} 元 ({data['000767']['price_change']/data['000767']['yesterday_price']*100:+.2f}%)
- 涨幅: {data['000767']['rate']:+.2f}%

🛡️ **{data['601319']['name']}**
- 累计盈利: {data['601319']['profit']:+,.2f} 元
- 当日盈亏: {data['601319']['today_profit']:+,.2f} 元
- 当前股价: {data['601319']['price']:.2f} 元
- 昨收: {data['601319']['yesterday_price']:.2f} 元
- 涨跌: {data['601319']['price_change']:+.2f} 元 ({data['601319']['price_change']/data['601319']['yesterday_price']*100:+.2f}%)
- 涨幅: {data['601319']['rate']:+.2f}%

🔥 **合计总收益**
- 累计: {total_profit:+,.2f} 元
- 当日盈亏: {today_profit_total:+,.2f} 元
- 盈利率: {total_rate:+.2f}%
- 当日盈利率: {today_rate:+.2f}%

📅 {now}
    """

    title = f"📊 三股日报 | 总{total_profit:+,.2f}元 | 当日{today_profit_total:+,.2f}元"

    print(content)
    send_wechat(title, content)



