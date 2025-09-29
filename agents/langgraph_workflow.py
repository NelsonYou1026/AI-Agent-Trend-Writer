import logging
from typing import Dict, List, TypedDict, Annotated
from dataclasses import dataclass
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import re

# LangGraph imports
from langgraph.graph import StateGraph
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from config import settings
from config.agents_config import (
    RESEARCHER_PROMPT,
    SCRIPT_WRITER_PROMPT,
    SOCIAL_WRITER_PROMPT,
    WEB_SCRAPER_PROMPT,
)

logging.basicConfig(level=logging.INFO)


# State 定義
class WorkflowState(TypedDict):
    topic: str
    trend_urls: List[str]
    website_analyses: List[Dict]
    scraping_codes: List[Dict]
    scraped_data: List[Dict]
    summary: str
    video_script: str
    social_media: str
    progress_callback: callable
    error_messages: List[str]


@dataclass
class WebsiteStructure:
    """網站結構分析結果"""
    url: str
    title: str
    main_content_selectors: List[str]
    text_selectors: List[str]
    image_selectors: List[str]
    link_selectors: List[str]
    meta_info: Dict
    suggested_approach: str


def get_llm():
    """獲取配置好的 LLM"""
    return ChatOpenAI(
        model=settings.OPENAI_MODEL_NAME,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_API_BASE,
        extra_body={
            "chat_template_kwargs": {"enable_thinking": False},
        },
    )


def analyze_website_structure(url: str) -> WebsiteStructure:
    """
    分析網站HTML結構，為爬蟲代碼生成提供信息
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 分析網站結構
        title = soup.find('title')
        title_text = title.get_text().strip() if title else "No title found"
        
        # 尋找主要內容選擇器
        main_content_selectors = []
        for selector in ['main', 'article', '.content', '.main-content', '#content', '.post', '.entry']:
            if soup.select(selector):
                main_content_selectors.append(selector)
        
        # 尋找文本選擇器
        text_selectors = []
        for selector in ['p', 'h1', 'h2', 'h3', '.text', '.description', '.summary']:
            if soup.select(selector):
                text_selectors.append(selector)
        
        # 尋找圖片選擇器
        image_selectors = []
        for selector in ['img', '.image', '.photo', 'figure img']:
            if soup.select(selector):
                image_selectors.append(selector)
        
        # 尋找鏈接選擇器
        link_selectors = []
        for selector in ['a[href]', '.link', '.more-link']:
            if soup.select(selector):
                link_selectors.append(selector)
        
        # Meta 信息
        meta_info = {
            'domain': urlparse(url).netloc,
            'has_json_ld': bool(soup.find_all('script', type='application/ld+json')),
            'has_meta_description': bool(soup.find('meta', {'name': 'description'})),
            'page_lang': soup.find('html', {'lang': True}),
            'total_elements': len(soup.find_all()),
            'has_structured_data': bool(soup.select('[itemscope], [vocab]'))
        }
        
        # 建議的爬蟲方法
        if meta_info['has_json_ld']:
            suggested_approach = "json-ld"
        elif main_content_selectors:
            suggested_approach = "content-selector"
        elif text_selectors:
            suggested_approach = "text-extraction"
        else:
            suggested_approach = "general-scraping"
        
        return WebsiteStructure(
            url=url,
            title=title_text,
            main_content_selectors=main_content_selectors[:3],  # 取前3個
            text_selectors=text_selectors[:5],  # 取前5個
            image_selectors=image_selectors[:3],  # 取前3個
            link_selectors=link_selectors[:3],  # 取前3個
            meta_info=meta_info,
            suggested_approach=suggested_approach
        )
        
    except Exception as e:
        logging.error(f"Error analyzing website structure for {url}: {e}")
        return WebsiteStructure(
            url=url,
            title="Analysis failed",
            main_content_selectors=[],
            text_selectors=['p', 'h1', 'h2', 'h3'],  # 預設選擇器
            image_selectors=['img'],
            link_selectors=['a'],
            meta_info={'error': str(e)},
            suggested_approach="general-scraping"
        )


# 工作流程節點函數
def analyze_urls_node(state: WorkflowState) -> WorkflowState:
    """節點1: 分析趨勢URL的網站結構"""
    logging.info("🔍 開始分析網站結構...")
    
    if state.get('progress_callback'):
        state['progress_callback']("🔍 正在分析趨勢網站結構...")
    
    website_analyses = []
    for url in state['trend_urls'][:3]:  # 限制處理前3個URL
        try:
            analysis = analyze_website_structure(url)
            website_analyses.append({
                'url': url,
                'structure': analysis,
                'analysis_success': True
            })
            logging.info(f"✅ 成功分析: {url}")
        except Exception as e:
            website_analyses.append({
                'url': url,
                'structure': None,
                'analysis_success': False,
                'error': str(e)
            })
            logging.error(f"❌ 分析失敗: {url} - {e}")
    
    state['website_analyses'] = website_analyses
    return state


def generate_scraping_code_node(state: WorkflowState) -> WorkflowState:
    """節點2: Code Agent 生成爬蟲程式碼"""
    logging.info("🤖 Code Agent 生成爬蟲程式碼...")
    
    if state.get('progress_callback'):
        state['progress_callback']("🤖 Code Agent 正在生成爬蟲程式碼...")
    
    llm = get_llm()
    scraping_codes = []
    
    code_agent_prompt = """你是一個專業的爬蟲程式碼生成專家。根據提供的網站結構分析，生成高效的Python爬蟲程式碼。

