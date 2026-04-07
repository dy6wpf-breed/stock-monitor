# -*- coding: utf-8 -*-
"""
股票盈利监控系统 - GitHub Actions v8.3 (经典Server酱接口 + 三账户全齐版)
"""

import requests
import os
from datetime import datetime, timedelta

# ================== 📌 核心财务底牌 (2026-03-20) ==================
# 累计落袋净利润: 609,633 元
REALIZED_PROFIT = 609633 

# 现有持仓: 中国电建 (601669) - 三账户对齐
STOCKS = {
    '601669': {'name': '中国电建', 'prefix': 'sh', 'holdings': {
        '中信建投': {'shares': 191600, 'cost': 5.938}, 
        '国信证券': {'shares': 209300, 'cost': 5.963},
        '东方财富': {'shares': 1500,   'cost': 6.073}
    }}
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

# ================== 🌐 行情抓取 ==================
def get_stock_data(code, prefix):
    url = f"http://qt.gtimg.cn/q={prefix}{code}"
    try:
        res = requests.get(url, timeout=10)
        data = res.text.split('~')
        if len(data) > 32:
            return float(data[3]), float(data[4]), float(data[32])
    except: pass
    return 0.0, 0.0, 0.0

# ================== 📊 核心资产计算 ==================
def calc_profit():
    # 1. 获取最新价
    price_now, price_last, pct = get_stock_data('601669', 'sh')
    if price_now == 0: return None
    
    cfg = STOCKS['601669']['holdings']
    
    # 2. 分账户盈亏计算
    zx_prof = cfg['中信建投']['shares'] * (price_now - cfg['中信建投']['cost'])
    gx_prof = cfg['国信证券']['shares'] * (price_now - cfg['国信证券']['cost'])
    df_prof = cfg['东方财富']['shares'] * (price_now - cfg['东方财富']['cost'])
    
    # 3. 汇总数据
    total_shares = sum(h['shares'] for h in cfg.values())
    total_mv = total_shares * price_now
    total_floating = zx_prof + gx_prof + df_prof
    final_profit = total_floating + REALIZED_PROFIT
    daily_change = (price_now - price_last) * total_shares

    # 4. 构建 Markdown 报告
    content = f"""
## 💰 账户资产概览 (GitHub v8.3)
- **总盈亏 (含落袋)**: **{final_profit:+,.2f}** 元
- **持仓总市值**: **{total_mv:,.0f}** 元
- **今日总变动**: **{daily_change:+,.2f}** 元 ({pct:+.2f}%)

> **资产分类账目**
- 历史落袋盈亏: `{REALIZED_PROFIT:+,.0f}` (实钱)
- 现有持仓浮盈: `{total_floating:+,.0f}` (浮钱)

---
## 👜 分账户对账单
- **中信建投**: `{zx_prof:+,.0f}` ({cfg['中信建投']['shares']:,}股)
- **国信证券**: `{gx_prof:+,.0f}` ({cfg['国信证券']['shares']:,}股)
- **东方财富**: `{df_prof:+,.0f}` ({cfg['东方财富']['shares']:,}股)

📅 数据同步时间: {(datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')}
"""
    return final_profit, daily_change, content

# ================== 🏁 执行入口 ==================
if __name__ == "__main__":
    print(f"🚀 开始计算资产日报...")
    result = calc_profit()
    if result:
        tot, day, body = result
        # 标题简洁直观
        title = f"📈 资产汇报: {tot:+,.0f} | 今日 {day:+,.0f}"
        send_wechat(title, body)
    else:
        print("❌ 无法联通行情接口，请检查网络")
