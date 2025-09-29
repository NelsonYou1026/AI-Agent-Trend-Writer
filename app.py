import streamlit as st
from streamlit_extras.app_logo import add_logo
import logging

# 導入兩種工作流程
from agents.workflow import run_workflow  # 原始 AutoGen 工作流程
from agents.langgraph_workflow import run_langgraph_workflow  # 新的 LangGraph 工作流程

from config import settings
from tools.content_formatter import ContentFormatter
from tools.trend_fetcher import TrendFetcher

# 設定日誌
logging.basicConfig(level=logging.INFO)

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Agent Trend Content Writer - Enhanced",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Initialize Session State ---
if "trends" not in st.session_state:
    st.session_state.trends = []
if "selected_topic" not in st.session_state:
    st.session_state.selected_topic = None
if "generated_content" not in st.session_state:
    st.session_state.generated_content = None
if "workflow_type" not in st.session_state:
    st.session_state.workflow_type = "LangGraph"  # 預設使用 LangGraph
# API keys are no longer required from the user in the UI
# We will rely on the environment variables set for the VLLM service
st.session_state.api_keys_configured = True 

# --- UI: Sidebar for Configuration ---
with st.sidebar:
    workflow_type = st.radio(
        "工作流程引擎",
        ["LangGraph", "AutoGen"],
        index=0
    )
    
    st.session_state.workflow_type = workflow_type
    
    tavily_api_key = st.text_input(
        "Tavily API Key",
        type="password",
        value=st.session_state.get("tavily_api_key", ""),
    )

    if st.button("儲存", use_container_width=True):
        if tavily_api_key:
            settings.TAVILY_API_KEY = tavily_api_key
            st.session_state.tavily_api_key = tavily_api_key
            st.success("已儲存")
        else:
            st.error("請輸入 API Key")

# --- Main Application ---
st.title("AI Agent 趨勢文案寫手")
st.markdown(f"**當前工作流程:** {st.session_state.workflow_type}")
st.markdown("---")

# --- Step 1: Fetch Trends ---
st.header("步驟 1: 獲取最新趨勢")

col1, col2 = st.columns([1, 1])
with col1:
    if st.button("獲取熱門趨勢", use_container_width=True):
        with st.spinner("正在從 Google Trends 獲取最新數據..."):
            try:
                trend_fetcher = TrendFetcher()
                st.session_state.trends = trend_fetcher.get_aggregated_trends(force_refresh=True)
                if st.session_state.trends:
                    st.success(f"成功獲取 {len(st.session_state.trends)} 條熱門趨勢！")
                else:
                    st.error("無法獲取趨勢。請檢查您的網路連線。")
            except Exception as e:
                st.error(f"獲取趨勢時發生錯誤: {e}")

with col2:
    if st.button("清除快取", use_container_width=True):
        st.session_state.trends = []
        st.session_state.selected_topic = None
        st.session_state.generated_content = None
        st.success("快取已清除！")

