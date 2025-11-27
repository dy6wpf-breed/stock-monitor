# -*- coding: utf-8 -*-
"""
股票盈利监控系统 - GitHub Actions 版
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
    '00767': {'name': '晋控电力', 'prefix': 'sz', 'holdings': {
        '中信': {'shares': 26700, 'cost': 3.00},
        '国信': {'shares': 26200, 'cost': 3.05}
    }},
    '601319': {'name': '中国人保', 'prefix': 'sh', 'holdings': {
        '中信': {'shares': 2900, 'cost': 8.502},
        '国信': {'shares': 2300, 'cost': 8.503},
        '加仓1': {'shares': 9300, 'cost': 8.59},
        '加仓2': {'shares': 7000, 'cost': 8.58}
    }}
}

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

    for code, cfg in STOCKS.items():
        holdings = cfg['holdings']
        shares = sum(h['shares'] for h in holdings.values())
        cost = sum(h['shares'] * h['cost'] for h in holdings.values())
        price = get_price(code)
        value = shares * price
        profit = value - cost
        rate = (profit / cost) * 100 if cost else 0

        results[code] = {
            'name': cfg['name'],
            'profit': profit,
            'rate': rate,
            'price': price,
            'shares': shares,
            'cost': cost
        }
        total_cost += cost
        total_profit += profit

    total_rate = (total_profit / total_cost) * 100 if total_cost else 0

    return results, total_profit, total_rate

# ================== 🏁 主程序 ==================
if __name__ == "__main__":
    print("🔍 开始获取股票数据...")

    data, total_profit, total_rate = calc_profit()
    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    # 微信消息
    content = f"""
📈 **股票盈利日报**

💰 **{data['601991']['name']}**
- 累计盈利: {data['601991']['profit']:+,.2f} 元
- 当前股价: {data['601991']['price']:.2f} 元
- 涨幅: {data['601991']['rate']:+.2f}%

💡 **{data['00767']['name']}**
- 累计盈利: {data['00767']['profit']:+,.2f} 元
- 当前股价: {data['00767']['price']:.2f} 元
- 涨幅: {data['00767']['rate']:+.2f}%

🛡️ **{data['601319']['name']}**
- 累计盈利: {data['601319']['profit']:+,.2f} 元
- 当前股价: {data['601319']['price']:.2f} 元
- 涨幅: {data['601319']['rate']:+.2f}%

🔥 **合计总收益**
- 累计: {total_profit:+,.2f} 元
- 盈利率: {total_rate:+.2f}%

📅 {now}
    """

    title = f"📊 三股日报 | 合计{total_profit:+,.2f}元"

    print(content)
    send_wechat(title, content)



