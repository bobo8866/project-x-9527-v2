import yfinance as yf
import pandas as pd
import requests
import os
from datetime import datetime
import pytz

HISTORY_FILE = "history.csv"

# === 1. 获取所有数据 (只抓取能自动化的) ===
def get_all_data():
    tickers = {
        "US10Y": "^TNX", "DXY": "DX-Y.NYB", "VIX": "^VIX", "HYG": "HYG",
        "USDCNH": "CNH=X", "GOLD": "GC=F", "SILVER": "SI=F", "COPPER": "HG=F"
    }
    raw_data = {}
    
    # Yahoo
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
            raw_data[name] = {"value": "N/A", "trend": "⚪"}

    # FRED数据 (TGA & RRP)
    try:
        df = pd.read_csv("https://fred.stlouisfed.org/graph/fredgraph.csv?id=WTREGEN")
        raw_data['TGA'] = f"${df.iloc[-1, 1]:.0f}B"
    except: raw_data['TGA'] = "N/A"

    try:
        df = pd.read_csv("https://fred.stlouisfed.org/graph/fredgraph.csv?id=RRPONTSYD")
        raw_data['RRP'] = f"${df.iloc[-1, 1]:.0f}B"
    except: raw_data['RRP'] = "N/A"

    # 加密数据
    try:
        r = requests.get("https://api.coingecko.com/api/v3/global", timeout=10)
        btc_d = r.json()['data']['market_cap_percentage']['btc']
        raw_data['BTC.D'] = f"{btc_d:.1f}%"
    except: raw_data['BTC.D'] = "N/A"

    try:
        r = requests.get("https://stablecoins.llama.fi/stablecoins?includePrices=true", timeout=10)
        assets = r.json()['peggedAssets']
        total = sum(a['circulating']['peggedUSD'] for a in assets if a['symbol'] in ['USDT','USDC','DAI','FDUSD'])
        raw_data['STABLE_CAP'] = f"${total/1e9:.1f}B"
    except: raw_data['STABLE_CAP'] = "N/A"
    
    try:
        r = requests.get("https://api.alternative.me/fng/", timeout=10)
        item = r.json()['data'][0]
        raw_data['FEAR'] = f"{item['value']}"
    except: raw_data['FEAR'] = "N/A"

    return raw_data

# === 2. 更新历史 (只存纯净数据) ===
def update_history(data):
    today = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d')
    
    def get_val(key):
        if key not in data: return ""
        val = data[key]['value'] if isinstance(data[key], dict) else data[key]
        return val if val != "N/A" else ""

    # 按照你的要求排序
    new_row = {
        "日期": today,
        "US10Y": get_val('US10Y'),
        "DXY": get_val('DXY'),
        "RRP": get_val('RRP'),
        "VIX": get_val('VIX'),
        "HYG": get_val('HYG'),
        "黄金": get_val('GOLD'),
        "白银": get_val('SILVER'),
        "铜": get_val('COPPER'),
        "BTC.D": data['BTC.D'],
        "稳定币": data['STABLE_CAP'],
        "TGA": data['TGA'],
        "恐慌": data['FEAR'],
        "汇率": get_val('USDCNH')
    }
    
    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE)
        # 清理旧数据，确保列一致
        df = df.reindex(columns=new_row.keys())
        df = df[df["日期"] != today]
    else:
        df = pd.DataFrame(columns=new_row.keys())
    
    new_df = pd.DataFrame([new_row])
    df = pd.concat([df, new_df], ignore_index=True)
    df = df.sort_values(by="日期", ascending=False)
    df.to_csv(HISTORY_FILE, index=False, encoding="utf-8-sig")
    return df

# === 3. 生成网页 ===
def generate_html(current_data, history_df):
    beijing_time = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M')
    history_html = history_df.head(60).to_html(index=False, classes="history-table", border=0)
    
    # 依然保留战术链接，方便你手动查看
    links = {
        "GAS": "https://mct.xyz/gasnow",
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
        "MMFI": "https://www.tradingview.com/symbols/MMFI/"
    }

    def cell(link, label):
        return f"<a href='{link}' target='_blank' class='btn'>{label}</a>"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>秘密档案馆</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: sans-serif; margin:0; padding:15px; background:#f0f2f5; }}
            .container {{ max-width: 1200px; margin:0 auto; }}
            h1 {{ text-align:center; color:#333; }}
            .time {{ text-align:center; color:#888; font-size:0.9em; margin-bottom:20px; }}
            .card {{ background:white; padding:15px; border-radius:10px; margin-bottom:20px; box-shadow:0 2px 5px rgba(0,0,0,0.05); }}
            
            /* 历史表格 (纯净版) */
            .history-table {{ width:100%; border-collapse:collapse; font-size:0.9em; white-space:nowrap; }}
            .history-table th {{ background:#333; color:white; padding:8px; }}
            .history-table td {{ padding:6px; text-align:center; border-bottom:1px solid #ddd; }}
            .history-table tr:nth-child(even) {{ background-color:#f9f9f9; }}
            
            /* 战术网格 */
            .grid-box {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(120px, 1fr)); gap:10px; }}
            .grid-item {{ background:#fafafa; padding:10px; text-align:center; border:1px solid #eee; border-radius:8px; }}
            .grid-label {{ display:block; font-size:0.8em; color:#888; margin-bottom:5px; }}
            
            .btn {{ background:#eef; color:#0066cc; padding:4px 10px; border-radius:4px; text-decoration:none; font-size:0.9em; border:1px solid #cce5ff; display:block; }}
            .btn:hover {{ background:#0066cc; color:white; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📂 每日金融档案</h1>
            <div class="time">最后归档: {beijing_time}</div>
            
            <div class="card">
                <h2>📜 历史数据 (自动归档)</h2>
                <div style="overflow-x:auto;">
                    {history_html}
                </div>
            </div>

            <div class="card">
                <h2>⚔️ 手动统计工具箱</h2>
                <div class="grid-box">
                    <div class="grid-item"><span class="grid-label">USDT溢价</span>{cell(links['USDT'], "非小号")}</div>
                    <div class="grid-item"><span class="grid-label">AH溢价</span>{cell(links['AH'], "东方财富")}</div>
                    <div class="grid-item"><span class="grid-label">Gas Fee</span>{cell(links['GAS'], "GasNow")}</div>
                    <div class="grid-item"><span class="grid-label">资金费率</span>{cell(links['FUNDING'], "CoinGlass")}</div>
                    <div class="grid-item"><span class="grid-label">北向资金</span>{cell(links['NORTH'], "东方财富")}</div>
                    <div class="grid-item"><span class="grid-label">贝莱德BTC</span>{cell(links['BLK_BTC'], "资金流")}</div>
                    <div class="grid-item"><span class="grid-label">贝莱德ETH</span>{cell(links['BLK_ETH'], "资金流")}</div>
                    <div class="grid-item"><span class="grid-label">短手成本</span>{cell(links['STH'], "CoinGlass")}</div>
                    <div class="grid-item"><span class="grid-label">稳定币流向</span>{cell(links['STABLE_FLOW'], "CryptoQuant")}</div>
                    <div class="grid-item"><span class="grid-label">MMFI宽度</span>{cell(links['MMFI'], "TradingView")}</div>
                    <div class="grid-item"><span class="grid-label">MVRV逃顶</span>{cell(links['MVRV'], "Magazine")}</div>
                    <div class="grid-item"><span class="grid-label">Ahr999抄底</span>{cell(links['AHR999'], "999")}</div>
                    <div class="grid-item"><span class="grid-label">披萨指数</span>{cell(links['PIZZA'], "Pizza")}</div>
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
