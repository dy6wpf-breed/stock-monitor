# -*- coding: utf-8 -*-
"""
股票盈利统计系统 v7.3 - 精准对账版
(根据中信/国信最新截图修正：总持仓 40.09 万股)
"""

import pandas as pd
from datetime import datetime
import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

# ================== 💰 已落袋收益统计 ==================
REALIZED_PROFIT = 609633 

# ================== 📌 现有持仓配置 (依据最新截图精准更新) ==================
STOCKS = {
    '601669': {
        'name': '中国电建',
        'holdings': {
            '中信建投': {'shares': 191600, 'cost': 5.938}, # 对应截图1
            '国信证券': {'shares': 209300, 'cost': 5.963}  # 对应截图2：大幅加仓后
        },
        'prefix': 'sh'
    }
}

# ================== 📧 通讯配置 ==================
EMAIL_CONFIG = {
    'sender': 'bjlmwpf@163.com',
    'password': 'RVSeJdxea8UKw8AS',
    'receivers': ['bjlmwpf@163.com', '18810296859@163.com'],
    'smtp_server': 'smtp.163.com',
    'smtp_port': 465
}
SERVERCHAN_SENDKEY = "SCT301051TaXqp0xNoZ458CWFsj31BI3At"

def get_stock_price_tencent(stock_code):
    stock_info = STOCKS[stock_code]
    url = f"http://qt.gtimg.cn/q={stock_info['prefix']}{stock_code}"
    try:
        response = requests.get(url, timeout=15)
        response.encoding = 'gbk'
        data = response.text.split('~')
        if len(data) > 32:
            return {'current': float(data[3]), 'yesterday_close': float(data[4]), 'pct_change': float(data[32])}
    except: pass
    return {'current': 0, 'yesterday_close': 0, 'pct_change': 0}

def process_data():
    all_data = {}
    total_mv = 0
    total_floating_profit = 0
    total_daily_profit = 0
    for code, config in STOCKS.items():
        price_data = get_stock_price_tencent(code)
        shares = sum(h['shares'] for h in config['holdings'].values())
        cost_sum = sum(h['shares'] * h['cost'] for h in config['holdings'].values())
        mv = shares * price_data['current']
        profit = mv - cost_sum
        daily = shares * (price_data['current'] - price_data['yesterday_close'])
        all_data[code] = {
            'name': config['name'], 'price': price_data['current'], 'shares': shares,
            'cost_avg': cost_sum / shares, 'value': mv, 'profit': profit,
            'profit_rate': (profit / cost_sum * 100), 'daily_profit': daily, 
            'daily_pct': price_data['pct_change']
        }
        total_mv += mv
        total_floating_profit += profit
        total_daily_profit += daily
    return all_data, total_mv, total_floating_profit, total_daily_profit

def send_deep_wechat(all_data, final_profit, daily_profit, floating_profit, total_mv):
    title = f"📊 账户对账日报: {final_profit:+,.0f}"
    stock_md = ""
    for code, d in all_data.items():
        stock_md += f"### 🔹 {d['name']} ({code})\n- **当前浮盈**: `{d['profit']:+,.0f}`\n- **现价/成本**: `{d['price']:.3f}` / `{d['cost_avg']:.3f}`\n- **最新持仓**: `{d['shares']:,}` 股\n---"
    desp = f"## 💰 资产快报\n- **总损益**: **{final_profit:+,.2f}**\n- **总市值**: {total_mv:,.0f}\n\n> 浮盈: {floating_profit:+,.0f}\n> 落袋: {REALIZED_PROFIT:+,.0f}\n\n{stock_md}"
    requests.post(f"https://sctapi.ftqq.com/{SERVERCHAN_SENDKEY}.send", data={'title': title, 'desp': desp})

def create_fancy_email(all_data, total_mv, final_profit, daily_profit, total_floating):
    rows = ""
    for code, d in all_data.items():
        p_color = "#e64340" if d['profit'] >= 0 else "#09bb07"
        rows += f"""<tr style="border-bottom: 1px solid #f0f0f0;">
            <td style="padding: 20px 10px;"><b>{d['name']}</b><br><small>{code}</small></td>
            <td style="padding: 20px 10px; text-align: right;">{d['price']:.3f}<br><small>成本: {d['cost_avg']:.3f}</small></td>
            <td style="padding: 20px 10px; text-align: right; color: {p_color}; font-weight: bold;">{d['profit']:+,.0f}</td>
            <td style="padding: 20px 10px; text-align: right;">{d['value']:,.0f}</td>
            <td style="padding: 20px 10px; text-align: right;">{d['shares']:,}</td></tr>"""
    return f"""<html><body style="background:#f2f4f7; padding:20px; font-family: sans-serif;">
        <div style="max-width:800px; margin:auto; background:white; border-radius:12px; overflow:hidden; box-shadow:0 4px 20px rgba(0,0,0,0.08);">
            <div style="background:#1c1c1e; padding:40px; color:white; text-align:center;">
                <div style="opacity:0.6; font-size:14px;">账户总盈亏 (含历史落袋)</div>
                <div style="font-size:42px; font-weight:bold;">{final_profit:+,.2f}</div>
            </div>
            <div style="padding:25px;">
                <table width="100%" cellspacing="0" style="border-collapse: collapse;">
                    <thead><tr style="text-align: right; font-size: 12px; color: #999; border-bottom: 2px solid #f0f0f0;"><th align="left" style="padding: 10px;">持仓</th><th style="padding: 10px;">现价/成本</th><th style="padding: 10px;">盈亏额</th><th style="padding: 10px;">市值</th><th style="padding: 10px;">股数</th></tr></thead>
                    <tbody>{rows}</tbody>
                </table>
                <div style="margin-top:20px; font-size:12px; color:#999;">持仓浮盈: {total_floating:+,.0f} | 历史落袋: {REALIZED_PROFIT:+,.0f}</div>
            </div>
        </div></body></html>"""

if __name__ == "__main__":
    all_data, total_mv, total_floating, total_daily = process_data()
    final_profit = total_floating + REALIZED_PROFIT
    send_deep_wechat(all_data, final_profit, total_daily, total_floating, total_mv)
    msg = MIMEMultipart(); msg['Subject'] = Header(f"📊 修正后资产报表 | {final_profit:+,.0f}"); msg['From'] = Header(EMAIL_CONFIG['sender']); msg['To'] = Header(', '.join(EMAIL_CONFIG['receivers']))
    msg.attach(MIMEText(create_fancy_email(all_data, total_mv, final_profit, total_daily, total_floating), 'html', 'utf-8'))
    try:
        server = smtplib.SMTP_SSL(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.login(EMAIL_CONFIG['sender'], EMAIL_CONFIG['password']); server.sendmail(EMAIL_CONFIG['sender'], EMAIL_CONFIG['receivers'], msg.as_string()); server.quit()
        print(f"✅ 修正版报表已发送")
    except Exception as e: print(f"❌ 失败: {e}")
