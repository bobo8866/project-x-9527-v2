import yfinance as yf
import pandas as pd
import requests
import os
from datetime import datetime
import pytz

HISTORY_FILE = "history.csv"

# === 1. 获取数据 ===
def get_all_data():
    tickers = {
        "US10Y": "^TNX", "DXY": "DX-Y.NYB", "VIX": "^VIX", "HYG": "HYG",
        "USDCNH": "CNH=X", "GOLD": "GC=F", "SILVER": "SI=F", "COPPER": "HG=F",
        "AH_PREMIUM": "HSCAHPI.HK"
    }
    raw_data = {}
    
    for name, ticker in tickers.items():
        try:
            stock = yf.Ticker(ticker)
            price = stock.fast_info['last_price']
            prev = stock.fast_info['previous_close']
            if name == "US10Y": val_str = f"{price:.2f}%"
            else: val_str = f"{price:.2f}"
            
            raw_data[name] = {
                "value": val_str,
                "trend": "🔴" if price > prev else "🟢" if price < prev else "⚪"
            }
        except: 
            # 如果获取失败，标记为 Link，后续生成按钮
            raw_data[name] = {"value": "Link", "trend": "⚪"}

    # BTC.D
    try:
        r = requests.get("https://api.coingecko.com/api/v3/global", timeout=10)
        btc_d = r.json()['data']['market_cap_percentage']['btc']
        raw_data['BTC.D'] = f"{btc_d:.1f}%"
    except: raw_data['BTC.D'] = "N/A"

    # Stablecoin
    try:
        r = requests.get("https://stablecoins.llama.fi/stablecoins?includePrices=true", timeout=10)
        assets = r.json()['peggedAssets']
        total = sum(a['circulating']['peggedUSD'] for a in assets if a['symbol'] in ['USDT','USDC','DAI','FDUSD'])
        raw_data['STABLE_CAP'] = f"${total/1e9:.1f}B"
    except: raw_data['STABLE_CAP'] = "N/A"

    # TGA
    try:
        df = pd.read_csv("https://fred.stlouisfed.org/graph/fredgraph.csv?id=WTREGEN")
        raw_data['TGA'] = f"${df.iloc[-1, 1]:.0f}B"
    except: raw_data['TGA'] = "N/A"
    
    # Fear
    try:
        r = requests.get("https://api.alternative.me/fng/", timeout=10)
        item = r.json()['data'][0]
        raw_data['FEAR'] = f"{item['value']}"
    except: raw_data['FEAR'] = "N/A"

    # Gas (增加失败处理)
    try:
        r = requests.get("https://beaconcha.in/api/v1/execution/gasnow", timeout=10)
        gas = int(r.json()['data']['rapid'] / 1e9)
        raw_data['GAS'] = f"{gas}"
    except: raw_data['GAS'] = "Link" # 失败则显示链接

    return raw_data

# === 2. 更新历史 ===
def update_history(data):
    today = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d')
    
    # 历史记录里，如果没抓到数据，就留空，保持表格整洁
    def get_val(key):
        val = data[key]['value'] if isinstance(data[key], dict) else data[key]
        return val if val != "Link" else ""

    new_row = {
        "日期": today,
        "US10Y": get_val('US10Y'),
        "DXY": get_val('DXY'),
        "VIX": get_val('VIX'),
        "HYG": get_val('HYG'),
        "黄金": get_val('GOLD'),
        "铜": get_val('COPPER'),
        "BTC.D": data['BTC.D'],
        "稳定币": data['STABLE_CAP'],
        "TGA": data['TGA'],
        "恐慌": data['FEAR'],
        "GAS": get_val('GAS'), # Gas特殊处理
        "汇率": get_val('USDCNH'),
        "AH溢价": get_val('AH_PREMIUM')
    }
    
    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE)
        df = df[df["日期"] != today]
    else:
        df = pd.DataFrame(columns=new_row.keys())
    
    new_df = pd.DataFrame([new_row])
    df = pd.concat([df, new_df], ignore_index=True)
    df = df.sort_values(by="日期", ascending=False)
    df.to_csv(HISTORY_FILE, index=False, encoding="utf-8-sig")
    return df

