# -*- coding: utf-8 -*-
"""
股票盈利监控系统 - GitHub Actions v8.8 (极致纯净 & 双通道推送版)
更新日志：
1. 集成原有 Secrets 动态 Key 机制与新写入的硬编码 SeedKey。
2. 保持 v8.7 个股及分仓极致纯净版输出（只保留累计盈亏与今日盈亏）。
"""

import requests
import os
from datetime import datetime, timedelta

# ================== 💰 核心财务底牌 ==================
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
            '国信证券': {'shares': 14400,  'cost': 4.180}  # 2026-06-09 购入
        }
    }
}

# ================== 📱 双 Server 酱通道配置 ==================
def send_wechat(title, content):
    """支持双 Key 同时推送，多通道分发互为备份"""
    keys = []
    
    # 通道 1：从 GitHub Secrets 动态获取的旧 Key
    env_key = os.getenv("SERVERCHAN_KEY")
    if env_key:
        keys.append(env_key)
    else:
        print("💡 未在 GitHub Secrets 中检测到 SERVERCHAN_KEY，将跳过此环境变量通道")

    # 通道 2：您刚刚提供的全新固定 SeedKey
    new_seed_key = "SCT369340TItDB979ZF0vvE5MOoI5sZyci"
    keys.append(new_seed_key)

    # 去重，防止配置了相同 Key 导致重复发送
    keys = list(set(keys))

    if not keys:
        print("❌ 未检测到任何可用的 SERVERCHAN_KEY，任务终止")
        return

    payload = {
        'title': title,
        'desp': content
    }
    
    # 遍历所有配置的 Key 进行群发
    for index, key in enumerate(keys, 1):
        url = f"https://sctapi.ftqq.com/{key}.send"
        try:
            res = requests.post(url, data=payload, timeout=15)
            if res.status_code == 200:
                print(f"✅ 通道 [{index}] 推送成功")
            else:
                print(f"⚠️ 通道 [{index}] 推送异常，状态码: {res.status_code}")
        except Exception as e:
            print(f"❌ 通道 [{index}] 连接故障: {e}")

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
    
    # 动态构建个股极简明细
    stocks_md = ""
    
    for code, info in STOCKS.items():
        p = prices[code]
        stock_prof = 0
        
        # 计算该股今日单股变动价差
        diff_today = p['now'] - p['last']
        stock_daily_change = 0
        
        acc_md_lines = []
        
        for acc_name, data in info['holdings'].items():
            mv = data['shares'] * p['now']
            prof = mv - (data['shares'] * data['cost'])
            acc_daily = diff_today * data['shares']
            
            stock_prof += prof
            stock_daily_change += acc_daily
            
            # 全局大账本数据累加
            total_mv += mv
            daily_change += acc_daily
            
            # 券商分仓：极致精简，只保留累计盈亏和今日盈亏
            acc_md_lines.append(f"   • {acc_name}：累计 `{prof:+,.0f}` | 今日 `{acc_daily:+,.0f}`")
            
        total_floating += stock_prof
        
        # 个股看板：聚焦累计和今日两个利润指标
        stocks_md += f"""
🔹 **{info['name']} ({code})** *现价: {p['now']:.2f}*
   • 累计总盈亏：**{stock_prof:+,.0f}** 元
   • 今日总变动：**{stock_daily_change:+,.0f}** 元
""" + "\n".join(acc_md_lines) + "\n\n"

    final_profit = total_floating + REALIZED_PROFIT

    # 构建全局总账 Markdown 报告
    content = f"""
# 💰 资产日报 (v8.8)

### 📊 核心大账本
* **总盈亏(含落袋)**：**{final_profit:+,.2f}** 元
* **今日总变动**：**{daily_change:+,.2f}** 元
* **当前总市值**：{total_mv:,.0f} 元

---

### 🗂️ 分类账目
* 历史已落袋：`{REALIZED_PROFIT:+,.0f}` (实钱)
* 持仓总浮盈：`{total_floating:+,.0f}` (浮钱)

---

### 📈 个股及分仓明细
{stocks_md}
⏱️ 同步：{(datetime.utcnow() + timedelta(hours=8)).strftime('%H:%M')}
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
        print("❌ 运行失败，未能成功提取核心行情")
