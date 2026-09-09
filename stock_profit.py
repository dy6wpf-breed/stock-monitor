# -*- coding: utf-8 -*-
"""
股票盈利监控系统 - GitHub Actions v9.3 (持仓变更同步版)
更新日志：
1. 【2026/09/08-09/09 交易同步】(依据国信/中信建投历史成交截图)
   - 中国电建(601669)：中信建投卖出 47900 股 @4.640 → 剩余 47900 股，成本不变 7.028
   - 中国人寿(601628)：中信建投 500 股 + 国信 600 股全部卖出清仓 → 移除该标的
   - 新增 港股通互联网ETF(513040, sh)：
       中信建投 263300 股 (113300@0.907 + 150000@0.908)，摊薄成本 0.9076
       国信证券 225000 股 @0.910
   - 新增 美年健康(002044, sz)：国信 38700 股 @4.680
   - 中国电建红利税补扣记录不影响股数，未计入
2. 【2026/09/09 落袋利润更新】已实现盈亏 -114,106.6 元并入 REALIZED_PROFIT
   (354127 → 240020.4)，人寿清仓 +278.6 / 电建减仓 -114,385.2
3. 【2026/09/09 东方财富账户同步】(依据东财持仓截图)
   - 中国电建东财成本 6.073 → 5.968 (券商摊薄口径)
   - 新增东财 港股通互联网ETF 600 股 @0.908
   - 全量成本口径切换为券商摊薄成本（由截图持仓盈亏反推，精度到分）：
     电建(中信) 7.028→9.419583、电建(东财) 6.073→5.967873、
     铸管 4.106→4.105476、ETF(中信/国信/东财) →0.907662/0.910082/0.908233、
     农产品 6.521→6.520745、美年 4.680→4.680534、有友 9.592→9.592498
5. 行情接口与双通道推送逻辑不变。
"""

import requests
import os
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

# ================== 💰 核心财务底牌 ==================
# 累计落袋净利润 = 354127 (历史 609633 - 255505.52) - 114106.6 (2026/09/08-09/09 平仓)
#   中国人寿清仓：+278.6 元  [600股*(38.49-38.209) + 500股*(38.39-38.170)]  ✅ 已于 2026/09/09 并入
#   中国电建减仓：-114,385.2 元 [47900股*(4.640-7.028)]                     ✅ 已于 2026/09/09 并入
# 注：中国电建红利税补扣记录不影响股数，未计入
REALIZED_PROFIT = 240020.4

# 现有持仓: 多股多账户对齐
STOCKS = {
    # 说明：以下 cost 全部采用券商摊薄成本口径，由 2026/09/09 收盘截图的
    #      "持仓盈亏" 反推得到（券商 App 只显示三位小数，直接抄会引入误差）
    '601669': {
        'name': '中国电建',
        'prefix': 'sh',
        'holdings': {
            '中信建投': {'shares': 47900, 'cost': 9.419583},
            '东方财富': {'shares': 1500,  'cost': 5.967873}
        }
    },
    '000778': {
        'name': '新兴铸管',
        'prefix': 'sz',
        'holdings': {
            '国信证券': {'shares': 14400, 'cost': 4.105476}
        }
    },
    '513040': {
        'name': '港股通互联网ETF',
        'prefix': 'sh',
        'holdings': {
            '中信建投': {'shares': 263300, 'cost': 0.907662},
            '国信证券': {'shares': 225000, 'cost': 0.910082},
            '东方财富': {'shares': 600,    'cost': 0.908233}
        }
    },
    '000061': {
        'name': '农 产 品',
        'prefix': 'sz',
        'holdings': {
            '国信证券': {'shares': 27900, 'cost': 6.520745}
        }
    },
    '002044': {
        'name': '美年健康',
        'prefix': 'sz',
        'holdings': {
            '国信证券': {'shares': 38700, 'cost': 4.680534}
        }
    },
    '603697': {
        'name': '有友食品',
        'prefix': 'sh',
        'holdings': {
            '国信证券': {'shares': 44200, 'cost': 9.592498}
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
# 💰 资产日报 (v9.3)

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
