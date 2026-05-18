import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
import json
import concurrent.futures
import time
from datetime import datetime
from stock_analysis import Orchestrator, QuantDataAgent


def render_detail_report(ticker: str, report: dict) -> None:
    quant_report = report["quant_report"]
    sentiment_report = report["sentiment_report"]
    tech = quant_report["technical_indicators"]
    chip_flow = quant_report["chip_flow"]

    tech_color = "green" if quant_report["technical_conclusion"] == "多" else "red"
    sent_color = "green" if sentiment_report["overall_score"] >= 0 else "red"

    st.markdown("### 📌 詳細報告")
    st.markdown(f"**股票代碼**：{ticker}")
    st.markdown(
        f"<span style='color:{tech_color}; font-weight:bold;'>技術結論：{quant_report['technical_conclusion']}</span>  |  "
        f"<span style='color:{sent_color}; font-weight:bold;'>輿情判讀：{sentiment_report['sentiment_label']}</span>",
        unsafe_allow_html=True,
    )
    st.markdown(f"**最終建議**：{report['final_recommendation']}")
    st.markdown(f"**交叉驗證**：{report['cross_verification'][0]}")
    if sentiment_report.get("news_status"):
        st.warning(sentiment_report["news_status"])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("最新收盤價", tech["last_price"])
        st.metric("支撐", tech["support"])
        st.metric("RSI", tech["rsi"])
    with col2:
        st.metric("MA20", tech["ma20"])
        st.metric("壓力", tech["resistance"])
        st.metric("MACD Hist", tech["macd_hist"])
    with col3:
        st.metric("MA50", tech["ma50"])
        st.metric("MA200", tech["ma200"] if tech["ma200"] is not None else "N/A")
        st.metric("布林位置", tech["bollinger_position"])

    st.markdown("#### 📊 技術面指標說明")
    st.write(quant_report["technical_reason"])
    # 已移除：籌碼面三大法人與新聞輿情顯示，改以技術面/價格為主

    data = QuantDataAgent(ticker).get_historical_data()
    data = data.rename(columns={"Open": "開盤價", "High": "最高價", "Low": "最低價", "Close": "收盤價", "Volume": "成交量"})
    data["MA20"] = data["收盤價"].rolling(window=20).mean()
    data["MA50"] = data["收盤價"].rolling(window=50).mean()
    data["MA200"] = data["收盤價"].rolling(window=200).mean()
    data["中軌"] = data["收盤價"].rolling(window=20).mean()
    data["上軌"] = data["中軌"] + 2 * data["收盤價"].rolling(window=20).std()
    data["下軌"] = data["中軌"] - 2 * data["收盤價"].rolling(window=20).std()
    pos = data["收盤價"].diff() > 0
    data["RSI"] = 100 - (100 / (1 + data["收盤價"].diff().where(data["收盤價"].diff() > 0, 0.0).ewm(alpha=1 / 14, adjust=False).mean() / data["收盤價"].diff().where(data["收盤價"].diff() < 0, 0.0).abs().ewm(alpha=1 / 14, adjust=False).mean()))
    data["MACD"] = data["收盤價"].ewm(span=12, adjust=False).mean() - data["收盤價"].ewm(span=26, adjust=False).mean()
    data["Signal"] = data["MACD"].ewm(span=9, adjust=False).mean()
    data = data.dropna()

    fig = go.Figure(
        data=[
            go.Candlestick(
                x=data.index,
                open=data["開盤價"],
                high=data["最高價"],
                low=data["最低價"],
                close=data["收盤價"],
                increasing_line_color="green",
                decreasing_line_color="red",
                name="K 線",
            ),
            go.Scatter(x=data.index, y=data["MA20"], mode="lines", line=dict(color="lime"), name="MA20"),
            go.Scatter(x=data.index, y=data["MA50"], mode="lines", line=dict(color="cyan"), name="MA50"),
            go.Scatter(x=data.index, y=data["MA200"], mode="lines", line=dict(color="blue"), name="MA200"),
            go.Scatter(x=data.index, y=data["上軌"], mode="lines", line=dict(color="orange", dash="dash"), name="Bollinger 上軌"),
            go.Scatter(x=data.index, y=data["中軌"], mode="lines", line=dict(color="yellow", dash="dash"), name="Bollinger 中軌"),
            go.Scatter(x=data.index, y=data["下軌"], mode="lines", line=dict(color="orange", dash="dash"), name="Bollinger 下軌"),
        ]
    )
    fig.update_layout(
        xaxis_rangeslider_visible=False,
        height=560,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_dark" if tech["technical_conclusion"] == "多" else "plotly_white",
    )

    st.markdown("---")
    st.markdown("### 📈 價格與均線 (半年前資料)")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 📉 成交量")
    st.bar_chart(data[["成交量"]])

    st.markdown("### 📉 MACD")
    st.line_chart(data[["MACD", "Signal"]])

    st.markdown("### 📉 RSI")
    st.line_chart(data[["RSI"]])


