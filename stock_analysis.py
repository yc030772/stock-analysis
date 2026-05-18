import datetime
import json
import os
import urllib3
import numpy as np
import pandas as pd
import requests
import yfinance as yf
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Simple in-memory caches to avoid repeated network calls during a single app session
HIST_CACHE: dict[str, tuple[float, pd.DataFrame]] = {}
TWSE_CACHE: dict[str, tuple[float, list[dict[str, object]]]] = {}
NEWS_CACHE: dict[str, tuple[float, list[dict[str, object]]]] = {}
CACHE_TTL = 300  # short-term seconds
LONG_CACHE_TTL = 86400  # long-term cache for disk (seconds)
CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache")
os.makedirs(CACHE_DIR, exist_ok=True)
TWSE_CACHE_FILE = os.path.join(CACHE_DIR, "twse_cache.json")
NEWS_CACHE_FILE = os.path.join(CACHE_DIR, "news_cache.json")


def _load_disk_cache(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_disk_cache(path: str, data: dict) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


def clamp(value: float, minimum: float = -1.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def calculate_rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff().dropna()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1]) if not rsi.empty else 0.0


def calculate_macd(series: pd.Series) -> dict[str, float]:
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal = macd_line.ewm(span=9, adjust=False).mean()
    hist = macd_line - signal
    return {
        "macd": float(macd_line.iloc[-1]),
        "signal": float(signal.iloc[-1]),
        "hist": float(hist.iloc[-1]),
    }


def sentiment_score_from_text(text: str) -> float:
    positive_words = ["利多", "成長", "上調", "營收", "毛利", "優於", "回升", "突破", "恢復"]
    negative_words = ["利空", "下修", "虧損", "衰退", "壓力", "下滑", "警示", "風險"]
    score = 0
    lower = text.lower()

    for word in positive_words:
        if word in lower:
            score += 0.2
    for word in negative_words:
        if word in lower:
            score -= 0.2

    return round(clamp(score), 2)


def convert_to_serializable(obj: object) -> object:
    if isinstance(obj, (pd.Timestamp, pd.Timedelta)):
        return str(obj)
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="ignore")
    return str(obj)


def normalize_holder_row(raw: dict) -> dict:
    return {key: convert_to_serializable(value) for key, value in raw.items()}


