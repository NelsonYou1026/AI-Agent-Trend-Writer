import logging
from typing import Dict, List

import autogen
from autogen import Agent, AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager

from config import settings
from config.agents_config import (
    RESEARCHER_PROMPT,
    SCRIPT_WRITER_PROMPT,
    SOCIAL_WRITER_PROMPT,
    WEB_SCRAPER_PROMPT,
)

# 協調者 Agent 提示詞
COORDINATOR_PROMPT = """
你是一個專業的工作流程協調者 (Workflow Coordinator)。你的職責是：

1. **監控進度**: 確保所有 Agent 按計劃完成任務
2. **質量控制**: 檢查每個 Agent 的輸出是否符合要求
3. **流程管理**: 確保工作流程順利進行
4. **最終確認**: 當所有工作完成時，宣布工作完成並觸發停止

工作流程檢查清單：
- ✅ Trend_Researcher 是否完成主題研究並提供結構化資料？
- ✅ Web_Scraper 是否成功爬取相關網頁並提供詳細資料？
- ✅ Script_Writer 是否基於研究資料創作了 60 秒影片腳本？
- ✅ Social_Media_Writer 是否創作了社群媒體文案？
- ✅ 所有內容是否品質良好，符合要求？

當所有任務都完成且品質合格時，你必須回覆：
"WORKFLOW_COMPLETE - 所有任務已完成，品質檢查通過！

請 user_proxy 按照以下精確格式整理最終內容：
===FINAL_OUTPUT_START===
@@VIDEO_SCRIPT@@
[完整的影片腳本內容]
@@VIDEO_SCRIPT_END@@
@@SOCIAL_MEDIA@@
[完整的社群媒體內容]
@@SOCIAL_MEDIA_END@@
===FINAL_OUTPUT_END==="

如果發現任何問題，請明確指出需要改進的地方，並要求相關 Agent 修正。
"""
from tools.web_search import WebSearch
from tools.web_scraper_tools import fetch_webpage, execute_python_code, validate_scraped_data, generate_scraping_template

logging.basicConfig(level=logging.INFO)


def get_llm_config() -> Dict:
    """
    Constructs the language model configuration for AutoGen agents.

    Returns:
        Dict: A dictionary containing the LLM configuration.
    """
    return {
        "model": settings.OPENAI_MODEL_NAME,
        "api_key": settings.OPENAI_API_KEY,
        "base_url": settings.OPENAI_API_BASE,
        "extra_body": {
                "chat_template_kwargs": {"enable_thinking": False},
                },
    }


