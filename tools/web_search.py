import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
from typing import List, Dict, Optional
from tavily import TavilyClient

from config import settings

logging.basicConfig(level=logging.INFO)

class WebSearch:
    """
    A tool for performing web searches using the Tavily API.
    """

    def __init__(self):
        """
        Initializes the web search tool with Tavily client and web scraping capabilities.
        """
        self.tavily_enabled = bool(settings.TAVILY_API_KEY)
        if self.tavily_enabled:
            self.client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        else:
            logging.warning("Tavily API key is not set. Only URL scraping will be available.")
            
        # 設置Web爬取headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.8,en;q=0.6',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    def scrape_url_content(self, url: str) -> Optional[Dict[str, str]]:
        """
        爬取單個URL的內容
        
        Args:
            url (str): 要爬取的URL
            
        Returns:
            Optional[Dict[str, str]]: 包含'title', 'url', 'content'的字典，失敗時返回None
        """
        try:
            logging.info(f"正在爬取URL: {url}")
            
            # 發送HTTP請求
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # 解析HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 提取標題
            title = ""
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text().strip()
            
            # 嘗試從各種標籤提取正文內容
            content_text = ""
            
            # 方法1: 嘗試article標籤
            article = soup.find('article')
            if article:
                content_text = article.get_text(strip=True, separator=' ')
            
            # 方法2: 嘗試常見的內容類名
            if not content_text:
                for class_name in ['content', 'main-content', 'article-content', 'post-content', 'entry-content']:
                    content_div = soup.find('div', class_=lambda x: x and class_name in x.lower())
                    if content_div:
                        content_text = content_div.get_text(strip=True, separator=' ')
                        break
            
            # 方法3: 嘗試main標籤
            if not content_text:
                main = soup.find('main')
                if main:
                    content_text = main.get_text(strip=True, separator=' ')
            
            # 方法4: 如果仍然沒有內容，取body內容但要移除常見的干擾元素
            if not content_text:
                # 移除常見的非內容元素
                for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                    element.decompose()
                
                body = soup.find('body')
                if body:
                    content_text = body.get_text(strip=True, separator=' ')
            
            # 限制內容長度，取前2000個字符
            if content_text:
                content_text = content_text[:2000]
            
            if not content_text:
                content_text = "無法提取內容"
                
            logging.info(f"成功爬取URL: {url}, 內容長度: {len(content_text)}")
            
            return {
                'title': title or '無標題',
                'url': url,
                'content': content_text
            }
            
        except requests.RequestException as e:
            logging.error(f"請求URL失敗 {url}: {e}")
            return None
        except Exception as e:
            logging.error(f"爬取URL內容時發生錯誤 {url}: {e}")
            return None
    
    def scrape_multiple_urls(self, urls: List[str], max_urls: int = 5) -> List[Dict[str, str]]:
        """
        批量爬取多個URL的內容
        
        Args:
            urls (List[str]): URL列表
            max_urls (int): 最大爬取數量
            
        Returns:
            List[Dict[str, str]]: 成功爬取的內容列表
        """
        results = []
        urls_to_scrape = urls[:max_urls]  # 限制數量
        
        for i, url in enumerate(urls_to_scrape, 1):
            logging.info(f"爬取進度: {i}/{len(urls_to_scrape)}")
            
            content = self.scrape_url_content(url)
            if content:
                results.append(content)
            
            # 添加小延遲防止被封禁
            if i < len(urls_to_scrape):
                time.sleep(1)
        
        logging.info(f"批量爬取完成，成功獲取 {len(results)}/{len(urls_to_scrape)} 個網頁內容")
        return results

    def search(self, query: str, max_results: int = 5, trend_urls: List[str] = None) -> List[Dict]:
        """
        執行網絡搜索，結合Tavily搜索和趨勢新聞 URL 爬取

        Args:
            query (str): 搜索查詢關鍵詞
            max_results (int): Tavily搜索結果的最大數量
            trend_urls (List[str], optional): 從趨勢數據獲取的相關新聞URL列表

        Returns:
            List[Dict]: 搜索結果列表，每個結果包含'title', 'url', 'content'
        """
        all_results = []
        
        # 優先使用趨勢新聞 URL爬取最新內容
        if trend_urls:
            logging.info(f"正在爬取 {len(trend_urls)} 個趨勢相關新聞URL...")
            trend_results = self.scrape_multiple_urls(trend_urls, max_urls=3)  # 限制爬取3個趨勢 URL
            all_results.extend(trend_results)
            
        # 如果啟用了Tavily，作為補充搜索
        if self.tavily_enabled:
            try:
                logging.info(f"使用Tavily進行補充搜索: '{query}'")
                response = self.client.search(query=query, search_depth="advanced", max_results=max_results)
                
                tavily_results = [
                    {
                        "title": res.get("title", "No Title"),
                        "url": res.get("url"),
                        "content": res.get("content", "No Content"),
                        "source": "Tavily"
                    }
                    for res in response.get('results', [])
                ]
                
                all_results.extend(tavily_results)
                logging.info(f"Tavily搜索獲取 {len(tavily_results)} 個結果")
                
            except Exception as e:
                logging.error(f"Tavily搜索發生錯誤: {e}")
        else:
            logging.info("未配置Tavily API key，僅使用URL爬取")
        
        # 給趨勢新聞標記來源
        for result in all_results:
            if 'source' not in result:
                result['source'] = 'Trending News'
        
        logging.info(f"搜索完成，共獲取 {len(all_results)} 個結果")
        return all_results

if __name__ == '__main__':
    # Make sure to have a .env file with TAVILY_API_KEY for this to work
    search_tool = WebSearch()
    results = search_tool.search("What are the latest AI trends in 2024?")
    if results:
        print(f"Search Results:")
        for result in results:
            print(f"- Title: {result['title']}")
            print(f"  URL: {result['url']}")
            print(f"  Content: {result['content'][:150]}...")
            print("-" * 20)
    else:
        print("No search results found or an error occurred.")