def style_table(df: pd.DataFrame) -> str:
    # Create an HTML table with inline styling to avoid Styler compatibility issues
    styled = df.copy()
    for col in ["入場信號", "出場信號"]:
        if col in styled.columns:
            styled[col] = styled[col].astype(str).map(
                lambda v: f"<span style='color:green; font-weight:bold'>{v}</span>" if v == "YES" else (
                    f"<span style='color:red; font-weight:bold'>{v}</span>" if v == "NO" else v
                )
            )

    if "情緒判讀" in styled.columns:
        styled["情緒判讀"] = styled["情緒判讀"].astype(str).map(
            lambda v: f"<span style='color:green; font-weight:bold'>{v}</span>" if "樂觀" in v else (
                f"<span style='color:red; font-weight:bold'>{v}</span>" if "悲觀" in v else v
            )
        )

    # Render HTML table without escaping so spans are applied
    return styled.to_html(escape=False, index=False)


def get_index_summary():
    try:
        idx = QuantDataAgent(INDEX_TICKER)
        data = idx.get_historical_data(period="3d")
        if data is None or data.shape[0] < 2:
            return "N/A", ""
        last = data['Close'].iloc[-1]
        prev = data['Close'].iloc[-2]
        chg = last - prev
        pct = chg / prev * 100.0
        return f"{last:,.2f}", f"{chg:+,.2f} ({pct:+.2f}%)"
    except Exception:
        return "N/A", ""


def render_market_heatmap():
    heatmap_rows = []
    for sector, tickers in st.session_state.sector_map.items():
        top_group = TOP_CATEGORY_MAP.get(sector, "其他")
        for ticker in tickers:
            change, size_proxy, label = get_ticker_heatmap_metrics(ticker)
            if change is None:
                continue
            heatmap_rows.append({
                "top": top_group,
                "sector": sector,
                "label": f"{label}\n{change:+.2f}%",
                "ticker": ticker,
                "pct_change": change,
                "size": max(size_proxy, 1.0),
            })

    if not heatmap_rows:
        st.warning("目前無法取得熱力圖資料。")
        return

    df_tree = pd.DataFrame(heatmap_rows)
    fig = px.treemap(
        df_tree,
        path=["top", "sector", "label"],
        values="size",
        color="pct_change",
        color_continuous_scale="RdYlGn",
        range_color=[-10, 10],
        title="",
        hover_data={"ticker": True, "pct_change": ":.2f"},
    )
    fig.update_traces(
        textinfo="label+text",
        textfont_size=12,
        hovertemplate="%{label}<br>%{value:.0f} 代理市值<br>%{color:.2f}%",
        colorbar=dict(
            title="漲跌幅",
            tickvals=[-10, -6, -3, 0, 3, 6, 10],
            ticks="outside",
            lenmode="fraction",
            len=0.35,
        ),
    )


