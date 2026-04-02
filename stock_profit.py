#!/usr/bin/env python3
"""
股票资产仪表盘 - PIC版
基于知识库数据，实时监控中国电建持仓
"""

import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import time
from datetime import datetime

# ==================== 知识库数据 ====================
KB = {
    "REALIZED_PROFIT": 609633.00,  # 累计落袋收益
    
    # 当前持仓
    "holdings": {
        "601669": {
            "name": "中国电建",
            "accounts": {
                "中信建投": {"shares": 191600, "cost": 5.938},
                "国信证券": {"shares": 209300, "cost": 5.963},
                "东方财富": {"shares": 1500, "cost": 6.073}
            },
            "total_shares": 402400
        }
    },
    
    # 通讯配置
    "serverchan_key": "SCT301051TaXqp0xNoZ458CWFsj31BI3At",
    "smtp": {"host": "smtp.163.com", "port": 465},
    "email": "bjlmwpf@163.com"
}

def get_quote(stock_code="sh601669"):
    """获取行情数据"""
    url = f"http://qt.gtimg.cn/q={stock_code}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.text
        
        # 解析: "~最新价~昨收~最高~最低~..."
        fields = data.split("~")
        if len(fields) > 5:
            return {
                "code": stock_code,
                "name": fields[1],
                "price": float(fields[3]),
                "prev_close": float(fields[4]),
                "high": float(fields[5]),
                "low": float(fields[6])
            }
    except Exception as e:
        print(f"获取行情失败: {e}")
    
    return None

def calculate_pnl(quote):
    """计算盈亏"""
    price = quote["price"]
    kb = KB["holdings"]["601669"]
    
    results = {}
    total_float_pnl = 0
    
    for account, info in kb["accounts"].items():
        cost = info["cost"]
        shares = info["shares"]
        market_value = price * shares
        cost_basis = cost * shares
        pnl = market_value - cost_basis
        pnl_pct = (price - cost) / cost * 100
        
        results[account] = {
            "shares": shares,
            "cost": cost,
            "price": price,
            "market_value": market_value,
            "pnl": pnl,
            "pnl_pct": pnl_pct
        }
        total_float_pnl += pnl
    
    # 总盈亏含落袋
    total_pnl = total_float_pnl + KB["REALIZED_PROFIT"]
    
    # 安全垫
    safety_buffer = KB["REALIZED_PROFIT"] / kb["total_shares"]
    safety_pct = safety_buffer / price * 100
    
    # 今日变动
    change_today = (price - quote["prev_close"]) * kb["total_shares"]
    change_pct = (price - quote["prev_close"]) / quote["prev_close"] * 100
    
    return {
        "accounts": results,
        "total_float_pnl": total_float_pnl,
        "total_pnl": total_pnl,
        "safety_buffer": safety_buffer,
        "safety_pct": safety_pct,
        "change_today": change_today,
        "change_pct": change_pct,
        "price": price,
        "prev_close": quote["prev_close"]
    }

def send_serverchan(title, content, key):
    """Server酱Turbo推送"""
    url = f"https://sctapi.ftqq.com/send/{key}.send"
    data = {"title": title, "desp": content}
    headers = {"Authorization": key}
    
    try:
        resp = requests.post(url, data=data, headers=headers, timeout=10)
        return resp.json().get("code") == 0
    except:
        return False

def send_email(subject, html_content):
    """邮件推送"""
    smtp_info = KB["smtp"]
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = KB["email"]
    msg["To"] = KB["email"]
    msg.attach(MIMEText(html_content, "html", "utf-8"))
    
    try:
        server = smtplib.SMTP_SSL(smtp_info["host"], smtp_info["port"])
        server.login(KB["email"], "SVhst3hJKdNGE2hQ")
        server.sendmail(KB["email"], KB["email"], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"邮件发送失败: {e}")
        return False