# --- Step 2: Display and Select Topics ---
if st.session_state.trends:
    st.header("步驟 2: 瀏覽熱門趨勢")
    
    # Display trends in an expandable format
    st.subheader("今日熱搜排行榜")
    
    for i, trend in enumerate(st.session_state.trends, 1):
        with st.expander(f"#{i} {trend['title']}", expanded=False):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                if trend.get('picture'):
                    st.image(trend['picture'], width=200, caption=f"圖片來源: {trend.get('picture_source', '')}")
                    
                st.markdown(f"**搜尋量:** {trend.get('approx_traffic', 'N/A')}")
                st.markdown(f"**發布時間:** {trend.get('pub_date', 'N/A')}")
                st.markdown(f"**來源:** {trend['source']}")
                if trend.get('url'):
                    st.markdown(f"**[查看完整趨勢]({trend['url']})**")
                    
            with col2:
                if trend.get('description'):
                    st.markdown(f"**描述:** {trend['description']}")
                
                # Display related news items with URL info for LangGraph
                if trend.get('news_items'):
                    st.markdown("**📰 相關新聞:**")
                    for j, news in enumerate(trend['news_items'][:3], 1):  # 只顯示前3則新聞
                        news_col1, news_col2 = st.columns([1, 3])
                        with news_col1:
                            if news.get('picture'):
                                st.image(news['picture'], width=100)
                        with news_col2:
                            if news.get('url'):
                                st.markdown(f"**[{news['title']}]({news['url']})**")
                                # 為 LangGraph 工作流程顯示URL信息
                                if st.session_state.workflow_type == "LangGraph":
                                    st.caption(f"🔗 URL: {news['url']}")
                            else:
                                st.markdown(f"**{news['title']}**")
                            if news.get('source'):
                                st.caption(f"來源: {news['source']}")
                            if news.get('snippet'):
                                st.caption(news['snippet'])
                
                # 為 LangGraph 顯示可用的URL數量
                if st.session_state.workflow_type == "LangGraph" and trend.get('news_items'):
                    url_count = len([news for news in trend['news_items'] if news.get('url')])
                    st.info(f"🔗 此趨勢有 {url_count} 個可分析的新聞URL")
            
            # Selection button for each trend
            if st.button(f"選擇 '{trend['title']}' 作為創作主題", key=f"select_{i}"):
                st.session_state.selected_topic = trend
                st.success(f"已選擇 '{trend['title']}' 作為創作主題！")
                st.rerun()
    
    st.markdown("---")
    
    # Quick selection dropdown (keep the original functionality)
    st.subheader("⚡ 快速選擇")
    topic_titles = [trend["title"] for trend in st.session_state.trends]
    selected_title = st.selectbox(
        "或使用下拉選單快速選擇：",
        options=["請選擇一個主題..."] + topic_titles,
        index=0,
        help="從下拉選單中快速選擇一個主題。"
    )

    if selected_title and selected_title != "請選擇一個主題...":
        st.session_state.selected_topic = next(
            (trend for trend in st.session_state.trends if trend["title"] == selected_title), None
        )

# --- Display Selected Topic ---
if st.session_state.selected_topic:
    st.success(f"已選擇主題: **{st.session_state.selected_topic['title']}**")
    
    with st.expander("查看選中主題的詳細資訊", expanded=True):
        col1, col2 = st.columns([1, 2])
        
        with col1:
            if st.session_state.selected_topic.get('picture'):
                st.image(
                    st.session_state.selected_topic['picture'], 
                    caption=f"圖片來源: {st.session_state.selected_topic.get('picture_source', '')}"
                )
            
            st.markdown(f"**搜尋量:** {st.session_state.selected_topic.get('approx_traffic', 'N/A')}")
            st.markdown(f"**發布時間:** {st.session_state.selected_topic.get('pub_date', 'N/A')}")
            st.markdown(f"**來源:** {st.session_state.selected_topic['source']}")
            
            # 為 LangGraph 工作流程顯示URL統計
            if st.session_state.workflow_type == "LangGraph":
                news_items = st.session_state.selected_topic.get('news_items', [])
                available_urls = [news['url'] for news in news_items if news.get('url')]
                st.markdown(f"**可分析URL數:** {len(available_urls)}")
                
        with col2:
            if st.session_state.selected_topic.get('description'):
                st.markdown(f"**描述:** {st.session_state.selected_topic['description']}")
            
            # 顯示將被處理的URL（僅LangGraph）
            if st.session_state.workflow_type == "LangGraph":
                news_items = st.session_state.selected_topic.get('news_items', [])
                available_urls = [news['url'] for news in news_items if news.get('url')][:3]  # 取前3個
                if available_urls:
                    st.markdown("**🔗 將被分析的URL:**")
                    for i, url in enumerate(available_urls, 1):
                        st.markdown(f"{i}. `{url}`")
                else:
                    st.warning("⚠️ 此趨勢沒有可分析的URL，將使用通用研究方式")
            
            # Display all related news items for selected topic
            if st.session_state.selected_topic.get('news_items'):
                st.markdown("**相關新聞報導:**")
                for j, news in enumerate(st.session_state.selected_topic['news_items'], 1):
                    with st.container():
                        news_col1, news_col2 = st.columns([1, 4])
                        with news_col1:
                            if news.get('picture'):
                                st.image(news['picture'], width=80)
                        with news_col2:
                            if news.get('url'):
                                st.markdown(f"**{j}. [{news['title']}]({news['url']})**")
                            else:
                                st.markdown(f"**{j}. {news['title']}**")
                            if news.get('source'):
                                st.caption(f"{news['source']}")
                            if news.get('snippet'):
                                st.caption(f"{news['snippet']}")
                        st.divider()