class QuantDataAgent:
    ticker: str

    def __init__(self, ticker: str) -> None:
        self.ticker = ticker

    def get_historical_data(self) -> pd.DataFrame:
        now = time.time()
        cached = HIST_CACHE.get(self.ticker)
        if cached and now - cached[0] < CACHE_TTL:
            return cached[1]

        ticker = yf.Ticker(self.ticker)
        data = ticker.history(period="240d", interval="1d")
        if data.empty:
            raise ValueError(f"無法取得 {self.ticker} 的歷史價格資料。")
        HIST_CACHE[self.ticker] = (now, data)
        return data

    def get_technical_indicators(self) -> dict[str, object]:
        data = self.get_historical_data()
        close = data["Close"]
        ma20 = close.rolling(window=20).mean().iloc[-1]
        ma50 = close.rolling(window=50).mean().iloc[-1]
        ma200 = close.rolling(window=200).mean().iloc[-1] if len(close) >= 200 else float("nan")
        rsi = calculate_rsi(close)
        macd = calculate_macd(close)
        middle_band = close.rolling(window=20).mean().iloc[-1]
        std = close.rolling(window=20).std().iloc[-1]
        upper_band = middle_band + 2 * std
        lower_band = middle_band - 2 * std
        last_price = float(close.iloc[-1])

        if last_price >= upper_band:
            bollinger_position = "上軌附近或突破"
        elif last_price <= lower_band:
            bollinger_position = "下軌附近或跌破"
        else:
            bollinger_position = "布林通道中軌附近"

        support = float(close[-20:].min())
        resistance = float(close[-20:].max())
        volume_avg_20 = float(data["Volume"].rolling(window=20).mean().iloc[-1])
        latest_volume = int(data["Volume"].iloc[-1])

        technical_conclusion = "盤整"
        technical_reason = "近期均線排列不明顯，RSI 在中性區間。"
        if last_price > ma20 and last_price > ma50 and rsi < 70:
            technical_conclusion = "多"
            technical_reason = "價格位於主要均線之上，且 RSI 尚未進入超買區。"
        elif last_price < ma20 and last_price < ma50 and rsi > 30:
            technical_conclusion = "空"
            technical_reason = "價格位於主要均線之下，且趨勢仍未轉強。"

        return {
            "last_price": last_price,
            "ma20": round(ma20, 2),
            "ma50": round(ma50, 2),
            "ma200": round(ma200, 2) if not pd.isna(ma200) else None,
            "rsi": round(rsi, 2),
            "macd_hist": round(macd["hist"], 4),
            "bollinger_position": bollinger_position,
            "support": round(support, 2),
            "resistance": round(resistance, 2),
            "volume_avg_20": round(volume_avg_20, 0),
            "latest_volume": latest_volume,
            "technical_conclusion": technical_conclusion,
            "technical_reason": technical_reason,
        }

    def get_twse_three_major_flow(self, max_days: int = 3, required_rows: int = 1) -> dict[str, object]:
        code = self.ticker.split(".")[0]
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate",
        }

        # Check cache first
        now = time.time()
        # in-memory short cache
        cached = TWSE_CACHE.get(self.ticker)
        if cached and now - cached[0] < CACHE_TTL:
            return {"entries": cached[1], "note": f"從快取取得 {len(cached[1])} 筆 TWSE 資料。"}
        # disk long cache
        disk = _load_disk_cache(TWSE_CACHE_FILE)
        if self.ticker in disk:
            rec = disk[self.ticker]
            if now - rec.get("ts", 0) < LONG_CACHE_TTL:
                TWSE_CACHE[self.ticker] = (now, rec.get("entries", []))
                return {"entries": rec.get("entries", []), "note": f"從磁碟快取取得 {len(rec.get('entries', []))} 筆 TWSE 資料。"}

        entries: list[dict[str, object]] = []
        for offset in range(max_days):
            target_date = datetime.date.today() - datetime.timedelta(days=offset)
            url = (
                f"https://www.twse.com.tw/fund/T86?response=json&date={target_date.strftime('%Y%m%d')}&selectType=ALL"
            )
            try:
                resp = requests.get(url, timeout=10, verify=False, headers=headers)
                if resp.status_code != 200:
                    continue
                data = resp.json()
            except Exception:
                continue

            if data.get("stat") != "OK" or not data.get("data"):
                continue

            fields = data.get("fields", [])
            for row in data["data"]:
                if str(row[0]).strip() == code:
                    row_data = dict(zip(fields, row))
                    row_data = {key: convert_to_serializable(value) for key, value in row_data.items()}
                    row_data["date"] = data.get("date", target_date.strftime('%Y%m%d'))
                    entries.append(row_data)
                    break

            if len(entries) >= required_rows:
                break

        if not entries:
            return {
                "entries": [],
                "note": "TWSE 三大法人買賣超資料未取得；可能為休市、資料尚未公告，或該代碼不在當日公開名單中。",
            }

        # Deduplicate by date (keep latest occurrence per date)
        seen = set()
        unique_entries = []
        for e in entries:
            d = e.get("date")
            if d in seen:
                continue
            seen.add(d)
            unique_entries.append(e)

        TWSE_CACHE[self.ticker] = (now, unique_entries)
        # save to disk
        disk = _load_disk_cache(TWSE_CACHE_FILE)
        disk[self.ticker] = {"ts": now, "entries": unique_entries}
        _save_disk_cache(TWSE_CACHE_FILE, disk)
        return {
            "entries": unique_entries,
            "note": f"已取得 {len(unique_entries)} 筆 TWSE 三大法人買賣超資料，最近交易日期：{unique_entries[0]['date']}。",
        }

    def get_chip_flow(self) -> dict[str, object]:
        ticker = yf.Ticker(self.ticker)
        holders = ticker.institutional_holders
        twse_flow = self.get_twse_three_major_flow()

        institution_count = len(holders) if holders is not None else 0
        top_institution = None
        if holders is not None and not holders.empty:
            top_institution = normalize_holder_row(holders.iloc[0].to_dict())

        return {
            "institution_holder_count": institution_count,
            "top_institution": top_institution,
            "three_major_flow": twse_flow["entries"],
            "note": twse_flow["note"],
        }

    def analyze(self) -> dict[str, object]:
        tech = self.get_technical_indicators()
        chip = self.get_chip_flow()

        chip_conclusion = "機構關注"
        chip_reason = "YFinance 顯示機構持股資料，若持股比重穩定或持續增加，可視為機構關注。"

        return {
            "report_type": "quant",
            "technical_indicators": tech,
            "chip_flow": chip,
            "technical_conclusion": tech["technical_conclusion"],
            "technical_reason": tech["technical_reason"],
            "chip_conclusion": chip_conclusion,
            "chip_reason": chip_reason,
            "support": tech["support"],
            "resistance": tech["resistance"],
        }


