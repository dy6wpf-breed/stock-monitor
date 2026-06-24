# ================== 📊 核心资产计算 (v8.7 极致纯净版) ==================
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
            
            # 全局大账本累加
            total_mv += mv
            daily_change += acc_daily
            
            # 券商分仓：只保留累计盈亏和今日盈亏
            acc_md_lines.append(f"   • {acc_name}：累计 `{prof:+,.0f}` | 今日 `{acc_daily:+,.0f}`")
            
        total_floating += stock_prof
        
        # 个股看板：去除市值，只留现价、累计和今日
        stocks_md += f"""
🔹 **{info['name']} ({code})** *现价: {p['now']:.2f}*
   • 累计总盈亏：**{stock_prof:+,.0f}** 元
   • 今日总变动：**{stock_daily_change:+,.0f}** 元
""" + "\n".join(acc_md_lines) + "\n\n"

    final_profit = total_floating + REALIZED_PROFIT

    # 构建 Markdown 报告
    content = f"""
# 💰 资产日报 (v8.7)

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