# --- Sector mapping / heatmap UI ---
SECTOR_FILE = os.path.join(os.path.dirname(__file__), ".cache", "sectors.json")
DEFAULT_SECTORS = [
    "半導體／IC 設計／晶圓代工",
    "AI／伺服器／PCB／電子零組件",
    "記憶體／儲存",
    "網通／通訊",
    "金融保險",
    "航運／航空／物流",
    "傳產／塑化／鋼鐵／原物料",
    "重電／機械／自動化",
    "生技醫療",
    "營建／資產／不動產",
    "電信／媒體／數位服務",
    "消費／零售／食品",
    "汽車／電動車／車用零件",
    "綠能／能源",
    "觀光／休閒",
    "高股息／防禦型代表",
    "高成長 AI 概念",
]
DEFAULT_SECTOR_MAP = {
    "半導體／IC 設計／晶圓代工": [
        "2330","2303","2454","3443","3661","3035","3034","2379","4919","6526",
        "6415","5269","6531","6770","2408","2344","2337","3006","8150","2441",
        "6239","6257","8046","3037","3189","2368","3044","6213","3532","1560",
        "3583","6515","3653","6669","7769","6789","6919","3030","6830","6451","5234",
        "6205","6756","4952","5471",
    ],
    "AI／伺服器／PCB／電子零組件": [
        "2382","3231","6669","2356","2317","4938","2385","2357","2376","2377",
        "8210","3017","3653","2059","3533","2383","3037","2368","8046","3189",
        "6213","3044","6278","6191","2449","2455","2486","4919","3023","6409",
        "2451","6285","3706","3036","3702","2347","2345","2301","2354","3532",
        "2467","6196","6176","3450","6451","6414",
    ],
    "記憶體／儲存": ["2408","2344","2337","6770","3006","2451","6257"],
    "網通／通訊": ["2412","4904","3045","6285","2345","3062","2332","6277","6416","2397","5203","6168","6756","2450","2417"],
    "金融保險": [
        "2881","2882","2891","2885","2887","2886","2884","2890","2880","2892",
        "5880","5876","2834","2812","2838","6005","2855","2889","2801","2845",
        "2852","2816",
    ],
    "航運／航空／物流": ["2603","2615","2618","2609","2633","2646","2645","2637","2606","5608","2614"],
    "傳產／塑化／鋼鐵／原物料": [
        "1301","1303","1326","6505","2002","2027","2006","1605","1717","1722",
        "1773","1802","1101","1102","1210","1216","1229","1305","1308","1309",
        "1310","1319","1402","1476","1477","1714","1709","2105","2102","2028",
        "2030","2012",
    ],
    "重電／機械／自動化": [
        "1519","1504","1503","2049","1590","8996","4583","1513","3167","4566",
        "4540","8374","1583","1528","1524","1525","1527",
    ],
    "生技醫療": ["6446","6472","1795","4142","4164","4119","1734","1760","4137","4746","6949"],
    "營建／資產／不動產": [
        "2542","2540","5522","5531","5515","5525","2539","2597","2514","2505",
        "2536","2442","3266","2701",
    ],
    "電信／媒體／數位服務": ["2412","3045","4904","8454","3130","4994","5203"],
    "消費／零售／食品": ["2912","1216","1201","1217","1225","1256","8454","6281","9943","5283","9910","9904","2236"],
    "汽車／電動車／車用零件": ["2207","2206","2258","1319","2497","6285","1524","2114","2228"],
    "綠能／能源": ["1519","1503","3712","6994","9946","1722","6805","6442"],
    "觀光／休閒": ["2646","2762","9943","2706"],
    "高股息／防禦型代表": ["2412","2881","2882","2891","2885","5880","1216","1101","2633","3045","4904","9917"],
    "高成長 AI 概念": ["2330","2454","6669","3661","3443","3017","3653","2059","2383","3231","8210","6805","6515","6919","5269","3035"],
}

if "sector_map" not in st.session_state:
    try:
        os.makedirs(os.path.dirname(SECTOR_FILE), exist_ok=True)
        if os.path.exists(SECTOR_FILE):
            with open(SECTOR_FILE, "r", encoding="utf-8") as f:
                saved_map = json.load(f)
            merged = {**DEFAULT_SECTOR_MAP}
            merged.update(saved_map)
            for s in DEFAULT_SECTORS:
                merged.setdefault(s, DEFAULT_SECTOR_MAP.get(s, []))
            st.session_state.sector_map = merged
        else:
            st.session_state.sector_map = {s: list(DEFAULT_SECTOR_MAP.get(s, [])) for s in DEFAULT_SECTORS}
    except Exception:
        st.session_state.sector_map = {s: list(DEFAULT_SECTOR_MAP.get(s, [])) for s in DEFAULT_SECTORS}