class SentimentAgent:
    ticker: str

    def __init__(self, ticker: str) -> None:
        self.ticker = ticker

    def get_financial_news(self) -> tuple[list[dict[str, object]], str]:
        # cache news per ticker to avoid repeated RSS/API calls
        now = time.time()
        cached = NEWS_CACHE.get(self.ticker)
        if cached and now - cached[0] < CACHE_TTL:
            return cached[1], "(從快取取得新聞)"
        # disk cache
        diskn = _load_disk_cache(NEWS_CACHE_FILE)
        if self.ticker in diskn and now - diskn[self.ticker].get("ts", 0) < LONG_CACHE_TTL:
            NEWS_CACHE[self.ticker] = (now, diskn[self.ticker].get("items", []))
            return diskn[self.ticker].get("items", []), "(從磁碟快取取得新聞)"
        # Try Yahoo Finance news first
        ticker = yf.Ticker(self.ticker)
        news = getattr(ticker, "news", None)
        result: list[dict[str, object]] = []
        if news:
            for item in news[:5]:
                title = item.get("title", "")
                publisher = item.get("publisher", "")
                summary = item.get("summary", title)
                text = f"{title} {summary}"
                score = sentiment_score_from_text(text)
                result.append(
                    {
                        "title": title,
                        "summary": summary,
                        "publisher": publisher,
                        "sentiment": score,
                    }
                )
            return result, ""

        # Yahoo failed — try Google News RSS search as fallback (no API key required)
        try:
            company_name = ""
            try:
                info = ticker.info
                company_name = info.get("shortName") or info.get("longName") or ""
            except Exception:
                company_name = ""

            query = f"{self.ticker} {company_name}" if company_name else self.ticker
            rss_url = (
                "https://news.google.com/rss/search?q=" + requests.utils.quote(query) +
                "&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
            )
            resp = requests.get(rss_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200 and resp.text:
                # Minimal XML parsing to extract items
                import xml.etree.ElementTree as ET

                root = ET.fromstring(resp.content)
                items = root.findall('.//item')[:5]
                for it in items:
                    title = it.findtext('title') or ''
                    desc = it.findtext('description') or ''
                    text = f"{title} {desc}"
                    score = sentiment_score_from_text(text)
                    result.append({"title": title, "summary": desc, "publisher": "GoogleNewsRSS", "sentiment": score})
                if result:
                    NEWS_CACHE[self.ticker] = (now, result)
                    diskn = _load_disk_cache(NEWS_CACHE_FILE)
                    diskn[self.ticker] = {"ts": now, "items": result}
                    _save_disk_cache(NEWS_CACHE_FILE, diskn)
                    return result, "(使用 Google News RSS 作為 Yahoo News 備援)"
        except Exception:
            pass

        # Final fallback
        NEWS_CACHE[self.ticker] = (now, [
            {
                "title": "無法取得新聞資料",
                "summary": "請確認網路連線或提供 API Key 的新聞來源。",
                "publisher": "",
                "sentiment": 0.0,
            }
        ])
        diskn = _load_disk_cache(NEWS_CACHE_FILE)
        diskn[self.ticker] = {"ts": now, "items": NEWS_CACHE[self.ticker][1]}
        _save_disk_cache(NEWS_CACHE_FILE, diskn)
        return (
            [
                {
                    "title": "無法取得新聞資料",
                    "summary": "請確認網路連線或提供 API Key 的新聞來源。",
                    "publisher": "",
                    "sentiment": 0.0,
                }
            ],
            "無可用新聞來源：Yahoo 與 Google RSS 均未回傳結果。"
        )

    def analyze(self) -> dict[str, object]:
        news, news_status = self.get_financial_news()
        overall_score = round(sum(item["sentiment"] for item in news) / len(news), 2)
        sentiment_label = "偏向樂觀" if overall_score > 0 else "偏向悲觀" if overall_score < 0 else "中性"

        news_list = [
            {
                "title": item["title"],
                "score": item["sentiment"],
                "interpretation": item["summary"],
            }
            for item in news
        ]

        return {
            "report_type": "sentiment",
            "overall_score": overall_score,
            "sentiment_label": sentiment_label,
            "news_status": news_status,
            "news_available": news_status == "",
            "news_list": news_list,
        }


class Orchestrator:
    def __init__(self, ticker: str) -> None:
        self.ticker = ticker
        self.quant_agent = QuantDataAgent(ticker)
        self.sentiment_agent = SentimentAgent(ticker)

    def cross_verify(self, quant: dict[str, object], sentiment: dict[str, object]) -> dict[str, list[str]]:
        findings: list[str] = []
        quant_side = quant["technical_conclusion"]
        score = sentiment["overall_score"]

        if quant_side == "多" and score < -0.2:
            findings.append("技術面看多，但輿情偏空，存在訊號背離。")
        elif quant_side == "空" and score > 0.2:
            findings.append("技術面看空，但輿情偏多，需警惕短期反彈。")
        else:
            findings.append("量化與輿情方向基本一致。")

        return {"cross_verification": findings}

    def build_final_report(self, quant: dict[str, object], sentiment: dict[str, object], verification: dict[str, list[str]]) -> dict[str, object]:
        support = quant["support"]
        resistance = quant["resistance"]
        final_recommendation = (
            f"短期觀察 {support} 支撐，若守穩可維持多頭；若跌破則須降低持股。"
            if quant["technical_conclusion"] == "多"
            else f"若反彈至 {resistance} 遇壓回落，可考慮短線佈局；若持續失守 {support}，應控制風險。"
        )

        return {
            "ticker": self.ticker,
            "quant_report": quant,
            "sentiment_report": sentiment,
            "cross_verification": verification["cross_verification"],
            "final_recommendation": final_recommendation,
            "risk_management": [
                f"短期防守價：{support}",
                f"壓力價位：{resistance}",
                "若輿情轉弱且成交量放大，應降低倉位並重新檢視資金管理。",
            ],
        }

    def run(self) -> dict[str, object]:
        quant_report = self.quant_agent.analyze()
        sentiment_report = self.sentiment_agent.analyze()
        verification = self.cross_verify(quant_report, sentiment_report)
        return self.build_final_report(quant_report, sentiment_report, verification)