# === 3. 生成 HTML ===
def generate_html(current_data, history_df):
    beijing_time = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M')
    history_html = history_df.head(60).to_html(index=False, classes="history-table", border=0)
    
    links = {
        "RRP": "https://www.newyorkfed.org/markets/desk-operations/reverse-repo",
        "MMFI": "https://www.tradingview.com/symbols/MMFI/",
        "USDT": "https://www.feixiaohao.com/data/stable",
        "NORTH": "https://data.eastmoney.com/hsgt/index.html",
        "AH": "https://quote.eastmoney.com/gb/zsHSAHP.html",
        "STH": "https://www.coinglass.com/pro/i/short-term-holder-price",
        "BLK_BTC": "https://www.coinglass.com/zh/bitcoin-etf",
        "BLK_ETH": "https://www.coinglass.com/zh/eth-etf",
        "STABLE_FLOW": "https://cryptoquant.com/asset/stablecoin/chart/exchange-flows/exchange-netflow-total?exchange=all_exchange&window=DAY&sma=0&ema=0&priceScale=log&metricScale=linear&chartStyle=column",
        "MVRV": "https://www.bitcoinmagazinepro.com/charts/mvrv-zscore/",
        "AHR999": "https://9992100.xyz/",
        "PIZZA": "https://www.pizzint.watch/",
        "FUNDING": "https://www.coinglass.com/zh/FundingRate",
        "GAS": "https://mct.xyz/gasnow"
    }

    def cell(val, link, label="查看"):
        # 如果是字典(Yahoo数据)取value
        if isinstance(val, dict): val = val['value']
        
        if val == "N/A" or val == "Link": 
            return f"<a href='{link}' target='_blank' class='btn'>{label}</a>"
        return f"<a href='{link}' target='_blank' class='val-link'>{val}</a>"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>秘密档案馆</title>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: sans-serif; margin:0; padding:20px; background:#f4f4f4; }}
            .container {{ max-width: 1200px; margin:0 auto; }}
            h1, h2 {{ text-align:center; color:#333; }}
            .time {{ text-align:center; color:#888; font-size:0.9em; }}
            .card {{ background:white; padding:20px; border-radius:10px; margin-bottom:20px; box-shadow:0 2px 5px rgba(0,0,0,0.05); }}
            
            /* 历史表格 */
            .history-table {{ width:100%; border-collapse:collapse; margin-top:10px; font-size:0.9em; }}
            .history-table th {{ background:#333; color:white; padding:8px; }}
            .history-table td {{ padding:6px; text-align:center; border-bottom:1px solid #ddd; }}
            .history-table tr:nth-child(even) {{ background-color:#f9f9f9; }}
            
            /* 战术网格 */
            .grid-box {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(140px, 1fr)); gap:10px; }}
            .grid-item {{ background:#fafafa; padding:10px; text-align:center; border:1px solid #eee; border-radius:8px; }}
            .grid-label {{ display:block; font-size:0.8em; color:#888; }}
            .grid-value {{ font-weight:bold; color:#333; }}
            
            .btn {{ background:#eef; color:#0066cc; padding:2px 8px; border-radius:4px; text-decoration:none; font-size:0.9em; }}
            .val-link {{ color:#333; text-decoration:none; border-bottom:1px dotted #ccc; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📂 每日金融档案</h1>
            <div class="time">最后归档: {beijing_time}</div>
            
            <div class="card">
                <h2>📜 历史数据 (Daily Log)</h2>
                <div style="overflow-x:auto;">
                    {history_html}
                </div>
            </div>

            <div class="card">
                <h2>⚔️ 战术面板 (Current Status)</h2>
                <div class="grid-box">
                    <div class="grid-item"><span class="grid-label">TGA余额</span>{current_data['TGA']}</div>
                    <div class="grid-item"><span class="grid-label">恐慌指数</span>{current_data['FEAR']}</div>
                    
                    <!-- 修复 Gas 显示 -->
                    <div class="grid-item"><span class="grid-label">Gas Fee</span>{cell(current_data['GAS'], links['GAS'])}</div>
                    
                    <!-- 修复 AH 显示 (加到面板里) -->
                    <div class="grid-item"><span class="grid-label">AH溢价</span>{cell(current_data['AH_PREMIUM'], links['AH'])}</div>

                    <div class="grid-item"><span class="grid-label">资金费率</span>{cell("Link", links['FUNDING'])}</div>
                    <div class="grid-item"><span class="grid-label">北向资金</span>{cell("Link", links['NORTH'])}</div>
                    <div class="grid-item"><span class="grid-label">贝莱德BTC</span>{cell("Link", links['BLK_BTC'])}</div>
                    <div class="grid-item"><span class="grid-label">贝莱德ETH</span>{cell("Link", links['BLK_ETH'])}</div>
                    <div class="grid-item"><span class="grid-label">短手成本</span>{cell("Link", links['STH'])}</div>
                    <div class="grid-item"><span class="grid-label">稳定币流向</span>{cell("Link", links['STABLE_FLOW'])}</div>
                    <div class="grid-item"><span class="grid-label">MMFI宽度</span>{cell("Link", links['MMFI'])}</div>
                    <div class="grid-item"><span class="grid-label">MVRV逃顶</span>{cell("Link", links['MVRV'])}</div>
                    <div class="grid-item"><span class="grid-label">Ahr999抄底</span>{cell("Link", links['AHR999'])}</div>
                    <div class="grid-item"><span class="grid-label">披萨指数</span>{cell("Link", links['PIZZA'])}</div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html

if __name__ == "__main__":
    print("开始归档...")
    data = get_all_data()
    df = update_history(data)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(generate_html(data, df))
    print("完成")
