# Stock Analysis Dual-Agent Scaffold

這是一個雙 Agent 架構範例專案，包含：

- `prompts/quant_agent.md`：量化數據官 prompt
- `prompts/sentiment_agent.md`：輿情研究員 prompt
- `prompts/master_prompt.md`：主控流程 prompt
- `main.py`：範例 Python 主控程式

## 使用方式

1. 安裝所需套件：
   ```bash
   pip install -r requirements.txt
   ```
2. 執行 CLI 分析：
   ```bash
   python main.py 2330.TW
   ```
3. 執行可視化平台：
   ```bash
   streamlit run streamlit_app.py
   ```

> Yahoo Finance 台灣股票通常需要加上 `.TW`；例如 `2330.TW`。

## 觀察清單功能

- 側邊欄可編輯觀察清單，每行一個股票代碼
- 可快速新增單一股票到清單
- 可批次分析觀察清單中的所有股票
- 可篩選出「入場機會」的標的

## 專案結構

- `stock_analysis.py`：核心分析模組，包含量化 Agent、輿情 Agent 與主控整合流程
- `main.py`：CLI 入口，輸出 JSON 格式結果
- `streamlit_app.py`：可視化平台，輸入股票代碼即可顯示分析報告與圖表
- `requirements.txt`：所需套件
- `prompts/`：Claude Code 雙 Agent prompt 檔案
