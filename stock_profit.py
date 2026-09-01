# -*- coding: utf-8 -*-
"""
股票盈利监控系统 - GitHub Actions v9.2 (终极硬换行排版修复版)
更新日志：
1. 修复 Markdown 列表项与标题粘连问题，全面应用行尾双空格硬换行机制。
2. 保证手机端各券商分仓与汇总数据严格单行展示、层级分明。
"""

import requests
import os
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

# ================== 💰 核心财务底牌 ==================
# 累计落袋净利润 (609633 - 255505.52)
REALIZED_PROFIT = 354127 

# 现有持仓: 多股多账户对齐
STOCKS = {
    '601669': {
        'name': '中国电建',
        'prefix': 'sh',
        'holdings': {
            '中信建投': {'shares': 95800, 'cost': 7.028},
            '东方财富': {'shares': 1500,  'cost': 6.073}
        }
    },
    '000778': {
        'name': '新兴铸管',
        'prefix': 'sz',
        'holdings': {
            '国信证券': {'shares': 14400, 'cost': 4.106}
        }
    },
    '601628': {
        'name': '中国人寿',
        'prefix': 'sh',
        'holdings': {
            '中信建投': {'shares': 500,   'cost': 38.170},
            '国信证券': {'shares': 600,   'cost': 38.209}
        }
    },
    '000061': {
        'name': '农 产 品',
        'prefix': 'sz',
        'holdings': {
            '国信证券': {'shares': 27900, 'cost': 6.521}
        }
    },
    '603697': {
        'name': '有友食品',
        'prefix': 'sh',
        'holdings': {
            '国信证券': {'shares': 44200, 'cost': 9.592}
        }
    }
}

# ================== 📧 邮件配置 ==================
EMAIL_CONFIG = {
    'sender': 'bjlmwpf@163.com',
    'password': os.getenv('EMAIL_PASSWORD', ''),
    'receivers': ['bjlmwpf@163.com', '18810296859@163.com'],
    'smtp_server': 'smtp.163.com',
    'smtp_port': 465
}