要求：
1. 生成的程式碼必須是完整可執行的
2. 包含錯誤處理和重試機制
3. 提取網站的主要內容、標題、文本、圖片URL等
4. 返回結構化的JSON格式數據
5. 使用requests和BeautifulSoup庫

網站結構分析結果：
{analysis}

請生成針對此網站的爬蟲程式碼，程式碼應該包含一個main函數，接受url參數並返回爬取結果。"""

    for website_analysis in state['website_analyses']:
        if not website_analysis['analysis_success']:
            scraping_codes.append({
                'url': website_analysis['url'],
                'code': None,
                'generation_success': False,
                'error': website_analysis.get('error', 'Unknown error')
            })
            continue
            
        try:
            structure = website_analysis['structure']
            analysis_text = f"""
URL: {structure.url}
標題: {structure.title}
建議方法: {structure.suggested_approach}
主要內容選擇器: {structure.main_content_selectors}
文本選擇器: {structure.text_selectors}
圖片選擇器: {structure.image_selectors}
Meta信息: {structure.meta_info}
            """
            
            messages = [
                SystemMessage(content=code_agent_prompt.format(analysis=analysis_text)),
                HumanMessage(content=f"為 {structure.url} 生成爬蟲程式碼")
            ]
            
            response = llm.invoke(messages)
            generated_code = response.content
            
            # 從回應中提取程式碼
            if "```python" in generated_code:
                code_start = generated_code.find("```python") + 9
                code_end = generated_code.find("```", code_start)
                if code_end != -1:
                    generated_code = generated_code[code_start:code_end].strip()
            
            scraping_codes.append({
                'url': structure.url,
                'code': generated_code,
                'generation_success': True,
                'structure_info': analysis_text
            })
            
            logging.info(f"✅ 成功生成爬蟲程式碼: {structure.url}")
            
        except Exception as e:
            scraping_codes.append({
                'url': website_analysis['url'],
                'code': None,
                'generation_success': False,
                'error': str(e)
            })
            logging.error(f"❌ 程式碼生成失敗: {website_analysis['url']} - {e}")
    
    state['scraping_codes'] = scraping_codes
    return state


def execute_scraping_code_node(state: WorkflowState) -> WorkflowState:
    """節點3: Code Executor Proxy 執行爬蟲程式碼"""
    logging.info("⚙️ 執行爬蟲程式碼...")
    
    if state.get('progress_callback'):
        state['progress_callback']("⚙️ Code Executor 正在執行爬蟲程式碼...")
    
    scraped_data = []
    
    for code_info in state['scraping_codes']:
        if not code_info['generation_success'] or not code_info['code']:
            scraped_data.append({
                'url': code_info['url'],
                'data': None,
                'execution_success': False,
                'error': code_info.get('error', 'No code to execute')
            })
            continue
        
        try:
            # 準備執行環境
            exec_globals = {
                'requests': requests,
                'BeautifulSoup': BeautifulSoup,
                'json': json,
                'urlparse': urlparse,
                'urljoin': urljoin,
                're': re
            }
            
            # 執行程式碼
            exec(code_info['code'], exec_globals)
            
            # 調用main函數（假設生成的程式碼包含main函數）
            if 'main' in exec_globals:
                result = exec_globals['main'](code_info['url'])
                scraped_data.append({
                    'url': code_info['url'],
                    'data': result,
                    'execution_success': True
                })
                logging.info(f"✅ 成功執行爬蟲: {code_info['url']}")
            else:
                scraped_data.append({
                    'url': code_info['url'],
                    'data': None,
                    'execution_success': False,
                    'error': 'No main function found in generated code'
                })
                
        except Exception as e:
            scraped_data.append({
                'url': code_info['url'],
                'data': None,
                'execution_success': False,
                'error': str(e)
            })
            logging.error(f"❌ 爬蟲執行失敗: {code_info['url']} - {e}")
    
    state['scraped_data'] = scraped_data
    return state


def summary_agent_node(state: WorkflowState) -> WorkflowState:
    """節點4: Summary Agent 整合爬蟲結果"""
    logging.info("📋 Summary Agent 整合爬蟲結果...")
    
    if state.get('progress_callback'):
        state['progress_callback']("📋 Summary Agent 正在整合爬蟲結果...")
    
    llm = get_llm()
    
    # 整理所有成功的爬蟲數據
    successful_data = []
    for item in state['scraped_data']:
        if item['execution_success'] and item['data']:
            successful_data.append({
                'url': item['url'],
                'content': item['data']
            })
    
    if not successful_data:
        state['summary'] = f"關於主題 '{state['topic']}' 的爬蟲過程中沒有獲得有效數據，請檢查網站可訪問性或調整爬蟲策略。"
        return state
    
    summary_prompt = f"""你是一個專業的內容分析專家。請根據以下爬蟲獲取的數據，為主題 "{state['topic']}" 生成一個全面的摘要報告。

