# -*- coding: utf-8 -*-
"""
股票盈利监控系统 - GitHub Actions v8.1 (全仓电建对齐版)
"""

import requests
import os
from datetime import datetime, timedelta

# ================== 📌 核心知识库数据 (2026-03-20 录入) ==================
# 历史累计落袋损益: 609,633 元
REALIZED_PROFIT = 609633 

# 现有持仓: 中国电建 (601669)
STOCKS = {
    '601669': {'name': '中国电建', 'prefix': 'sh', 'holdings': {
        '中信建投': {'shares': 191600, 'cost': 5.938}, 
        '国信证券': {'shares': 209300, 'cost': 5.963}
    }}
}

# ================== 📱 推送逻辑 ==================
def send_wechat(title, content):
    # 优先从 GitHub Secrets 获取 Key，如果没有则使用代码里的 V3 Key
    key = os.getenv("SERVERCHAN_KEY") or "sctp19090tnwug12v5ljfqyvsgugxfrv"
    
    # 根据 Key 类型自动选择 URL (如果是 sctp 开头则使用 V3 专属 URL)
    if key.startswith("sctp"):
        url = f"https://19090.push.ft07.com/send/{key}.send"
    else:
        url = f"https://sctapi.ftqq.com/{key}.send"
        
    try:
        requests.post(url, data={'title': title, 'desp': content}, timeout=15)
        print("✅ 微信推送指令已发出")
    except Exception as e:
        print(f"❌ 推送失败: {e}")

# ================== 🌐 获取行情逻辑 ==================
def get_stock_data(code, prefix):
    url = f"http://qt.gtimg.cn/q={prefix}{code}"
    try:
        res = requests.get(url, timeout=10)
        data = res.text.split('~')
        if len(data) > 32:
            return float(data[3]), float(data[4]), float(data[32])
    except: pass
    return 0.0, 0.0, 0.0

# ================== 📊 核心计算逻辑 ==================
def calc_profit():
    # 1. 获取行情
    price_now, price_last, pct = get_stock_data('601669', 'sh')
    if price_now == 0: return None
    
    # 2. 持仓详情计算
    zx_cfg = STOCKS['601669']['holdings']['中信建投']
    gx_cfg = STOCKS['601669']['holdings']['国信证券']
    
    zx_prof = zx_cfg['shares'] * (price_now - zx_cfg['cost'])
    gx_prof = gx_cfg['shares'] * (price_now - gx_cfg['cost'])
    
    total_shares = zx_cfg['shares'] + gx_cfg['shares']
    total_mv = total_shares * price_now
    total_floating = zx_prof + gx_prof
    final_total_profit = total_floating + REALIZED_PROFIT
    
    # 3. 动态指标
    daily_change = (price_now - price_last) * total_shares
    avg_cost = ((zx_cfg['shares']*zx_cfg['cost']) + (gx_cfg['shares']*gx_cfg['cost'])) / total_shares

    # 4. 构建 Markdown 内容
    content = f"""
## 💰 账户资产概览 (GitHub v8.1)
- **总损益 (含落袋)**: **{final_total_profit:+,.2f}** 元
- **持仓总市值**: **{total_mv:,.0f}** 元
- **今日总变动**: **{daily_change:+,.2f}** 元 ({pct:+.2f}%)

> **资产账目明细**
- 历史落袋盈亏: `{REALIZED_PROFIT:+,.0f}` (实钱)
- 现有持仓浮盈: `{total_floating:+,.0f}` (浮钱)
- 综合持仓成本: `{avg_cost:.3f}`

---
## 👜 分账户对账
- **中信建投**: `{zx_prof:+,.0f}` ({zx_cfg['shares']:,}股)
- **国信证券**: `{gx_prof:+,.0f}` ({gx_cfg['shares']:,}股)

📅 同步时间: {(datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')}
"""
    return final_total_profit, daily_change, content

# ================== 🏁 主程序 ==================
if __name__ == "__main__":
    result = calc_profit()
    if result:
        tot, day, body = result
        send_wechat(f"🚀 资产日报: {tot:+,.0f} | 变动 {day:+,.0f}", body)
    else:
        print("❌ 行情获取失败，任务终止")