# ================== 🌐 批量行情抓取 ==================
def get_all_stock_data():
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
    stock_details = []
    stocks_md = ""

    for code, info in STOCKS.items():
        p = prices[code]
        stock_prof = 0
        diff_today = p['now'] - p['last']
        stock_daily_change = 0
        acc_md_lines = []
        account_rows = []

        for acc_name, data in info['holdings'].items():
            mv = data['shares'] * p['now']
            prof = mv - (data['shares'] * data['cost'])
            acc_daily = diff_today * data['shares']

            stock_prof += prof
            stock_daily_change += acc_daily
            total_mv += mv
            daily_change += acc_daily

            # 行尾增加两个空格实现 Markdown 标准强制换行
            acc_md_lines.append(f"  * 🏦 {acc_name}：累计 `{prof:+,.0f}` | 今日 `{acc_daily:+,.0f}`  ")
            account_rows.append({
                'account': acc_name,
                'shares': data['shares'],
                'cost': data['cost'],
                'prof': prof,
                'mv': mv
            })

        total_floating += stock_prof

        stock_details.append({
            'code': code,
            'name': info['name'],
            'now': p['now'],
            'last': p['last'],
            'total_shares': sum(a['shares'] for a in account_rows),
            'total_mv': sum(a['mv'] for a in account_rows),
            'total_prof': stock_prof,
            'accounts': account_rows
        })

        sub_accounts_str = "\n".join(acc_md_lines)
        stocks_md += f"""
🔹 **{info['name']} ({code})** *现价: {p['now']:.2f}*  
* 累计总盈亏：**{stock_prof:+,.0f}** 元  
* 今日总变动：**{stock_daily_change:+,.0f}** 元  
{sub_accounts_str}
"""

    final_profit = total_floating + REALIZED_PROFIT

    fin = {
        'total_mv': total_mv,
        'total_floating': total_floating,
        'daily_change': daily_change,
        'final_profit': final_profit,
        'stock_details': stock_details
    }

    content = f"""
# 💰 资产日报 (v9.2)

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
    return final_profit, daily_change, content, fin

# ================== 📧 邮件 HTML 生成 ==================
def create_fancy_email_html(fin):
    p_color = "#e64340" if fin['total_floating'] >= 0 else "#09bb07"
    d_color = "#e64340" if fin['daily_change'] >= 0 else "#09bb07"

    detail_blocks = ""
    for s in fin['stock_details']:
        acc_rows = ""
        for a in s['accounts']:
            acc_rows += f"""
            <tr style="border-top:1px solid #f2f2f2; font-size:13px;">
                <td style="padding:12px 5px;"><b>{a['account']}</b><br><small style="color:#666;">{a['shares']:,}股</small></td>
                <td align="right" style="padding:12px 5px;">{s['now']:.3f}<br><small style="color:#666;">成本:{a['cost']:.3f}</small></td>
                <td align="right" style="padding:12px 5px; color:{'#e64340' if a['prof']>=0 else '#09bb07'}; font-weight:bold;">{a['prof']:+,.0f}</td>
                <td align="right" style="padding:12px 5px;">{(a['mv']/fin['total_mv']*100):.1f}%</td>
            </tr>"""

        detail_blocks += f"""
        <div style="margin-top:25px; border:1px solid #e0e0e0; border-radius:12px; padding:18px; background:#fff;">
            <div style="margin-bottom:12px;">
                <span style="font-size:16px; font-weight:bold; color:#333;">📋 {s['name']} ({s['code']})</span>
                <span style="float:right; font-size:14px; color:#666;">现价: <b>{s['now']:.3f}</b></span>
            </div>
            <table width="100%" cellspacing="0" cellpadding="6" style="background:#f8f9fa; border-radius:6px; font-size:12px; text-align:center; margin-bottom:15px; color:#555;">
                <tr>
                    <td style="border-right:1px solid #eee;">总持仓<br><b style="color:#333; font-size:13px;">{s['total_shares']:,} 股</b></td>
                    <td style="border-right:1px solid #eee;">总市值<br><b style="color:#333; font-size:13px;">{s['total_mv']:,.0f}</b></td>
                    <td>该股累计总盈亏<br><b style="color:{'#e64340' if s['total_prof']>=0 else '#09bb07'}; font-size:14px;">{s['total_prof']:+,.0f}</b></td>
                </tr>
            </table>
            <table width="100%" cellspacing="0" cellpadding="0" style="font-size:14px; border-collapse: collapse;">
                <thead>
                    <tr style="color:#888; font-size:12px; text-align:left;">
                        <th style="padding:5px;">分仓账户</th>
                        <th align="right" style="padding:5px;">现价/成本</th>
                        <th align="right" style="padding:5px;">分仓盈亏</th>
                        <th align="right" style="padding:5px;">占总仓位</th>
                    </tr>
                </thead>
                <tbody>
                    {acc_rows}
                </tbody>
            </table>
        </div>"""

    return f"""
    <html>
    <body style="background:#f0f2f5; padding:20px; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;">
        <div style="max-width:600px; margin:auto; background:white; border-radius:16px; overflow:hidden; box-shadow:0 8px 24px rgba(0,0,0,0.08);">
            <div style="background: linear-gradient(135deg, #1a1a1a 0%, #3a3a3a 100%); padding:40px 20px; color:white; text-align:center;">
                <div style="opacity:0.7; font-size:14px; letter-spacing:1px;">账户总盈亏 (含落袋)</div>
                <div style="font-size:42px; font-weight:bold; margin:10px 0;">{fin['final_profit']:+,.2f}</div>
                <div style="margin-top:15px;">
                    <span style="background:{d_color}; padding:6px 16px; border-radius:50px; font-weight:bold; font-size:14px;">
                        今日总变动 {fin['daily_change']:+,.0f}
                    </span>
                </div>
            </div>
            <div style="padding:24px 20px 0px 20px;">
                <table width="100%" cellspacing="10" cellpadding="0" style="text-align:center;">
                    <tr>
                        <td width="33.33%" style="background:#f8f9fa; padding:12px; border-radius:8px;">
                            <span style="font-size:12px; color:#666;">总浮盈</span><br>
                            <b style="color:{p_color}; font-size:16px;">{fin['total_floating']:+,.0f}</b>
                        </td>
                        <td width="33.33%" style="background:#f8f9fa; padding:12px; border-radius:8px;">
                            <span style="font-size:12px; color:#666;">落袋利润</span><br>
                            <b style="color:#333; font-size:16px;">{REALIZED_PROFIT:+,.0f}</b>
                        </td>
                        <td width="33.33%" style="background:#f8f9fa; padding:12px; border-radius:8px;">
                            <span style="font-size:12px; color:#666;">总市值</span><br>
                            <b style="color:#333; font-size:16px;">{fin['total_mv']:,.0f}</b>
                        </td>
                    </tr>
                </table>
            </div>
            <div style="padding:10px 20px 30px 20px;">
                {detail_blocks}
            </div>
        </div>
    </body>
    </html>
    """

def send_email(fin):
    if not EMAIL_CONFIG['password']:
        print("💡 未在 GitHub Secrets 中检测到 EMAIL_PASSWORD，跳过邮件发送")
        return

    try:
        msg = MIMEMultipart()
        msg['Subject'] = Header(f"📊 资产对账单 | {fin['final_profit']:+,.0f}", 'utf-8')
        msg['From'] = EMAIL_CONFIG['sender']
        msg['To'] = ', '.join(EMAIL_CONFIG['receivers'])
        msg.attach(MIMEText(create_fancy_email_html(fin), 'html', 'utf-8'))

        server = smtplib.SMTP_SSL(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'], timeout=15)
        server.login(EMAIL_CONFIG['sender'], EMAIL_CONFIG['password'])
        server.sendmail(EMAIL_CONFIG['sender'], EMAIL_CONFIG['receivers'], msg.as_string())
        server.quit()
        print("✅ 邮件渠道报表已发出")
    except Exception as e:
        print(f"❌ 邮件渠道失败: {e}")

# ================== 📱 双 Server 酱通道配置 ==================
def send_wechat(title, content):
    keys = []
    env_key = os.getenv("SERVERCHAN_KEY")
    if env_key:
        keys.append(env_key)

    new_seed_key = "SCT369340TItDB979ZF0vvE5MOoI5sZyci"
    keys.append(new_seed_key)

    keys = list(set(keys))
    if not keys:
        print("❌ 未检测到任何可用的 SERVERCHAN_KEY，任务终止")
        return

    payload = {'title': title, 'desp': content}

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

# ================== 🏁 执行入口 ==================
if __name__ == "__main__":
    print(f"🚀 开始计算全局多股资产日报...")
    result = calc_profit()
    if result:
        tot, day, body, fin = result
        title = f"📈 全局资产汇报: {tot:+,.0f} | 今日 {day:+,.0f}"
        send_wechat(title, body)
        send_email(fin)
    else:
        print("❌ 运行失败，未能成功提取核心行情")
