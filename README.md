# AI Agent 趨勢文案寫手

一個基於 AI 的智能內容創作工具，結合 Google Trends 數據和多 Agent 協作技術，自動生成高質量的影片腳本和社群媒體內容。

## 核心

### 雙工作流程架構
- **LangGraph 工作流程** (推薦)：結構化處理流程，支援直接 URL 分析和動態爬蟲
- **AutoGen 工作流程**：多 Agent 協作對話模式

### LangGraph 工作流程優勢
- **直接URL分析** - 從趨勢新聞URL獲取最新內容
- **智能結構分析** - 自動分析網站HTML結構
- **動態程式碼生成** - AI根據網站特性生成客製化爬蟲程式碼
- **安全執行環境** - 隔離環境中執行生成的程式碼
- **詳細摘要報告** - 整合所有數據源生成深度分析
- **結構化流程** - 清晰的進度追蹤

## 技術架構

### 主要依賴
- **Streamlit** - Web UI 框架
- **LangGraph** - 工作流程編排 (新架構)
- **AutoGen** - 多 Agent 協作 (原始架構)
- **LangChain** - LLM 整合框架
- **BeautifulSoup4** - 網頁解析
- **Requests** - HTTP 請求處理

### AI 工作流程節點
1. **URL分析節點** - 分析趨勢URL的網站結構
2. **程式碼生成節點** - AI生成客製化爬蟲程式碼
3. **執行節點** - 安全執行爬蟲程式碼
4. **摘要節點** - 整合爬蟲結果生成摘要
5. **腳本創作節點** - 生成60秒影片腳本
6. **社群內容節點** - 創作多平台社群媒體內容

## 快速開始

### 環境需求
- Python 3.8+
- pip 或 conda 套件管理器

### 1. 安裝依賴
```bash
pip install -r requirements.txt
```

### 2. 環境配置
創建 `.env` 文件並設定以下環境變數：

```env
# OpenAI API 配置 (用於 VLLM 服務)
OPENAI_API_KEY=your_vllm_api_key
OPENAI_API_BASE=http://your-vllm-server:port/v1
OPENAI_MODEL_NAME=your_model_name

# Tavily API (用於網路搜尋)
TAVILY_API_KEY=your_tavily_api_key
```

### 3. 啟動應用程式
```bash
streamlit run app.py --server.port 8006
```

## 使用方式

### 步驟1: 工作流程選擇
在左側邊欄選擇工作流程引擎：
- **LangGraph** - 推薦用於深度內容分析
- **AutoGen** - 適合複雜推理和對話

### 步驟2: API Key 設定
輸入你的 Tavily API Key 並點擊「儲存」

### 步驟3: 獲取趨勢
點擊「獲取熱門趨勢」按鈕從 Google Trends 獲取最新熱門話題

### 步驟4: 選擇主題
- 瀏覽熱門趨勢列表
- 查看每個趨勢的詳細資訊和相關新聞
- 選擇感興趣的主題作為創作素材

### 步驟5: 生成內容
點擊「開始生成內容」，系統將自動：
- 分析選定主題的相關網站
- 提取關鍵資訊和數據
- 生成60秒影片腳本
- 創作多平台社群媒體內容

### 步驟6: 查看與匯出
在不同標籤頁中查看生成的內容：
- **影片腳本** - 結構化的60秒影片腳本
- **社群媒體** - Instagram、Twitter、LinkedIn內容
- **摘要報告** - 深度分析報告 (LangGraph 專用)
- **匯出** - JSON 和文本格式下載

## 設定配置

### config/settings.py
主要配置文件，包含：
- API 端點設定
- 模型參數配置
- 系統行為設定

### config/agents_config.py
Agent 提示詞配置：
- 研究員 Agent 提示詞
- 腳本作家 Agent 提示詞
- 社群媒體作家 Agent 提示詞
- 網路爬蟲 Agent 提示詞

### tools/ 目錄
各種工具模組：
- `trend_fetcher.py` - Google Trends 數據獲取
- `web_search.py` - 網路搜尋功能
- `web_scraper_tools.py` - 網頁爬蟲工具
- `content_formatter.py` - 內容格式化工具

## 進階配置

### 自定義 LLM 配置
修改 `agents/langgraph_workflow.py` 中的 `get_llm()` 函數：
```python
def get_llm():
    return ChatOpenAI(
        model="your-custom-model",
        api_key="your-api-key",
        base_url="your-api-base",
        temperature=0.7,  # 調整創意程度
        max_tokens=2000   # 調整最大輸出長度
    )
```

### 工作流程自定義
在 `create_langgraph_workflow()` 函數中添加新節點或修改流程邊：
```python
# 添加新節點
workflow.add_node("custom_node", custom_node_function)

# 修改流程邊
workflow.add_edge("summarize", "custom_node")
workflow.add_edge("custom_node", "write_script")
```

## 輸出格式

### 影片腳本結構
```
【開場白 (0-10秒)】
- 吸引人的開場
- 主題介紹

【主要內容 (10-50秒)】
- 核心要點1
- 核心要點2
- 統計數據支撐

【結論 (50-60秒)】
- 總結要點
- 行動呼籲
```

### 社群媒體內容
- **Instagram/Facebook** - 視覺化內容 + 標籤
- **Twitter/X** - 簡潔推文 (280字內)
- **LinkedIn** - 專業分析 + 商業價值

## 故障排除

### 常見問題

**Q: 無法獲取趨勢數據**
A: 檢查網路連線和 Google Trends 服務狀態

**Q: LangGraph 工作流程失敗**
A: 確認 OpenAI API 配置正確，檢查 VLLM、ollama 服務狀態

**Q: 網頁爬蟲執行失敗**
A: 檢查目標網站的可訪問性，某些網站可能有反爬蟲機制

**Q: 生成的內容質量不佳**
A: 調整 LLM 參數（temperature, max_tokens），或優化提示詞

### 日誌查看
應用程式會輸出詳細的執行日誌，包含：
- 各節點執行狀態
- 錯誤資訊和堆疊追蹤
- 性能指標

## 貢獻指南

歡迎提交 Issue 和 Pull Request！

### 開發環境設定
```bash
git clone <repository>
cd agent-trend
pip install -r requirements.txt
```

### 程式碼結構
```
agents/              # AI Agent 相關
├── workflow.py      # AutoGen 工作流程
├── langgraph_workflow.py  # LangGraph 工作流程
config/              # 配置文件
├── settings.py      # 主要設定
├── agents_config.py # Agent 配置
tools/               # 工具模組
├── trend_fetcher.py # 趨勢獲取
├── web_search.py    # 網路搜尋
└── web_scraper_tools.py  # 爬蟲工具
```

## 授權條款

MIT License

## 更新日誌

### v1.0.0
- AutoGen 工作流程
- LangGraph 工作流程
- 爬蟲整合
- Google Trends 整合
- 影片腳本生成
- 社群媒體內容創作
