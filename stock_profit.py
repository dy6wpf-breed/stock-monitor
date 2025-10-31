# -*- coding: utf-8 -*-
"""
股票盈利监控系统 - GitHub Actions 版
✅ 支持微信 + 精美 HTML 邮件双通知
✅ 新增：当日盈利、历史数据记录
"""

import requests
import os
import smtplib
import json
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.header import Header

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
    }}
}

# ================== 📱 发送微信通知 ==================
def send_wechat(title, content):
    key = os.getenv("SERVERCHAN_KEY")
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

# ================== 📧 发送精美 HTML 邮件 ==================
def send_email(title, html_content):
    user = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASSWORD")
    
    if not user or not password:
        print("❌ 未设置 EMAIL_USER 或 EMAIL_PASSWORD")
        return

    msg = MIMEText(html_content, 'html', 'utf-8')
    msg['From'] = Header(user)
    msg['To'] = Header(user)
    msg['Subject'] = Header(title)

    try:
        server = smtplib.SMTP_SSL('smtp.163.com', 465)
        server.login(user, password)
        server.sendmail(user, [user], msg.as_string())
        server.quit()
        print("✅ 邮件发送成功！")
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")

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

# ================== 🗃️ 读取历史价格 ==================
def load_history():
    if os.path.exists('stock_history.json'):
        with open('stock_history.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# ================== 💾 保存历史价格 ==================
def save_history(history):
    with open('stock_history.json', 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

# ================== 📊 计算盈利 ==================
def calc_profit():
    results = {}
    total_cost = 0
    total_profit = 0
    total_daily_profit = 0  # 新增：当日总盈利

    # 读取历史价格
    history = load_history()
    today = datetime.now().strftime('%Y-%m-%d')

    for code, cfg in STOCKS.items():
        holdings = cfg['holdings']
        shares = sum(h['shares'] for h in holdings.values())
        cost = sum(h['shares'] * h['cost'] for h in holdings.values())
        price = get_price(code)
        value = shares * price
        profit = value - cost
        rate = (profit / cost) * 100 if cost else 0

        # 获取昨日收盘价
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        last_close = None

        # 查找最近一个非今天的收盘价
        for i in range(1, 8):  # 向前查7天（避免周末）
            check_date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            if code in history and check_date in history[code]:
                last_close = history[code][check_date]['close']
                break

        # 如果没有历史数据，用当前价作为“昨日价”（首次运行）
        if last_close is None:
            last_close = price

        # 计算当日盈利
        daily_profit = (price - last_close) * shares

        # 更新历史数据
        if code not in history:
            history[code] = {}
        history[code][today] = {
            'close': price,
            'date': today
        }

        results[code] = {
            'name': cfg['name'],
            'profit': profit,
            'rate': rate,
            'price': price,
            'shares': shares,
            'cost': cost,
            'daily_profit': daily_profit,  # 新增
            'last_close': last_close        # 新增
        }
        total_cost += cost
        total_profit += profit
        total_daily_profit += daily_profit

    total_rate = (total_profit / total_cost) * 100 if total_cost else 0

    # 保存历史数据
    save_history(history)

    return results, total_profit, total_rate, total_daily_profit

# ================== 🎨 生成 HTML 邮件内容 ==================
def create_html_content(data, total_profit, total_rate, total_daily_profit):
    stock_rows = ""
    colors = {
        '601991': '#66bb6a' if data['601991']['profit'] >= 0 else '#ef5350',
        '00767': '#66bb6a' if data['00767']['profit'] >= 0 else '#ef5350'
    }
    daily_colors = {
        '601991': '#4caf50' if data['601991']['daily_profit'] >= 0 else '#f44336',
        '00767': '#4caf50' if data['00767']['daily_profit'] >= 0 else '#f44336'
    }
    
    for code in ['601991', '00767']:
        d = data[code]
        icon = '📈' if d['profit'] >= 0 else '📉'
        daily_icon = '🟢' if d['daily_profit'] >= 0 else '🔴'
        color = colors[code]
        dcolor = daily_colors[code]
        stock_rows += f"""
        <tr>
            <td style="padding:12px;border:1px solid #ddd;text-align:center;">{code}</td>
            <td style="padding:12px;border:1px solid #ddd;">{d['name']}</td>
            <td style="padding:12px;border:1px solid #ddd;text-align:right;">{d['shares']:,}</td>
            <td style="padding:12px;border:1px solid #ddd;text-align:right;">{d['price']:.2f}</td>
            <td style="padding:12px;border:1px solid #ddd;text-align:right;">{d['cost']:,.2f}</td>
            <td style="padding:12px;border:1px solid #ddd;text-align:right;color:{color};font-weight:bold;">
                {icon} {d['profit']:+,.2f}
            </td>
            <td style="padding:12px;border:1px solid #ddd;text-align:right;">{d['rate']:+.2f}%</td>
            <td style="padding:12px;border:1px solid #ddd;text-align:right;color:{dcolor};font-weight:bold;">
                {daily_icon} {d['daily_profit']:+,.2f}
            </td>
        </tr>
        """

    total_icon = '📈' if total_profit >= 0 else '📉'
    total_color = '#388e3c' if total_profit >= 0 else '#d32f2f'
    daily_total_color = '#2e7d32' if total_daily_profit >= 0 else '#c62828'
    daily_total_icon = '🟢' if total_daily_profit >= 0 else '🔴'

    html = f"""
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="font-family:Arial,'Microsoft YaHei';line-height:1.8;margin:0;padding:20px;background:#f5f5f5;">
        <div style="max-width:900px;margin:auto;background:white;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,0.1);">
            <div style="background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:30px;text-align:center;">
                <h2 style="margin:0;">📊 股票盈利日报</h2>
                <p style="opacity:0.9;margin:5px 0 0 0;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            <div style="padding:20px;">
                <table width="100%" style="border-collapse:collapse;text-align:center;">
                    <thead>
                        <tr style="background:#f8f9fa;">
                            <th style="padding:12px;border:1px solid #ddd;">代码</th>
                            <th style="padding:12px;border:1px solid #ddd;">名称</th>
                            <th style="padding:12px;border:1px solid #ddd;">持股数</th>
                            <th style="padding:12px;border:1px solid #ddd;">现价</th>
                            <th style="padding:12px;border:1px solid #ddd;">总成本</th>
                            <th style="padding:12px;border:1px solid #ddd;">累计盈利</th>
                            <th style="padding:12px;border:1px solid #ddd;">盈利率</th>
                            <th style="padding:12px;border:1px solid #ddd;">当日盈利</th>
                        </tr>
                    </thead>
                    <tbody>
                        {stock_rows}
                    </tbody>
                </table>

                <!-- 总计 -->
                <div style="text-align:center;padding:25px;background:linear-gradient(135deg,#ff7e5f,#feb47b);color:white;border-radius:12px;margin:25px 0;box-shadow:0 4px 12px rgba(0,0,0,0.2);">
                    <div style="font-size:24px;opacity:0.9;">🔥 合计总收益</div>
                    <div style="font-size:38px;font-weight:bold;margin:10px 0; color:white;">
                        {total_icon} <span style="font-size:38px;">{total_profit:+,.2f} 元</span>
                    </div>
                    <div style="font-size:20px;">{total_rate:+.2f}%</div>
                </div>

                <!-- 当日总盈利 -->
                <div style="text-align:center;padding:20px;background:#e3f2fd;border:1px dashed #2196f3;border-radius:12px;margin:25px 0;">
                    <div style="font-size:20px;opacity:0.9;">📅 今日浮动盈亏</div>
                    <div style="font-size:32px;font-weight:bold;color:{daily_total_color};">
                        {daily_total_icon} {total_daily_profit:+,.2f} 元
                    </div>
                </div>
            </div>
            <div style="text-align:center;color:#999;font-size:12px;padding:20px;border-top:1px dashed #eee;">
                🤖 本邮件由 GitHub Actions 自动发送 | 📊 已记录历史数据 | 🍀 祝投资顺利！
            </div>
        </div>
    </body>
    </html>
    """
    return html

# ================== 🏁 主程序 ==================
if __name__ == "__main__":
    print("🔍 开始获取股票数据...")

    data, total_profit, total_rate, total_daily_profit = calc_profit()
    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    # 微信消息（Markdown）
    wechat_content = f"""
📈 **股票盈利日报**

💰 **{data['601991']['name']}**
- 累计盈利: {data['601991']['profit']:+,.2f} 元
- 当前股价: {data['601991']['price']:.2f} 元
- 涨幅: {data['601991']['rate']:+.2f}%
- 📅 当日盈利: {data['601991']['daily_profit']:+,.2f} 元

💡 **{data['00767']['name']}**
- 累计盈利: {data['00767']['profit']:+,.2f} 元
- 当前股价: {data['00767']['price']:.2f} 元
- 涨幅: {data['00767']['rate']:+.2f}%
- 📅 当日盈利: {data['00767']['daily_profit']:+,.2f} 元

🔥 **合计总收益**
- 累计: {total_profit:+,.2f} 元
- 盈利率: {total_rate:+.2f}%

📅 **今日浮动盈亏**
- 🔴🟢 {total_daily_profit:+,.2f} 元

📅 {now}
    """

    title = f"📊 双股日报 | 合计{total_profit:+,.2f}元"

    # 发送微信
    print(wechat_content)
    send_wechat(title, wechat_content)

    # 发送 HTML 邮件
    html_email = create_html_content(data, total_profit, total_rate, total_daily_profit)
    send_email(title, html_email)