def main():
    print("=" * 50)
    print("🏆 股票资产仪表盘 - 启动")
    print("=" * 50)
    
    # 1. 获取行情
    print("\n📡 正在获取行情...")
    quote = get_quote("sh601669")
    if not quote:
        print("❌ 行情获取失败")
        return
    
    print(f"✅ {quote['name']} 现价: {quote['price']:.3f}")
    
    # 2. 计算盈亏
    print("\n🧮 正在计算盈亏...")
    pnl_data = calculate_pnl(quote)
    
    # 3. 打印结果
    print("\n" + "=" * 50)
    print("📊 资产仪表盘")
    print("=" * 50)
    print(f"总盈亏(含落袋): {pnl_data['total_pnl']:+,.0f} 元")
    print(f"浮动盈亏: {pnl_data['total_float_pnl']:+,.0f} 元")
    print(f"累计落袋: +{KB['REALIZED_PROFIT']:,.0f} 元")
    
    print("\n⚠️ 安全垫分析")
    print(f"安全垫: {pnl_data['safety_buffer']:.3f} 元/股")
    print(f"安全跌幅: {pnl_data['safety_pct']:.1f}%")
    print(f"护城河价: {pnl_data['price'] - pnl_data['safety_buffer']:.3f} 元")
    
    print("\n📈 今日实况")
    print(f"今日变动: {pnl_data['change_today']:+,.0f} 元 ({pnl_data['change_pct']:+.2f}%)")
    
    print("\n📋 分账户对账")
    for acc, info in pnl_data['accounts'].items():
        print(f"  {acc}: {info['pnl']:+,.0f} 元 ({info['pnl_pct']:+.1f}%)")
    
    # 4. 推送消息
    print("\n📤 正在推送消息...")
    
    title = f"🏆 财富日报: {pnl_data['total_pnl']:+,.0f} | 今日 {pnl_data['change_today']:+,.0f}"
    md_content = f"""
## 📊 资产仪表盘
- 总盈亏(含落袋): **{pnl_data['total_pnl']:+,.0f}** 元
- 浮动盈亏: {pnl_data['total_float_pnl']:+,.0f} 元
- 累计落袋: +{KB['REALIZED_PROFIT']:,.0f} 元

## ⚠️ 安全垫分析
- 安全垫: {pnl_data['safety_buffer']:.3f} 元/股
- 安全跌幅: {pnl_data['safety_pct']:.1f}%
- 护城河价: {pnl_data['price'] - pnl_data['safety_buffer']:.3f} 元

## 📈 今日实况
- 今日变动: {pnl_data['change_today']:+,.0f} 元 ({pnl_data['change_pct']:+.2f}%)

## 📋 分账户对账
- 中信建投: {pnl_data['accounts']['中信建投']['pnl']:+,.0f} 元
- 国信证券: {pnl_data['accounts']['国信证券']['pnl']:+,.0f} 元
- 东方财富: {pnl_data['accounts']['东方财富']['pnl']:+,.0f} 元
"""
    
    if send_serverchan(title, md_content, KB["serverchan_key"]):
        print("✅ Server酱推送成功")
    else:
        print("⚠️ Server酱推送失败")
    
    html = f"<html><body><h1>财富日报</h1><p>总盈亏: {pnl_data['total_pnl']:+,.0f}元</p></body></html>"
    email_subject = f"🏆 财富日报 {datetime.now().strftime('%Y-%m-%d')}"
    
    if send_email(email_subject, html):
        print("✅ 邮件推送成功")
    else:
        print("⚠️ 邮件推送失败")
    
    print("\n" + "=" * 50)
    print("✅ 执行完成")
    print("=" * 50)

if __name__ == "__main__":
    main()

---
文件2: stock_github.py (GitHub Actions版)
# -*- coding: utf-8 -*-
"""
股票盈利监控系统 - GitHub Actions v8.2
"""

import requests
import os
from datetime import datetime, timedelta

# ================== 核心财务基准 ==================
REALIZED_PROFIT = 609633 

# ================== 持仓配置 ==================
STOCKS = {
    '601669': {'name': '中国电建', 'prefix': 'sh', 'holdings': {
        '中信建投': {'shares': 191600, 'cost': 5.938}, 
        '国信证券': {'shares': 209300, 'cost': 5.963},
        '东方财富': {'shares': 1500,   'cost': 6.073}
    }}
}

# ================== 推送逻辑 (Server酱Turbo) ==================
def send_wechat(title, content):
    key = os.getenv("SERVERCHAN_KEY") or "SCT301051TaXqp0xNoZ458CWFsj31BI3At"
    url = f"https://sctapi.ftqq.com/send/{key}.send"
    try:
        requests.post(url, data={'title': title, 'desp': content}, timeout=15)
    except: pass

# ================== 获取行情 ==================
def get_stock_data(code, prefix):
    url = f"http://qt.gtimg.cn/q={prefix}{code}"
    try:
        res = requests.get(url, timeout=10)
        data = res.text.split('~')
        if len(data) > 32:
            return float(data[3]), float(data[4]), float(data[32])
    except: pass
    return 0.0, 0.0, 0.0

# ================== 计算逻辑 ==================
def calc_profit():
    price_now, price_last, pct = get_stock_data('601669', 'sh')
    if price_now == 0: return None

    cfg = STOCKS['601669']['holdings']
    zx, gx, df = cfg['中信建投'], cfg['国信证券'], cfg['东方财富']

    zx_prof = zx['shares'] * (price_now - zx['cost'])
    gx_prof = gx['shares'] * (price_now - gx['cost'])
    df_prof = df['shares'] * (price_now - df['cost'])

    total_shares = zx['shares'] + gx['shares'] + df['shares']
    total_mv = total_shares * price_now
    total_floating = zx_prof + gx_prof + df_prof
    final_total_profit = total_floating + REALIZED_PROFIT
    daily_change = (price_now - price_last) * total_shares

    content = f"""
## 💰 账户资产概览
- **总损益 (含落袋)**: **{final_total_profit:+,.2f}** 元
- **持仓总市值**: **{total_mv:,.0f}** 元
- **今日总变动**: **{daily_change:+,.2f}** 元 ({pct:+.2f}%)

## 分账户对账
- 中信建投: {zx_prof:+,.0f} ({zx['shares']:,}股)
- 国信证券: {gx_prof:+,.0f} ({gx['shares']:,}股)
- 东方财富: {df_prof:+,.0f} ({df['shares']:,}股)

📅 更新时间: {(datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')}
"""
    return final_total_profit, daily_change, content

if __name__ == "__main__":
    result = calc_profit()
    if result:
        tot, day, body = result
        send_wechat(f"🚀 资产日报: {tot:+,.0f} | 变动 {day:+,.0f}", body)