def save_sector_map():
    try:
        with open(SECTOR_FILE, "w", encoding="utf-8") as f:
            json.dump(st.session_state.sector_map, f, ensure_ascii=False, indent=2)
        st.success("板塊 mapping 已儲存到 .cache/sectors.json")
    except Exception as e:
        st.error(f"儲存失敗：{e}")

st.set_page_config(page_title="股票雙 Agent 可視化分析", layout="wide")
st.title("📈 股價漲跌即時熱力圖")
index_value, index_delta = get_index_summary()
left, right = st.columns([3, 1])
with left:
    st.markdown("#### 篩選條件 (面積: 總市值, 漲跌: 前一個營業日)")
    market_choice = st.radio("市場選擇", ["市", "櫃"], index=0, horizontal=True)
with right:
    st.markdown("#### 加權 (TAIEX)")
    st.metric("加權指數", index_value, index_delta)
    st.caption(f"更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

st.markdown("---")
main_left, main_right = st.columns([2.8, 7.2])
with main_left:
    tabs = st.tabs(["Heat Map & Pool Filter", "追蹤名單分析"])
    with tabs[0]:
        st.markdown("### Heat Map & Pool Filter")
        render_market_heatmap()
        st.markdown("---")
        st.markdown("#### 目前可用板塊")
        st.write([s for s in DEFAULT_SECTORS])
    with tabs[1]:
        st.markdown("### 追蹤名單分析")
        watchlist = [t.strip() for t in st.session_state.get("watchlist", "").splitlines() if t.strip()]
        if not watchlist:
            st.info("請先在觀察清單新增至少一個股票代碼。")
        else:
            st.write(f"目前觀察清單共有 {len(watchlist)} 檔股票。")
            held_tickers = st.multiselect("標記已持有股票", options=watchlist, default=st.session_state.get("held_tickers", []))
            st.session_state.held_tickers = held_tickers
            render_watchlist_signal_panel(watchlist, held_tickers)

    st.markdown("---")
    st.markdown("### 信號燈總覽")
    watchlist = [t.strip() for t in st.session_state.get("watchlist", "").splitlines() if t.strip()]
    held_tickers = st.session_state.get("held_tickers", [])
    if watchlist:
        summary = []
        for ticker in watchlist:
            sig = compute_watchlist_signal(ticker, held=(ticker in held_tickers))
            summary.append({"股票": ticker, "訊號": sig["訊號"]})
        st.table(pd.DataFrame(summary))
    else:
        st.info("目前沒有觀察清單股票，因此無法顯示訊號燈。")

TICKER_NAME_MAP = {
    "2330": "台積電",
    "2454": "聯發科",
    "2303": "聯電",
    "2317": "鴻海",
    "2308": "台積電代號?",
    "2301": "光寶科",
    "2881": "富邦金",
    "2882": "國泰金",
    "2382": "廣達",
    "2302": "聯電",
    "2305": "全友電",
    "4938": "和碩",
    "2408": "南亞科",
}

TOP_CATEGORY_MAP = {
    "半導體／IC 設計／晶圓代工": "半導體",
    "記憶體／儲存": "半導體",
    "高成長 AI 概念": "半導體",
    "AI／伺服器／PCB／電子零組件": "電子零組件",
    "網通／通訊": "電子零組件",
    "電信／媒體／數位服務": "電子零組件",
    "汽車／電動車／車用零件": "電子零組件",
    "金融保險": "金融",
    "高股息／防禦型代表": "金融",
    "營建／資產／不動產": "其他",
    "生技醫療": "其他",
    "航運／航空／物流": "其他",
    "傳產／塑化／鋼鐵／原物料": "其他",
    "重電／機械／自動化": "其他",
    "消費／零售／食品": "其他",
    "綠能／能源": "其他",
    "觀光／休閒": "其他",
}

INDEX_TICKER = "^TWII"


def get_ticker_pct_change(ticker: str):
    try:
        data = QuantDataAgent(ticker).get_historical_data(period="5d")
        if data is None or data.shape[0] < 2:
            return None
        last = data['Close'].iloc[-1]
        prev = data['Close'].iloc[-2]
        return (last - prev) / prev * 100.0
    except Exception:
        return None


def get_ticker_heatmap_metrics(ticker: str):
    try:
        data = QuantDataAgent(ticker).get_historical_data(period="3d")
        if data is None or data.shape[0] < 2:
            return None, None, None
        last = data['Close'].iloc[-1]
        prev = data['Close'].iloc[-2]
        change = (last - prev) / prev * 100.0
        size_proxy = float(last * data['Volume'].iloc[-1]) if 'Volume' in data.columns else float(last)
        label = TICKER_NAME_MAP.get(ticker, ticker)
        return change, size_proxy, label
    except Exception:
        return None, None, ticker


def determine_trade_signal(held: bool, entry_condition: bool, exit_condition: bool) -> str:
    if held and exit_condition:
        return "🔴 出場訊號"
    if not held and entry_condition:
        return "🟢 入場訊號"
    return "⚪ 監控中"


def compute_watchlist_signal(ticker: str, held: bool = False):
    try:
        data = QuantDataAgent(ticker).get_historical_data(period="60d")
        if data is None or data.shape[0] < 20:
            return {
                "股票": ticker,
                "是否持有": "是" if held else "否",
                "入場條件": "N/A",
                "出場條件": "N/A",
                "訊號": "⚪ 監控中",
                "最後價": "N/A",
                "MA20": "N/A",
                "MA50": "N/A",
            }

        close = data['Close']
        last = close.iloc[-1]
        prev = close.iloc[-2]
        ma20 = close.rolling(window=20).mean().iloc[-1]
        ma50 = close.rolling(window=50).mean().iloc[-1] if data.shape[0] >= 50 else None
        entry_condition = ma50 is not None and ma20 > ma50 and last > ma20 and last > prev
        exit_condition = ma50 is not None and (ma20 < ma50 or last < ma20 or last < close.rolling(window=20).min().iloc[-1] * 0.98)

        status = determine_trade_signal(held, entry_condition, exit_condition)
        return {
            "股票": ticker,
            "是否持有": "是" if held else "否",
            "入場條件": "符合" if entry_condition else "不符合",
            "出場條件": "符合" if exit_condition else "不符合",
            "訊號": status,
            "最後價": f"{last:.2f}",
            "MA20": f"{ma20:.2f}",
            "MA50": f"{ma50:.2f}" if ma50 is not None else "N/A",
        }
    except Exception:
        return {
            "股票": ticker,
            "是否持有": "是" if held else "否",
            "入場條件": "N/A",
            "出場條件": "N/A",
            "訊號": "⚪ 監控中",
            "最後價": "N/A",
            "MA20": "N/A",
            "MA50": "N/A",
        }


def render_watchlist_signal_panel(watchlist, held_tickers):
    if not watchlist:
        st.info("觀察清單目前為空，請先新增股票代碼。")
        return

    signals = []
    for ticker in watchlist:
        signals.append(compute_watchlist_signal(ticker, held=(ticker in held_tickers)))

    st.markdown("### 追蹤名單訊號燈")
    st.table(pd.DataFrame(signals))


# compute a simple sector-level pct change (average of tickers)
sector_avgs = {}
for s, tickers in st.session_state.sector_map.items():
    vals = []
    for t in tickers:
        pct = get_ticker_pct_change(t)
        if pct is not None:
            vals.append(pct)
    sector_avgs[s] = sum(vals) / len(vals) if vals else 0.0

# display top 6 hottest sectors and all sectors sorted by daily change
sorted_sectors = sorted(sector_avgs.items(), key=lambda item: item[1], reverse=True)
if sorted_sectors:
    top6 = sorted_sectors[:6]
    st.markdown("#### 熱門板塊前 6 名")
    top6_df = pd.DataFrame(top6, columns=["板塊", "當日平均漲幅(%)"]).round(2)
    st.table(top6_df)

    st.markdown("#### 板塊漲幅排序")
    all_df = pd.DataFrame(sorted_sectors, columns=["板塊", "當日平均漲幅(%)"]).round(2)
    st.dataframe(all_df, height=260)

# render a simple heatmap (arrange sectors in rows)
cols = 6
rows = (len(DEFAULT_SECTORS) + cols - 1) // cols
z = [[None for _ in range(cols)] for __ in range(rows)]
text = [["" for _ in range(cols)] for __ in range(rows)]
for idx, s in enumerate(DEFAULT_SECTORS):
    r = idx // cols
    c = idx % cols
    z[r][c] = sector_avgs.get(s, 0.0)
    text[r][c] = f"{s}\n{sector_avgs.get(s,0.0):+.2f}%"

fig_sec = go.Figure(data=go.Heatmap(z=z, text=text, hoverinfo='text', colorscale='RdYlGn', colorbar=dict(title="%")))
fig_sec.update_layout(height=200, margin=dict(l=10, r=10, t=20, b=20))
st.plotly_chart(fig_sec, use_container_width=True)

# clickable sector buttons
st.write("選擇板塊：")
cols_sect = st.columns(6)
for i, s in enumerate(DEFAULT_SECTORS):
    with cols_sect[i % 6]:
        if st.button(s):
            st.session_state.selected_sector = s

with st.expander("編輯板塊 -> 對應股票代碼（每行一個）"):
    sel = st.selectbox("選擇板塊以編輯", DEFAULT_SECTORS)
    current_text = "\n".join(st.session_state.sector_map.get(sel, []))
    updated = st.text_area("板塊成分（每行一個代碼）", value=current_text, height=180)
    if st.button("儲存板塊成分"):
        st.session_state.sector_map[sel] = [t.strip() for t in updated.splitlines() if t.strip()]
        save_sector_map()

selected = st.session_state.get("selected_sector")
if selected:
    st.markdown(f"### 已選：{selected}")
    tickers = st.session_state.sector_map.get(selected, [])
    if not tickers:
        st.info("此板塊目前沒有設定任何股票，請在上方編輯板塊成分。")
    else:
        st.write(f"共有 {len(tickers)} 檔；正在偵測近期動能與技術面符合的個股...")
        # analyze tickers in parallel but limit to first 30 for speed
        candidates = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(tickers))) as exe:
            futures = {exe.submit(lambda tt: (tt, Orchestrator(tt).run()), t): t for t in tickers[:30]}
            for fut in concurrent.futures.as_completed(futures):
                t = futures[fut]
                try:
                    _t, rep = fut.result()
                    q = rep["quant_report"]
                    tech = q["technical_indicators"]
                    # momentum criteria: 短期均線多頭 (MA20>MA50) and 技術結論 多
                    ma20 = tech.get("ma20")
                    ma50 = tech.get("ma50")
                    pct = get_ticker_pct_change(t)
                    if q["technical_conclusion"] == "多" and ma20 and ma50 and ma20 > ma50 and (pct is None or pct > 0):
                        candidates.append((t, pct if pct is not None else 0.0))
                except Exception:
                    continue

        if not candidates:
            st.warning("找不到符合條件的個股（短期動能 + 技術面）。")
        else:
            cand_df = pd.DataFrame(candidates, columns=["股票", "當日漲幅(%)"]).sort_values(by="當日漲幅(%)", ascending=False)
            st.table(cand_df)