# --- Step 3: Generate Content ---
if st.session_state.selected_topic:
    st.header("步驟 3: 生成內容")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown(f"**選中的主題:** {st.session_state.selected_topic['title']}")
        st.markdown(f"**使用的工作流程:** {st.session_state.workflow_type}")
    
    with col2:
        if st.session_state.workflow_type == "LangGraph":
            news_items = st.session_state.selected_topic.get('news_items', [])
            url_count = len([news for news in news_items if news.get('url')])
            st.markdown(f"**可分析的URL數量:** {url_count}")
    
    if not st.session_state.get("tavily_api_key"):
        st.warning("請在側邊欄設定您的 Tavily API 金鑰以生成內容。")
    else:
        if st.button("🚀 開始生成內容", use_container_width=True, type="primary"):
            # 使用進度條
            progress_bar = st.progress(0)
            status_text = st.empty()
            log_container = st.container()
            
            # 進度回調函數
            def progress_callback(message):
                status_text.text(f"⏳ {message}")
                with log_container:
                    st.info(message)
            
            try:
                progress_callback("開始內容生成流程...")
                progress_bar.progress(10)
                
                if st.session_state.workflow_type == "LangGraph":
                    # 使用新的 LangGraph 工作流程
                    topic = st.session_state.selected_topic['title']
                    news_items = st.session_state.selected_topic.get('news_items', [])
                    trend_urls = [news['url'] for news in news_items if news.get('url')][:3]  # 取前3個URL
                    
                    progress_callback(f"使用 LangGraph 工作流程處理 {len(trend_urls)} 個URL...")
                    progress_bar.progress(20)
                    
                    result = run_langgraph_workflow(
                        topic=topic,
                        trend_urls=trend_urls,
                        progress_callback=progress_callback
                    )
                    
                    progress_bar.progress(90)
                    
                    # 處理結果
                    if result and result.get('video_script') and result.get('social_media'):
                        st.session_state.generated_content = {
                            'video_script': result['video_script'],
                            'social_media': result['social_media'],
                            'summary': result.get('summary', ''),
                            'workflow_info': {
                                'type': 'LangGraph',
                                'processed_urls': result.get('processed_urls', []),
                                'scraped_data_count': result.get('scraped_data_count', 0)
                            }
                        }
                        progress_bar.progress(100)
                        status_text.text("✅ 內容生成完成！")
                        st.success("🎉 內容生成成功！")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ LangGraph 工作流程執行失敗，請檢查日誌。")
                
                else:
                    # 使用原始的 AutoGen 工作流程
                    progress_callback("使用 AutoGen 工作流程...")
                    progress_bar.progress(20)
                    
                    raw_content = run_workflow(
                        topic=st.session_state.selected_topic['title'], 
                        progress_callback=progress_callback,
                        selected_topic_data=st.session_state.selected_topic
                    )
                    
                    progress_bar.progress(70)
                    
                    if raw_content and raw_content.get('video_script') and raw_content.get('social_media'):
                        # Format the content before storing it
                        video_script = ContentFormatter.format_video_script(
                            topic=st.session_state.selected_topic['title'],
                            script_content=raw_content['video_script'],
                            source=st.session_state.selected_topic['source']
                        )
                        social_media = ContentFormatter.format_social_media(
                            topic=st.session_state.selected_topic['title'],
                            social_content=raw_content['social_media'],
                            source=st.session_state.selected_topic['source']
                        )
                        
                        st.session_state.generated_content = {
                            'video_script': video_script,
                            'social_media': social_media,
                            'workflow_info': {
                                'type': 'AutoGen'
                            }
                        }
                        progress_bar.progress(100)
                        status_text.text("✅ 內容生成完成！")
                        st.success("🎉 AI Agents 協作完成！")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ AutoGen 工作流程執行失敗，請檢查設定。")
                    
            except Exception as e:
                st.error(f"❌ 生成內容時發生錯誤: {e}")
                logging.error(f"Content generation error: {e}", exc_info=True)
                
                # 詳細錯誤資訊供調試
                with st.expander("🔍 詳細錯誤資訊", expanded=False):
                    import traceback
                    st.code(traceback.format_exc())
                    
            finally:
                progress_bar.empty()
                status_text.empty()