爬蟲數據：
{json.dumps(successful_data, ensure_ascii=False, indent=2)}

請提供：
1. 主題的核心要點和關鍵信息
2. 重要的統計數據或事實
3. 最新的發展動態
4. 相關的背景信息
5. 值得關注的趋势或影響

要求：
- 內容要準確、客觀
- 重點突出，層次分明
- 適合用於後續的影片腳本創作
- 字數控制在800-1200字之間
"""
    
    try:
        messages = [
            SystemMessage(content=summary_prompt),
            HumanMessage(content=f"請為主題 '{state['topic']}' 生成摘要報告")
        ]
        
        response = llm.invoke(messages)
        state['summary'] = response.content
        logging.info("✅ 成功生成摘要報告")
        
    except Exception as e:
        state['summary'] = f"摘要生成過程中出現錯誤：{str(e)}"
        logging.error(f"❌ 摘要生成失敗: {e}")
    
    return state


def script_writer_node(state: WorkflowState) -> WorkflowState:
    """節點5: Script Writer 創作影片腳本"""
    logging.info("🎬 Script Writer 創作影片腳本...")
    
    if state.get('progress_callback'):
        state['progress_callback']("🎬 Script Writer 正在創作影片腳本...")
    
    llm = get_llm()
    
    script_prompt = f"""你是一個專業的影片腳本作家。請根據提供的摘要內容，為主題 "{state['topic']}" 創作一個60秒的影片腳本。

摘要內容：
{state['summary']}

腳本要求：
1. 時長：適合60秒影片（約150-180字）
2. 結構：開場白(10秒) + 主要內容(40秒) + 結論(10秒)
3. 語調：專業但易懂，吸引觀眾
4. 包含：關鍵統計數據、具體事實、行動呼籲
5. 格式：標明時間節點和旁白內容

請創作出引人入勝的影片腳本。
"""
    
    try:
        messages = [
            SystemMessage(content=script_prompt),
            HumanMessage(content=f"請為主題 '{state['topic']}' 創作60秒影片腳本")
        ]
        
        response = llm.invoke(messages)
        state['video_script'] = response.content
        logging.info("✅ 成功創作影片腳本")
        
    except Exception as e:
        state['video_script'] = f"影片腳本創作過程中出現錯誤：{str(e)}"
        logging.error(f"❌ 影片腳本創作失敗: {e}")
    
    return state


def social_media_writer_node(state: WorkflowState) -> WorkflowState:
    """節點6: Social Media Writer 創作社群媒體內容"""
    logging.info("📱 Social Media Writer 創作社群媒體內容...")
    
    if state.get('progress_callback'):
        state['progress_callback']("📱 Social Media Writer 正在創作社群媒體內容...")
    
    llm = get_llm()
    
    social_prompt = f"""你是一個專業的社群媒體內容創作者。請根據影片腳本和摘要內容，為主題 "{state['topic']}" 創作社群媒體貼文。

影片腳本：
{state['video_script']}