# --- end sector UI ---

if "watchlist" not in st.session_state:
    st.session_state.watchlist = "2330.TW\nAAPL"

with st.sidebar:
    st.header("觀察清單管理")
    watchlist_text = st.text_area("觀察清單（每行一個股票代碼）", value=st.session_state.watchlist, height=180)
    if st.button("儲存觀察清單"):
        st.session_state.watchlist = watchlist_text.strip()
        st.success("觀察清單已更新。")

    if st.button("清除觀察清單"):
        st.session_state.watchlist = ""
        watchlist_text = ""
        st.success("已清除觀察清單。")

    st.markdown("---")
    st.header("快速新增股票")
    new_ticker = st.text_input("新股票代碼", value="")
    if st.button("加入觀察清單"):
        current = [t.strip() for t in st.session_state.watchlist.splitlines() if t.strip()]
        if new_ticker.strip():
            if new_ticker.strip() not in current:
                current.append(new_ticker.strip())
                st.session_state.watchlist = "\n".join(current)
                watchlist_text = st.session_state.watchlist
                st.success(f"已加入 {new_ticker.strip()}。")
            else:
                st.warning(f"{new_ticker.strip()} 已在觀察清單中。")

    st.markdown("---")
    st.header("篩選設定")
    filter_positive_sentiment = st.checkbox("只顯示輿情得分>=0 的股票", value=True)
    filter_long_signal = st.checkbox("只顯示技術面看多的股票", value=True)
    filter_near_support = st.checkbox("只顯示價格接近支撐的股票", value=False)
    support_margin = st.slider("支撐區距 (%)", min_value=1, max_value=10, value=5)
    st.markdown("---")
    st.header("出場條件設定")
    enable_exit_rules = st.checkbox("啟用出場判斷", value=True)
    sentiment_exit_threshold = st.slider(
        "出場：輿情逆轉閾值（小於該值視為顯著負向）",
        min_value=-1.0,
        max_value=0.0,
        value=-0.2,
        step=0.05,
    )
    resistance_break_pct = st.slider(
        "出場：突破壓力所需 (%)（達到或超過視為突破）",
        min_value=0,
        max_value=10,
        value=0,
        step=1,
    )

