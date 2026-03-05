import yfinance as yf
import pandas as pd
import requests
import os
from datetime import datetime
import pytz

# === 配置区 ===
HISTORY_FILE = "history.csv"

# === 1. 获取所有数据 ===
def get_all_data():
    tickers = {
        "US10Y": "^TNX", "DXY": "DX-Y.NYB", "VIX": "^VIX", "HYG": "HYG",
        "USDCNH": "CNH=X", "GOLD": "GC=F", "SILVER": "SI=F", "COPPER": "HG=F",
        "AH_PREMIUM": "HSCAHPI.HK"
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
        except: raw_data[name] = {"value": "N/A", "trend": "⚪"}

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

    # Gas
    try:
        r = requests.get("https://beaconcha.in/api/v1/execution/gasnow", timeout=10)
        gas = int(r.json()['data']['rapid'] / 1e9)
        raw_data['GAS'] = f"{gas}"
    except: raw_data['GAS'] = "N/A"

    return raw_data

# === 2. 更新历史 CSV ===
def update_history(data):
    today = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d')
    new_row = {
        "日期": today,
        "US10Y": data['US10Y']['value'],
        "DXY": data['DXY']['value'],
        "VIX": data['VIX']['value'],
        "HYG": data['HYG']['value'],
        "黄金": data['GOLD']['value'],
        "铜": data['COPPER']['value'],
        "BTC.D": data['BTC.D'],
        "稳定币": data['STABLE_CAP'],
        "TGA": data['TGA'],
        "恐慌": data['FEAR'],
        "GAS": data['GAS'],
        "汇率": data['USDCNH']['value'],
        "AH溢价": data['AH_PREMIUM']['value']
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

# === 3. 生成网页 ===
def generate_html(current_data, history_df):
    beijing_time = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M')
    history_html = history_df.head(60).to_html(index=False, classes="history-table", border=0)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>秘密档案馆</title>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: sans-serif; margin:0; padding:20px; background:#f4f4f4; }}
            .container {{ max-width: 1200px; margin:0 auto; background:white; padding:20px; border-radius:10px; }}
            h1 {{ text-align:center; }}
            .history-table {{ width:100%; border-collapse:collapse; margin-top:20px; }}
            .history-table th {{ background:#333; color:white; padding:10px; }}
            .history-table td {{ padding:8px; text-align:center; border-bottom:1px solid #ddd; }}
            .history-table tr:nth-child(even) {{ background-color:#f9f9f9; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📂 每日金融档案 (18:00)</h1>
            <div style="text-align:center; color:#888;">最后归档: {beijing_time}</div>
            <div style="overflow-x:auto;">
                {history_html}
            </div>
        </div>
    </body>
    </html>
    """
    return html

if __name__ == "__main__":
    data = get_all_data()
    df = update_history(data)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(generate_html(data, df))