# --- Step 4: Display and Download Content ---
if st.session_state.get('generated_content'):
    st.header("步驟 4: 查看與下載您的內容")
    
    # 工作流程信息
    workflow_info = st.session_state.generated_content.get('workflow_info', {})
    workflow_type = workflow_info.get('type', 'Unknown')
    
    st.info(f"**使用的工作流程:** {workflow_type}")
    
    if workflow_type == "LangGraph":
        col1, col2 = st.columns(2)
        with col1:
            st.metric("處理的URL數量", workflow_info.get('scraped_data_count', 0))
        with col2:
            processed_urls = workflow_info.get('processed_urls', [])
            st.metric("分析的網站數量", len(processed_urls))
    
    st.markdown("---")
    
    # Tabs for different content types
    if workflow_type == "LangGraph" and st.session_state.generated_content.get('summary'):
        tab1, tab2, tab3, tab4 = st.tabs(["🎬 影片腳本", "📱 社群媒體", "📋 摘要報告", "💾 匯出"])
    else:
        tab1, tab2, tab4 = st.tabs(["🎬 影片腳本", "📱 社群媒體", "💾 匯出"])
    
    with tab1:
        st.subheader("60秒影片腳本")
        video_script = st.session_state.generated_content.get('video_script', '')
        st.text_area(
            "影片腳本內容",
            value=video_script,
            height=400,
            key="video_script_display"
        )
        
        if st.button("📋 複製影片腳本", key="copy_video"):
            st.write("```")
            st.code(video_script, language="text")
            st.write("```")
    
    with tab2:
        st.subheader("社群媒體內容")
        social_media = st.session_state.generated_content.get('social_media', '')
        st.text_area(
            "社群媒體內容",
            value=social_media,
            height=400,
            key="social_media_display"
        )
        
        if st.button("📋 複製社群媒體內容", key="copy_social"):
            st.write("```")
            st.code(social_media, language="text")
            st.write("```")
    
    # 摘要報告頁籤（僅LangGraph）
    if workflow_type == "LangGraph" and st.session_state.generated_content.get('summary'):
        with tab3:
            st.subheader("內容摘要報告")
            summary = st.session_state.generated_content.get('summary', '')
            st.text_area(
                "摘要內容",
                value=summary,
                height=300,
                key="summary_display"
            )
            
            # 顯示處理的URL
            processed_urls = workflow_info.get('processed_urls', [])
            if processed_urls:
                st.subheader("分析的網站")
                for i, url in enumerate(processed_urls, 1):
                    st.write(f"{i}. {url}")
    
    # 匯出頁籤
    with (tab4 if workflow_type == "LangGraph" and st.session_state.generated_content.get('summary') else tab3):
        st.subheader("匯出內容")
        
        # 準備匯出數據
        export_data = {
            'topic': st.session_state.selected_topic['title'],
            'workflow_type': workflow_type,
            'generation_time': st.session_state.get('generation_time', 'N/A'),
            'video_script': st.session_state.generated_content.get('video_script', ''),
            'social_media': st.session_state.generated_content.get('social_media', ''),
            'summary': st.session_state.generated_content.get('summary', ''),
            'workflow_info': workflow_info
        }
        
        col1, col2 = st.columns(2)
        
        with col1:
            # JSON 匯出
            import json
            json_data = json.dumps(export_data, ensure_ascii=False, indent=2)
            st.download_button(
                "📥 下載 JSON",
                data=json_data,
                file_name=f"content_{st.session_state.selected_topic['title'][:20]}.json",
                mime="application/json"
            )
        
        with col2:
            # 文本匯出
            text_data = f"""主題: {export_data['topic']}
工作流程: {export_data['workflow_type']}

=== 影片腳本 ===
{export_data['video_script']}

=== 社群媒體內容 ===
{export_data['social_media']}

=== 摘要報告 ===
{export_data.get('summary', 'N/A')}
"""
            st.download_button(
                "📥 下載文本",
                data=text_data,
                file_name=f"content_{st.session_state.selected_topic['title'][:20]}.txt",
                mime="text/plain"
            )

else:
    # 如果沒有生成的內容，但有選擇的主題，顯示提示
    if st.session_state.get('selected_topic'):
        st.info("💡 請點擊上方的「生成內容」按鈕開始創作！")

# --- Footer ---
st.markdown("---")
st.markdown("🤖 **AI Agent 趨勢文案寫手 - 增強版** | 支援 AutoGen 和 LangGraph 工作流程")
