import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import xml.etree.ElementTree as ET

import requests

from config import settings

logging.basicConfig(level=logging.INFO)

class TrendFetcher:
    """
    Fetches, aggregates, and ranks trending topics by scraping Google Trends.
    """

    def __init__(self, cache_duration_hours: int = 1):
        """
        Initializes the TrendFetcher with cache settings.
        """
        self.cache_duration = timedelta(hours=cache_duration_hours)
        self.last_fetch_time: Optional[datetime] = None
        self.cached_trends: List[Dict] = []
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def get_google_trends(self) -> List[Dict]:
        """
        Fetches daily trending searches from Google Trends RSS for Taiwan.

        Returns:
            List[Dict]: A list of trending search terms with comprehensive metadata.
                       Returns an empty list on failure.
        """
        url = "https://trends.google.com/trending/rss?geo=TW"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()  # Raise an exception for bad status codes
            
            # 解析 XML
            root = ET.fromstring(response.content)
            trends = []
            
            # 定義正確的命名空間 - 根據實際 RSS 結構
            namespace = {'ht': 'https://trends.google.com/trending/rss'}
            
            # 找到所有 item 元素
            for item in root.findall('.//item'):
                title = item.find('title').text if item.find('title') is not None else ""
                link = item.find('link').text if item.find('link') is not None else ""
                description = item.find('description').text if item.find('description') is not None else ""
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                
                # 提取 Google Trends 特有的資訊
                approx_traffic = item.find('ht:approx_traffic', namespace)
                traffic = approx_traffic.text if approx_traffic is not None else ""
                
                picture = item.find('ht:picture', namespace)
                picture_url = picture.text if picture is not None else ""
                
                picture_source = item.find('ht:picture_source', namespace)
                pic_source = picture_source.text if picture_source is not None else ""
                
                # 提取新聞項目
                news_items = []
                for news_item in item.findall('ht:news_item', namespace):
                    news_title = news_item.find('ht:news_item_title', namespace)
                    news_url = news_item.find('ht:news_item_url', namespace)
                    news_snippet = news_item.find('ht:news_item_snippet', namespace)
                    news_picture = news_item.find('ht:news_item_picture', namespace)
                    news_source = news_item.find('ht:news_item_source', namespace)
                    
                    if news_title is not None:
                        news_items.append({
                            "title": news_title.text or "",
                            "url": news_url.text if news_url is not None else "",
                            "snippet": news_snippet.text if news_snippet is not None else "",
                            "picture": news_picture.text if news_picture is not None else "",
                            "source": news_source.text if news_source is not None else ""
                        })
                
                if title:  # 只添加有標題的項目
                    trends.append({
                        "title": title,
                        "url": link,
                        "description": description,
                        "pub_date": pub_date,
                        "approx_traffic": traffic,
                        "picture": picture_url,
                        "picture_source": pic_source,
                        "news_items": news_items
                    })
            
            if not trends:
                logging.warning("Could not find trend items in RSS feed.")

            return trends[:10]  # Return top 10
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching Google Trends RSS: {e}")
            return []
        except ET.ParseError as e:
            logging.error(f"Error parsing Google Trends RSS XML: {e}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error fetching Google Trends: {e}")
            return []

    def get_aggregated_trends(self, force_refresh: bool = False) -> List[Dict]:
        """
        Aggregates trends from Google, ranks them, and caches the result.

        Args:
            force_refresh (bool): If True, forces a refetch of data, ignoring the cache.

        Returns:
            List[Dict]: A sorted list of top 10 trending topics.
        """
        now = datetime.now()
        if not force_refresh and self.last_fetch_time and (now - self.last_fetch_time < self.cache_duration):
            logging.info("Returning cached trends.")
            return self.cached_trends

        logging.info("Fetching new trends from Google Trends...")
        google_trends = self.get_google_trends()

        all_trends = []

        # Process Google Trends
        if google_trends:
            for i, trend_data in enumerate(google_trends):
                all_trends.append({
                    "title": trend_data["title"],
                    "description": trend_data["description"] or f"Google 熱搜趨勢第 {i+1} 名",
                    "source": "Google Trends",
                    "url": trend_data["url"],
                    "pub_date": trend_data["pub_date"],
                    "approx_traffic": trend_data["approx_traffic"],
                    "picture": trend_data["picture"],
                    "picture_source": trend_data["picture_source"],
                    "news_items": trend_data["news_items"],
                    "score": 100 - i * 5  # Higher score for higher rank
                })

        self.cached_trends = all_trends[:10]
        self.last_fetch_time = now
        
        logging.info(f"Fetched and cached {len(self.cached_trends)} unique trends.")
        return self.cached_trends

