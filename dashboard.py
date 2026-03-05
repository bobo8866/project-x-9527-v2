import yfinance as yf
import pandas as pd
import requests
import os
from datetime import datetime
import pytz

HISTORY_FILE = "history.csv"

# === 1. 获取纯净数据 ===
def get_all_data():
    tickers = {
        "US10Y": "^TNX", "DXY": "DX-Y.NYB", "VIX": "^VIX", "HYG": "HYG",
        "USDCNH": "CNH=X", "GOLD": "GC=F", "SILVER": "SI=F", "COPPER": "HG=F"
    }
    raw_data = {}
    
    # A. Yahoo (行情)
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

    # B. FRED (宏观)
    try:
        df = pd.read_csv("https://fred.stlouisfed.org/graph/fredgraph.csv?id=WTREGEN")
        raw_data['TGA'] = f"${df.iloc[-1, 1]:.0f}B"
    except: raw_data['TGA'] = "N/A"

    try:
        df = pd.read_csv("https://fred.stlouisfed.org/graph/fredgraph.csv?id=RRPONTSYD")
        raw_data['RRP'] = f"${df.iloc[-1, 1]:.0f}B"
    except: raw_data['RRP'] = "N/A"

    # C. Crypto (API)
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

# === 2. 更新历史 (严格排序) ===
def update_history(data):
    today = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d')
    
    def get_val(key):
        val = data[key]['value'] if isinstance(data[key], dict) else data[key]
        return val if val != "N/A" else ""

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
        # 确保列顺序一致，如果 CSV 里有旧的列(如Gas)会自动被忽略
        df = df.reindex(columns=new_row.keys())
        df = df[df["日期"] != today]
    else:
        df = pd.DataFrame(columns=new_row.keys())
    
    new_df = pd.DataFrame([new_row])
    df = pd.concat([df, new_df], ignore_index=True)
    df = df.sort_values(by="日期", ascending=False)
    df.to_csv(HISTORY_FILE, index=False, encoding="utf-8-sig")
    return df

# === 3. 生成网页 (纯净表格) ===
def generate_html(current_data, history_df):
    beijing_time = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M')
    history_html = history_df.head(60).to_html(index=False, classes="history-table", border=0)
    
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
            h1 {{ text-align:center; color:#333; margin-bottom:5px; }}
            .time {{ text-align:center; color:#888; font-size:0.9em; margin-bottom:20px; }}
            
            .card {{ background:white; padding:15px; border-radius:10px; margin-bottom:20px; box-shadow:0 2px 5px rgba(0,0,0,0.05); }}
            h2 {{ font-size:1.1em; color:#444; border-left:4px solid #0066cc; padding-left:10px; margin:0 0 15px 0; }}
            
            /* 通用表格样式 */
            table {{ width:100%; border-collapse:collapse; white-space:nowrap; font-size:0.9em; }}
            th {{ background:#333; color:white; padding:10px; text-align:center; }}
            td {{ padding:8px; text-align:center; border-bottom:1px solid #eee; }}
            tr:nth-child(even) {{ background-color:#f9f9f9; }}
            
            .trend {{ font-size:0.7em; margin-left:3px; }}
            .value {{ font-weight:bold; color:#333; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📂 每日金融档案</h1>
            <div class="time">最后归档: {beijing_time}</div>
            
            <!-- 实时看板 -->
            <div class="card">
                <h2>⚡ 实时快照 (Realtime)</h2>
                <div style="overflow-x:auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>US10Y</th><th>DXY</th><th>RRP</th><th>VIX</th><th>HYG</th>
                                <th>黄金</th><th>白银</th><th>铜</th>
                                <th>BTC.D</th><th>稳定币</th><th>TGA</th><th>恐慌</th><th>汇率</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>{current_data['US10Y']['value']}<span class="trend">{current_data['US10Y']['trend']}</span></td>
                                <td>{current_data['DXY']['value']}<span class="trend">{current_data['DXY']['trend']}</span></td>
                                <td>{current_data['RRP']}</td>
                                <td>{current_data['VIX']['value']}<span class="trend">{current_data['VIX']['trend']}</span></td>
                                <td>{current_data['HYG']['value']}<span class="trend">{current_data['HYG']['trend']}</span></td>
                                <td>{current_data['GOLD']['value']}<span class="trend">{current_data['GOLD']['trend']}</span></td>
                                <td>{current_data['SILVER']['value']}<span class="trend">{current_data['SILVER']['trend']}</span></td>
                                <td>{current_data['COPPER']['value']}<span class="trend">{current_data['COPPER']['trend']}</span></td>
                                <td>{current_data['BTC.D']}</td>
                                <td>{current_data['STABLE_CAP']}</td>
                                <td>{current_data['TGA']}</td>
                                <td>{current_data['FEAR']}</td>
                                <td>{current_data['USDCNH']['value']}<span class="trend">{current_data['USDCNH']['trend']}</span></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- 历史看板 -->
            <div class="card">
                <h2>📜 历史数据 (每日18:00自动写入)</h2>
                <div style="overflow-x:auto;">
                    {history_html}
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