def run_workflow(topic: str, progress_callback=None, selected_topic_data: dict = None) -> Dict[str, str]:
    """
    Orchestrates the collaboration between AI agents to generate content for a given topic.

    Args:
        topic (str): The topic to research and write about.
        progress_callback (callable, optional): Function to call with progress updates.
        selected_topic_data (dict, optional): Complete topic data including news URLs from trends.

    Returns:
        Dict[str, str]: A dictionary containing the generated 'video_script' and 'social_media' content.
    """
    llm_config = get_llm_config()
    
    # 初始化進度追蹤
    if progress_callback:
        progress_callback("🚀 初始化 AI Agents...")
    
    # Initialize the web search tool
    web_search_tool = WebSearch()

    # Define the UserProxyAgent that will execute function calls
    user_proxy = UserProxyAgent(
        name="user_proxy",
        is_termination_msg=lambda x: (
            x.get("content", "") and 
            ("===FINAL_OUTPUT_END===" in x.get("content", "") or 
             "WORKFLOW_COMPLETE" in x.get("content", "") or 
             "FINAL_CONTENT" in x.get("content", ""))
        ),
        human_input_mode="NEVER",
        max_consecutive_auto_reply=20,
        code_execution_config=False,
    )

    # Define the Researcher Agent
    researcher = AssistantAgent(
        name="Trend_Researcher",
        system_message=RESEARCHER_PROMPT.format(topic=topic),
        llm_config=llm_config,
    )
    
    # Register the search function for the researcher
    def search_for_topic(query: str) -> str:
        """Function to be called by the researcher agent to search the web."""
        # 提取趨勢新聞 URL
        trend_urls = []
        if selected_topic_data and selected_topic_data.get('news_items'):
            trend_urls = [news.get('url') for news in selected_topic_data['news_items'] if news.get('url')]
            if progress_callback and trend_urls:
                progress_callback(f"🗞️ 發現 {len(trend_urls)} 個趨勢相關新聞，正在爬取最新內容...")
            logging.info(f"從趨勢數據提取到 {len(trend_urls)} 個相關新聞URL")
        
        results = web_search_tool.search(query, trend_urls=trend_urls)
        
        if progress_callback:
            total_results = len(results) if results else 0
            trend_count = sum(1 for r in results if r.get('source') == 'Trending News')
            tavily_count = sum(1 for r in results if r.get('source') == 'Tavily')
            progress_callback(f"📚 研究完成：獲取 {total_results} 個資料來源 (最新新聞: {trend_count}, Tavily: {tavily_count})")
        
        return str(results)

    # 為 Web Scraper 定義工具函數
    def fetch_webpage_content(url: str) -> str:
        """由 Web Scraper Agent 調用來獲取網頁內容"""
        if progress_callback:
            progress_callback(f"🌐 正在獲取網頁: {url}")
        return fetch_webpage(url)
    
    def execute_scraping_code(code: str) -> str:
        """由 Web Scraper Agent 調用來執行爬蟲程式碼"""
        if progress_callback:
            progress_callback("🔧 執行自定義爬蟲程式碼...")
        result = execute_python_code(code)
        return str(result)
    
    user_proxy.register_function(
        function_map={
            "search_for_topic": search_for_topic,
            "fetch_webpage_content": fetch_webpage_content,
            "execute_scraping_code": execute_scraping_code
        }
    )
    
    researcher.register_function(
        function_map={
            "search_for_topic": search_for_topic
        }
    )


    # Define the Script Writer Agent
    script_writer = AssistantAgent(
        name="Script_Writer",
        system_message=SCRIPT_WRITER_PROMPT,
        llm_config=llm_config,
    )

    # Define the Social Media Writer Agent
    social_writer = AssistantAgent(
        name="Social_Media_Writer",
        system_message=SOCIAL_WRITER_PROMPT,
        llm_config=llm_config,
    )

    # Define the Web Scraper Agent
    web_scraper = AssistantAgent(
        name="Web_Scraper",
        system_message=WEB_SCRAPER_PROMPT,
        llm_config=llm_config,
    )
    
    # Register web scraping functions for the Web Scraper Agent
    web_scraper.register_function(
        function_map={
            "fetch_webpage_content": fetch_webpage_content,
            # "execute_scraping_code": execute_scraping_code
        }
    )

    # Define the Workflow Coordinator Agent
    coordinator = AssistantAgent(
        name="Workflow_Coordinator",
        system_message=COORDINATOR_PROMPT,
        llm_config=llm_config,
    )
    
    if progress_callback:
        progress_callback("🤖 AI Agents 組建完成，開始協作...")

    # Create the GroupChat and Manager
    agents: List[Agent] = [user_proxy, researcher, web_scraper, script_writer, social_writer, coordinator]
    groupchat = GroupChat(agents=agents, messages=[], max_round=20)
    manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config)

    # Initial message to kick off the process
    initial_message = f"""
    主題選定："{topic}"

    工作流程計劃：
    1.  **Trend_Researcher**: 使用 `search_for_topic` 工具研究主題 '{topic}'。將發現整理成結構化 JSON 格式，包含關鍵點、統計資料和來源。
    2.  **Web_Scraper**: 針對研究過程中發現的重要 URL，使用 `fetch_webpage_content` 獲取網頁，分析結構後用 `execute_scraping_code` 執行客製化爬蟲程式碼，提供更詳細的結構化資料。
    3.  **Script_Writer**: 研究和爬蟲完成後，使用所有結構化資料撰寫 60 秒影片腳本。
    4.  **Social_Media_Writer**: 根據研究、爬蟲資料和影片腳本，為 Instagram/Facebook、X/Twitter 和 LinkedIn 創作社群媒體文案。
    5.  **Workflow_Coordinator**: 監控所有任務進度，確保品質，當所有工作完成時宣布 "WORKFLOW_COMPLETE" 並要求 user_proxy 格式化輸出。
    5.  **user_proxy**: 當協調者確認工作完成後，必須按照以下精確格式整理最終輸出：
        
        ===FINAL_OUTPUT_START===
        @@VIDEO_SCRIPT@@
        [完整的60秒影片腳本內容]
        @@VIDEO_SCRIPT_END@@
        @@SOCIAL_MEDIA@@
        [完整的社群媒體文案內容]
        @@SOCIAL_MEDIA_END@@
        ===FINAL_OUTPUT_END===

    請開始執行！
    """
    
    if progress_callback:
        progress_callback("🔍 Trend_Researcher 正在研究主題...")

    # Start the chat
    if progress_callback:
        progress_callback("🔄 開始 AI Agents 協作對話...")
    
    user_proxy.initiate_chat(
        manager,
        message=initial_message,
    )
    
    # 根據對話歷史更新進度
    if progress_callback:
        messages = groupchat.messages
        for msg in messages[-10:]:  # 檢查最後10條消息
            sender = msg.get("name", "")
            content = msg.get("content", "")
            
            if sender == "Web_Scraper" and len(content) > 50:
                progress_callback("🕷️ Web_Scraper 正在分析和爬取網頁...")
            elif sender == "Script_Writer" and len(content) > 50:
                progress_callback("🎬 Script_Writer 正在創作影片腳本...")
            elif sender == "Social_Media_Writer" and len(content) > 50:
                progress_callback("📱 Social_Media_Writer 正在撰寫社群文案...")
            elif sender == "Workflow_Coordinator" and "WORKFLOW_COMPLETE" in content:
                progress_callback("✅ Workflow_Coordinator 確認所有任務完成...")
        
        progress_callback("📋 正在提取生成的內容...")

    # Extract the final content with improved parsing logic
    def extract_content_from_messages(messages: List[Dict]) -> Dict[str, str]:
        """從消息歷史中智能提取內容"""
        video_script = None
        social_media = None
        
        # 檢查所有消息，尋找內容
        for msg in reversed(messages):  # 從最新消息開始檢查
            content = msg.get("content", "")
            sender = msg.get("name", "")
            
            # 優先使用新格式
            if "===FINAL_OUTPUT_START===" in content:
                try:
                    if "@@VIDEO_SCRIPT@@" in content and "@@SOCIAL_MEDIA@@" in content:
                        video_part = content.split("@@VIDEO_SCRIPT@@")[1].split("@@VIDEO_SCRIPT_END@@")[0].strip()
                        social_part = content.split("@@SOCIAL_MEDIA@@")[1].split("@@SOCIAL_MEDIA_END@@")[0].strip()
                        return {"video_script": video_part, "social_media": social_part}
                except (IndexError, AttributeError):
                    continue
            
            # 嘗試舊格式
            if "---VIDEO_SCRIPT_START---" in content:
                try:
                    video_part = content.split("---VIDEO_SCRIPT_START---")[1].split("---VIDEO_SCRIPT_END---")[0].strip()
                    if len(video_part) > 50:
                        video_script = video_part
                except (IndexError, AttributeError):
                    continue
                    
            if "---SOCIAL_MEDIA_START---" in content:
                try:
                    social_part = content.split("---SOCIAL_MEDIA_START---")[1].split("---SOCIAL_MEDIA_END---")[0].strip()
                    if len(social_part) > 30:
                        social_media = social_part
                except (IndexError, AttributeError):
                    continue
            
            # 智能識別內容類型
            if sender == "Script_Writer" and len(content) > 100:
                if not video_script and any(keyword in content.lower() for keyword in 
                    ["腳本", "script", "影片", "video", "旁白", "開場"]):
                    video_script = content
                    
            elif sender == "Social_Media_Writer" and len(content) > 50:
                if not social_media and any(keyword in content.lower() for keyword in 
                    ["社群", "social", "instagram", "facebook", "twitter", "linkedin", "貼文"]):
                    social_media = content
        
        return {
            "video_script": video_script or "無法提取影片腳本內容",
            "social_media": social_media or "無法提取社群媒體內容"
        }
    
    final_message = user_proxy.last_message()["content"]
    logging.info(f"Final message received: {final_message[:200]}...")
    
    # 嘗試多種提取方法
    content_extracted = False
    video_script = None
    social_media = None
    
    try:
        # 方法1: 嘗試新格式
        if "===FINAL_OUTPUT_START===" in final_message:
            if "@@VIDEO_SCRIPT@@" in final_message and "@@SOCIAL_MEDIA@@" in final_message:
                video_script = final_message.split("@@VIDEO_SCRIPT@@")[1].split("@@VIDEO_SCRIPT_END@@")[0].strip()
                social_media = final_message.split("@@SOCIAL_MEDIA@@")[1].split("@@SOCIAL_MEDIA_END@@")[0].strip()
                content_extracted = True
                logging.info("✅ @@格式成功提取內容")
        
        # 方法2: 嘗試舊格式
        if not content_extracted and "---VIDEO_SCRIPT_START---" in final_message:
            video_script = final_message.split("---VIDEO_SCRIPT_START---")[1].split("---VIDEO_SCRIPT_END---")[0].strip()
            social_media = final_message.split("---SOCIAL_MEDIA_START---")[1].split("---SOCIAL_MEDIA_END---")[0].strip()
            content_extracted = True
            logging.info("✅ 使用舊格式成功提取內容")
        
        # 方法3: 從對話歷史智能提取
        if not content_extracted:
            logging.warning("🔍 標準格式未找到，開始智能內容提取...")
            extracted_content = extract_content_from_messages(groupchat.messages)
            video_script = extracted_content["video_script"]
            social_media = extracted_content["social_media"]
            logging.info("📋 智能提取完成")
            
    except Exception as e:
        logging.error(f"❌ 內容提取過程中發生錯誤: {e}")
        # 最後嘗試：從對話歷史提取
        extracted_content = extract_content_from_messages(groupchat.messages)
        video_script = extracted_content["video_script"]
        social_media = extracted_content["social_media"]
    
    # 確保返回有效內容
    if not video_script or len(video_script.strip()) < 20:
        video_script = "內容生成過程中出現問題，請重新嘗試。"
    if not social_media or len(social_media.strip()) < 10:
        social_media = "內容生成過程中出現問題，請重新嘗試。"
        
    logging.info(f"📊 最終提取結果 - 影片腳本長度: {len(video_script)}, 社群內容長度: {len(social_media)}")
    
    # 記錄詳細的內容片段供調試
    logging.info(f"🎬 影片腳本前100字符: {video_script[:100]}...")
    logging.info(f"📱 社群內容前100字符: {social_media[:100]}...")

    return {
        "video_script": video_script,
        "social_media": social_media,
    }


if __name__ == '__main__':
    # Example usage:
    # Ensure .env file has the necessary API keys
    test_topic = "NVIDIA GTC 2024"
    content = run_workflow(test_topic)
    print("--- Generated Video Script ---")
    print(content["video_script"])
    print("\n--- Generated Social Media Content ---")
    print(content["social_media"])