摘要內容：
{state['summary']}

請為以下平台創作內容：

1. **Instagram/Facebook 貼文**：
   - 吸引人的開場
   - 2-3個關鍵點
   - 相關標籤 (#hashtags)
   - 行動呼籲

2. **Twitter/X 推文**：
   - 簡潔有力（280字以內）
   - 包含1-2個要點
   - 相關標籤

3. **LinkedIn 文章**：
   - 專業語調
   - 深度分析
   - 商業價值導向
   - 專業標籤

每個平台的內容要符合其特色和用戶習慣。
"""
    
    try:
        messages = [
            SystemMessage(content=social_prompt),
            HumanMessage(content=f"請為主題 '{state['topic']}' 創作多平台社群媒體內容")
        ]
        
        response = llm.invoke(messages)
        state['social_media'] = response.content
        logging.info("✅ 成功創作社群媒體內容")
        
    except Exception as e:
        state['social_media'] = f"社群媒體內容創作過程中出現錯誤：{str(e)}"
        logging.error(f"❌ 社群媒體內容創作失敗: {e}")
    
    return state


def create_langgraph_workflow():
    """創建 LangGraph 工作流程"""
    
    # 創建狀態圖
    workflow = StateGraph(WorkflowState)
    
    # 添加節點
    workflow.add_node("analyze_urls", analyze_urls_node)
    workflow.add_node("generate_code", generate_scraping_code_node)
    workflow.add_node("execute_code", execute_scraping_code_node)
    workflow.add_node("summarize", summary_agent_node)
    workflow.add_node("write_script", script_writer_node)
    workflow.add_node("write_social", social_media_writer_node)
    
    # 設定流程邊
    workflow.set_entry_point("analyze_urls")
    workflow.add_edge("analyze_urls", "generate_code")
    workflow.add_edge("generate_code", "execute_code")
    workflow.add_edge("execute_code", "summarize")
    workflow.add_edge("summarize", "write_script")
    workflow.add_edge("write_script", "write_social")
    workflow.set_finish_point("write_social")
    
    return workflow.compile()


def run_langgraph_workflow(topic: str, trend_urls: List[str], progress_callback=None) -> Dict[str, str]:
    """
    使用 LangGraph 執行完整的工作流程
    
    Args:
        topic (str): 主題
        trend_urls (List[str]): 趨勢URL列表
        progress_callback (callable): 進度回調函數
    
    Returns:
        Dict[str, str]: 包含影片腳本和社群媒體內容的字典
    """
    try:
        # 創建工作流程
        workflow = create_langgraph_workflow()
        
        # 初始化狀態
        initial_state = WorkflowState(
            topic=topic,
            trend_urls=trend_urls,
            website_analyses=[],
            scraping_codes=[],
            scraped_data=[],
            summary="",
            video_script="",
            social_media="",
            progress_callback=progress_callback,
            error_messages=[]
        )
        
        if progress_callback:
            progress_callback("🚀 啟動 LangGraph 工作流程...")
        
        # 執行工作流程
        final_state = workflow.invoke(initial_state)
        
        if progress_callback:
            progress_callback("✅ LangGraph 工作流程執行完成！")
        
        # 返回結果
        return {
            "video_script": final_state.get('video_script', '影片腳本生成失敗'),
            "social_media": final_state.get('social_media', '社群媒體內容生成失敗'),
            "summary": final_state.get('summary', ''),
            "scraped_data_count": len([d for d in final_state.get('scraped_data', []) if d.get('execution_success')]),
            "processed_urls": [analysis['url'] for analysis in final_state.get('website_analyses', [])]
        }
        
    except Exception as e:
        logging.error(f"❌ LangGraph 工作流程執行失敗: {e}")
        return {
            "video_script": f"工作流程執行失敗：{str(e)}",
            "social_media": f"工作流程執行失敗：{str(e)}",
            "summary": "",
            "scraped_data_count": 0,
            "processed_urls": []
        }


if __name__ == '__main__':
    # 測試範例
    test_topic = "AI 技術發展趨勢"
    test_urls = [
        "https://example.com/ai-news1",
        "https://example.com/ai-news2", 
        "https://example.com/ai-news3"
    ]
    
    def test_callback(message):
        print(f"進度更新: {message}")
    
    result = run_langgraph_workflow(test_topic, test_urls, test_callback)
    
    print("=== 影片腳本 ===")
    print(result["video_script"])
    print("\n=== 社群媒體內容 ===")
    print(result["social_media"])