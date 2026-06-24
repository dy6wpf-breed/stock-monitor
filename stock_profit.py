# -*- coding: utf-8 -*-
"""
股票盈利监控系统 - GitHub Actions v8.5 (经典Server酱多股对账完美版)
更新日志：
1. 扩展数据结构，新增国信证券新兴铸管持仓
2. 行情接口升级为批量获取，优化网络请求
3. 微信推送增加“个股全局看板”（个股总股数、个股总市值、个股历史总盈亏）
"""

import requests
import os
from datetime import datetime, timedelta

# ================== 📌 核心财务底牌 ==================
# 累计落袋净利润
REALIZED_PROFIT = 609633 

# 现有持仓: 多股多账户对齐
STOCKS = {
    '601669': {
        'name': '中国电建',
        'prefix': 'sh',
        'holdings': {
            '中信建投': {'shares': 191600, 'cost': 5.938}, 
            '国信证券': {'shares': 209300, 'cost': 5.963},
            '东方财富': {'shares': 1500,   'cost': 6.073}
        }
    },
    '000778': {
        'name': '新兴铸管',
        'prefix': 'sz',
        'holdings': {
            '国信证券': {'shares': 14400,  'cost': 4.180} # 2026-06-09 购入
        }
    }
}

# ================== 📱 经典 Server 酱推送 (Key 模式) ==================
def send_wechat(title, content):
    # 从 GitHub Secrets 获取 SERVERCHAN_KEY
    key = os.getenv("SERVERCHAN_KEY")
    if not key:
        print("❌ 未在 Secrets 中设置 SERVERCHAN_KEY，任务终止")
        return

    # 使用最原始的接口地址
    url = f"https://sctapi.ftqq.com/{key}.send"
    
    payload = {
        'title': title,
        'desp': content
    }
    
    try:
        res = requests.post(url, data=payload, timeout=15)
        if res.status_code == 200:
            print("✅ 微信推送成功")
        else:
            print(f"⚠️ 推送可能失败，返回码: {res.status_code}")
    except Exception as e:
        print(f"❌ 推送接口连接故障: {e}")

# ================== 🌐 批量行情抓取 ==================
def get_all_stock_data():
    """一次性批量抓取所有股票行情，减少连接次数"""
    queries = [f"{info['prefix']}{code}" for code, info in STOCKS.items()]
    url = f"http://qt.gtimg.cn/q={','.join(queries)}"
    prices = {}
    try:
        res = requests.get(url, timeout=10)
        res.encoding = 'gbk'
        lines = res.text.split('\n')
        for line in lines:
            if not line.strip(): continue
            parts = line.split('~')
            if len(parts) > 32:
                raw_code = parts[0].split('=')[0][-6:] 
                prices[raw_code] = {
                    'now': float(parts[3]), 
                    'last': float(parts[4]), 
                    'pct': float(parts[32])
                }
        return prices
    except Exception as e:
        print(f"⚠️ 行情获取失败: {e}")
    return None

# ================== 📊 核心资产计算 ==================
def calc_profit():
    prices = get_all_stock_data()
    if not prices or len(prices) < len(STOCKS): 
        print("❌ 行情获取不全，终止计算。")
        return None
    
    total_mv = 0
    total_floating = 0
    daily_change = 0
    
    # 动态构建个股明细部分的 Markdown
    stocks_md = ""
    
    for code, info in STOCKS.items():
        p = prices[code]
        stock_shares = 0
        stock_mv = 0
        stock_prof = 0
        acc_md_lines = []
        
        for acc_name, data in info['holdings'].items():
            mv = data['shares'] * p['now']
            prof = mv - (data['shares'] * data['cost'])
            
            stock_shares += data['shares']
            stock_mv += mv
            stock_prof += prof
            
            # 累加全局变动
            daily_change += (p['now'] - p['last']) * data['shares']
            
            # 记录账户分仓
            acc_md_lines.append(f"  - **{acc_name}**:浮盈 `{prof:+,.0f}` 元 *(现价:{p['now']:.3f}/成本:{data['cost']:.3f}, 持仓:{data['shares']:,}股)*")
            
        total_mv += stock_mv
        total_floating += stock_prof
        
        # 核心改进：为每只个股构建全局看板
        stocks_md += f"""
---
### 📋 {info['name']} ({code}) 看板
- 📊 **该股总数据**:
  - 总持仓量: `{stock_shares:,}` 股
  - 现存总市值: **{stock_mv:,.0f}** 元
  - **该股累计总盈亏**: **{stock_prof:+,.0f}** 元
- 🏦 **分仓对账明细**:
""" + "\n".join(acc_md_lines) + "\n"

    final_profit = total_floating + REALIZED_PROFIT

    # 4. 构建顶层全局总账 Markdown 报告
    content = f"""
## 💰 全局账户资产概览 (GitHub v8.5)
- **总盈亏 (含落袋)**: **{final_profit:+,.2f}** 元
- **持仓总市值**: **{total_mv:,.0f}** 元
- **今日总变动**: **{daily_change:+,.2f}** 元

> **总资产分类账目**
- 历史落袋盈亏: `{REALIZED_PROFIT:+,.0f}` (实钱)
- 现有持仓总浮盈: `{total_floating:+,.0f}` (浮钱)
{stocks_md}
📅 数据同步时间: {(datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')}
"""
    return final_profit, daily_change, content

# ================== 🏁 执行入口 ==================
if __name__ == "__main__":
    print(f"🚀 开始计算全局多股资产日报...")
    result = calc_profit()
    if result:
        tot, day, body = result
        title = f"📈 全局资产汇报: {tot:+,.0f} | 今日 {day:+,.0f}"
        send_wechat(title, body)
    else:
        print("❌ 无法联通行情接口，请检查网络")