watchlist = [t.strip() for t in st.session_state.watchlist.splitlines() if t.strip()]
if not watchlist:
    st.warning("請在左側建立觀察清單，或新增至少一個股票代碼。")

col1, col2 = st.columns([2, 1])
with col1:
    st.subheader("觀察清單")
    st.write("目前觀察清單：")
    st.write(watchlist)

with col2:
    st.subheader("操作")
    run_single = st.text_input("單一分析股票代碼", value="")
    if st.button("分析單一股票"):
        run_single_ticker = run_single.strip()
    else:
        run_single_ticker = ""

if st.button("分析觀察清單") or run_single_ticker:
    targets = [run_single_ticker] if run_single_ticker else watchlist
    results = []
    summary_rows = []

    if run_single_ticker:
        # single run synchronously for immediate detail
        with st.spinner(f"分析 {run_single_ticker} ..."):
            orchestrator = Orchestrator(run_single_ticker)
            report = orchestrator.run()
            results.append((run_single_ticker, report))
            quant = report["quant_report"]
            sentiment = report["sentiment_report"]
            tech = quant["technical_indicators"]
            entry_signal = True
            reasons = []
            if filter_long_signal and quant["technical_conclusion"] != "多":
                entry_signal = False
                reasons.append("技術面非多頭")
            if filter_positive_sentiment and sentiment["overall_score"] < 0:
                entry_signal = False
                reasons.append("輿情偏空")
            if filter_near_support:
                threshold = tech["support"] * (1 + support_margin / 100)
                if tech["last_price"] > threshold:
                    entry_signal = False
                    reasons.append("價格尚未接近支撐")
            negative_sentiment_reversal = sentiment["overall_score"] < sentiment_exit_threshold if 'sentiment_exit_threshold' in locals() else sentiment["overall_score"] < -0.2
            resistance_break = (
                tech["last_price"] >= tech["resistance"] * (1 + resistance_break_pct / 100)
                if 'resistance_break_pct' in locals()
                else tech["last_price"] >= tech["resistance"]
            )
            exit_signal = False
            if enable_exit_rules:
                exit_signal = (
                    quant["technical_conclusion"] == "空"
                    or negative_sentiment_reversal
                    or resistance_break
                )

            summary_rows.append(
                {
                    "股票": run_single_ticker,
                    "技術結論": quant["technical_conclusion"],
                    "RSI": tech["rsi"],
                    "收盤價": tech["last_price"],
                    "支撐": tech["support"],
                    "壓力": tech["resistance"],
                    "新聞得分": sentiment["overall_score"],
                    "情緒判讀": sentiment["sentiment_label"],
                    "入場信號": "YES" if entry_signal else "NO",
                    "出場信號": "YES" if exit_signal else "NO",
                    "不符合原因": "; ".join(reasons) if reasons else "符合篩選條件",
                }
            )

        df = pd.DataFrame(summary_rows)
        st.subheader("單一股票分析結果")
        st.markdown(style_table(df), unsafe_allow_html=True)
        st.markdown("---")
        st.subheader(f"{run_single_ticker} 詳細分析")
        render_detail_report(run_single_ticker, report)
    else:
        st.subheader("觀察清單總覽")
        progress = st.progress(0)
        status_text = st.empty()
        total = len(targets)
        completed = 0
        futures_map = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, total)) as exe:
            for t in targets:
                futures_map[exe.submit(lambda tt: (tt, Orchestrator(tt).run()), t)] = t

            for fut in concurrent.futures.as_completed(futures_map):
                ticker = futures_map[fut]
                try:
                    tck, report = fut.result()
                    quant = report["quant_report"]
                    sentiment = report["sentiment_report"]
                    tech = quant["technical_indicators"]

                    entry_signal = True
                    reasons = []
                    if filter_long_signal and quant["technical_conclusion"] != "多":
                        entry_signal = False
                        reasons.append("技術面非多頭")
                    if filter_positive_sentiment and sentiment["overall_score"] < 0:
                        entry_signal = False
                        reasons.append("輿情偏空")
                    if filter_near_support:
                        threshold = tech["support"] * (1 + support_margin / 100)
                        if tech["last_price"] > threshold:
                            entry_signal = False
                            reasons.append("價格尚未接近支撐")

                    negative_sentiment_reversal = sentiment["overall_score"] < sentiment_exit_threshold if 'sentiment_exit_threshold' in locals() else sentiment["overall_score"] < -0.2
                    resistance_break = (
                        tech["last_price"] >= tech["resistance"] * (1 + resistance_break_pct / 100)
                        if 'resistance_break_pct' in locals()
                        else tech["last_price"] >= tech["resistance"]
                    )
                    exit_signal = False
                    if enable_exit_rules:
                        exit_signal = (
                            quant["technical_conclusion"] == "空"
                            or negative_sentiment_reversal
                            or resistance_break
                        )

                    summary_rows.append(
                        {
                            "股票": ticker,
                            "技術結論": quant["technical_conclusion"],
                            "RSI": tech["rsi"],
                            "收盤價": tech["last_price"],
                            "支撐": tech["support"],
                            "壓力": tech["resistance"],
                            "新聞得分": sentiment["overall_score"],
                            "情緒判讀": sentiment["sentiment_label"],
                            "入場信號": "YES" if entry_signal else "NO",
                            "出場信號": "YES" if exit_signal else "NO",
                            "不符合原因": "; ".join(reasons) if reasons else "符合篩選條件",
                        }
                    )
                    results.append((ticker, report))
                except Exception as exc:
                    summary_rows.append(
                        {
                            "股票": ticker,
                            "技術結論": "分析失敗",
                            "RSI": None,
                            "收盤價": None,
                            "支撐": None,
                            "壓力": None,
                            "新聞得分": None,
                            "情緒判讀": None,
                            "入場信號": "NO",
                            "出場信號": "NO",
                            "不符合原因": str(exc),
                        }
                    )

                completed += 1
                progress.progress(int(completed / total * 100))
                status_text.text(f"已完成 {completed}/{total}：{ticker}")

        df = pd.DataFrame(summary_rows)
        st.markdown(style_table(df), unsafe_allow_html=True)
        st.markdown("---")
        st.subheader("符合入場條件的股票")
        filtered = df[df["入場信號"] == "YES"]
        if filtered.empty:
            st.warning("目前沒有符合入場條件的股票。")
        else:
            st.dataframe(filtered)
            for ticker, report in results:
                quant_report = report["quant_report"]
                sentiment_report = report["sentiment_report"]
                if quant_report["technical_conclusion"] == "多" and sentiment_report["overall_score"] >= 0:
                    with st.expander(f"{ticker} 詳細報告"):
                        render_detail_report(ticker, report)
