"""
Web Scraper Tools for Agent-based scraping
提供網頁獲取和程式碼執行的工具函數
"""

import requests
import subprocess
import sys
import tempfile
import os
import json
import logging
from typing import Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import time

logging.basicConfig(level=logging.INFO)


def fetch_webpage(url: str, timeout: int = 30) -> str:
    """
    獲取網頁的原始 HTML 內容
    
    Args:
        url (str): 目標網頁 URL
        timeout (int): 請求超時時間（秒）
        
    Returns:
        str: 網頁的 HTML 內容，如果失敗則返回錯誤訊息
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }
    
    try:
        logging.info(f"正在獲取網頁: {url}")
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        # 嘗試解碼內容
        if response.encoding is None:
            response.encoding = 'utf-8'
            
        html_content = response.text
        logging.info(f"成功獲取網頁，內容長度: {len(html_content)} 字符")
        
        return html_content
        
    except requests.exceptions.Timeout:
        error_msg = f"請求超時: {url} (超過 {timeout} 秒)"
        logging.error(error_msg)
        return f"ERROR: {error_msg}"
        
    except requests.exceptions.ConnectionError:
        error_msg = f"連接失敗: {url}"
        logging.error(error_msg)
        return f"ERROR: {error_msg}"
        
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP 錯誤 {response.status_code}: {url}"
        logging.error(error_msg)
        return f"ERROR: {error_msg}"
        
    except Exception as e:
        error_msg = f"獲取網頁時發生未知錯誤: {str(e)}"
        logging.error(error_msg)
        return f"ERROR: {error_msg}"


def execute_python_code(code: str, timeout: int = 60) -> Dict[str, Any]:
    """
    在安全環境中執行 Python 程式碼
    
    Args:
        code (str): 要執行的 Python 程式碼
        timeout (int): 執行超時時間（秒）
        
    Returns:
        Dict[str, Any]: 包含執行結果、輸出、錯誤等信息的字典
    """
    try:
        # 創建臨時檔案來儲存程式碼
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(code)
            temp_file_path = temp_file.name
        
        logging.info(f"執行 Python 程式碼，臨時檔案: {temp_file_path}")
        
        # 執行程式碼
        try:
            result = subprocess.run(
                [sys.executable, temp_file_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.path.dirname(temp_file_path)
            )
            
            # 清理臨時檔案
            os.unlink(temp_file_path)
            
            execution_result = {
                "success": result.returncode == 0,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "execution_time": "completed within timeout"
            }
            
            if result.returncode == 0:
                logging.info("程式碼執行成功")
            else:
                logging.error(f"程式碼執行失敗，返回碼: {result.returncode}")
                logging.error(f"錯誤輸出: {result.stderr}")
            
            return execution_result
            
        except subprocess.TimeoutExpired:
            # 清理臨時檔案
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
            error_msg = f"程式碼執行超時 (超過 {timeout} 秒)"
            logging.error(error_msg)
            return {
                "success": False,
                "return_code": -1,
                "stdout": "",
                "stderr": error_msg,
                "execution_time": f"timeout after {timeout}s"
            }
            
    except Exception as e:
        error_msg = f"執行程式碼時發生錯誤: {str(e)}"
        logging.error(error_msg)
        return {
            "success": False,
            "return_code": -1,
            "stdout": "",
            "stderr": error_msg,
            "execution_time": "failed"
        }


def validate_scraped_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    驗證和標準化爬取的資料
    
    Args:
        data (Dict[str, Any]): 爬取的原始資料
        
    Returns:
        Dict[str, Any]: 驗證後的標準化資料
    """
    standard_template = {
        "url": "",
        "title": "",
        "content": "",
        "publish_date": "",
        "author": "",
        "summary": "",
        "keywords": [],
        "metadata": {
            "word_count": 0,
            "reading_time": "",
            "source_domain": ""
        }
    }
    
    # 合併原始資料和標準模板
    validated_data = standard_template.copy()
    if isinstance(data, dict):
        for key, value in data.items():
            if key in validated_data:
                validated_data[key] = value
            elif key in validated_data.get("metadata", {}):
                validated_data["metadata"][key] = value
    
    # 基本驗證和處理
    if validated_data.get("content"):
        content = str(validated_data["content"])
        word_count = len(content.split())
        validated_data["metadata"]["word_count"] = word_count
        
        # 估算閱讀時間 (假設每分鐘 200 字)
        reading_time_minutes = max(1, word_count // 200)
        validated_data["metadata"]["reading_time"] = f"{reading_time_minutes} 分鐘"
    
    # 提取來源網域
    if validated_data.get("url"):
        try:
            from urllib.parse import urlparse
            parsed_url = urlparse(validated_data["url"])
            validated_data["metadata"]["source_domain"] = parsed_url.netloc
        except:
            pass
    
    return validated_data


def generate_scraping_template(url: str, html_preview: str) -> str:
    """
    根據網頁預覽生成爬蟲程式碼模板
    
    Args:
        url (str): 目標 URL
        html_preview (str): HTML 內容預覽
        
    Returns:
        str: 爬蟲程式碼模板
    """
    template = f'''
import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from urllib.parse import urlparse

def scrape_webpage():
    """爬取網頁內容"""
    url = "{url}"
    domain = urlparse(url).netloc
    headers = {{
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # TODO: 根據網頁結構調整以下選擇器
        
        # 標題提取 (常見的標題標籤)
        title = ""
        for selector in ['h1', 'title', '.title', '.headline', '[class*="title"]']:
            title_elem = soup.select_one(selector)
            if title_elem and title_elem.get_text().strip():
                title = title_elem.get_text().strip()
                break
        
        # 內容提取 (常見的內容標籤)
        content = ""
        for selector in ['.content', '.article-body', '.post-content', 'article', '.entry-content']:
            content_elem = soup.select_one(selector)
            if content_elem:
                # 移除腳本和樣式
                for script in content_elem(["script", "style"]):
                    script.decompose()
                content = content_elem.get_text().strip()
                break
        
        # 如果沒找到特定內容區域，嘗試 p 標籤
        if not content:
            paragraphs = soup.find_all('p')
            if paragraphs:
                content = ' '.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
        
        # 發布時間提取
        publish_date = ""
        for selector in ['time', '.date', '.publish-date', '[datetime]', '.timestamp']:
            date_elem = soup.select_one(selector)
            if date_elem:
                publish_date = date_elem.get_text().strip() or date_elem.get('datetime', '')
                break
        
        # 作者提取
        author = ""
        for selector in ['.author', '.by-author', '.writer', '[rel="author"]']:
            author_elem = soup.select_one(selector)
            if author_elem:
                author = author_elem.get_text().strip()
                break
        
        # 關鍵字提取 (從 meta 標籤或內容中)
        keywords = []
        meta_keywords = soup.find('meta', {{'name': 'keywords'}})
        if meta_keywords and meta_keywords.get('content'):
            keywords = [k.strip() for k in meta_keywords.get('content').split(',')]
        
        # 生成摘要 (取前200字)
        summary = content[:200] + "..." if len(content) > 200 else content
        
        result = {{
            "url": url,
            "title": title,
            "content": content,
            "publish_date": publish_date,
            "author": author,
            "summary": summary,
            "keywords": keywords,
            "metadata": {{
                "word_count": len(content.split()) if content else 0,
                "reading_time": f"{{max(1, len(content.split()) // 200)}} 分鐘" if content else "0 分鐘",
                "source_domain": domain
            }}
        }}
        
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return result
        
    except Exception as e:
        error_result = {{
            "url": url,
            "error": f"爬取失敗: {{str(e)}}",
            "title": "",
            "content": "",
            "publish_date": "",
            "author": "",
            "summary": "",
            "keywords": [],
            "metadata": {{"word_count": 0, "reading_time": "0 分鐘", "source_domain": ""}}
        }}
        print(json.dumps(error_result, ensure_ascii=False, indent=2))
        return error_result

if __name__ == "__main__":
    scrape_webpage()
'''
    
    return template


if __name__ == "__main__":
    # 測試程式碼
    test_url = "https://example.com"
    html = fetch_webpage(test_url)
    print("HTML Preview:", html[:500])
    
    test_code = '''
print("Hello from executed code!")
import json
result = {"test": "success", "message": "Code execution works!"}
print(json.dumps(result, indent=2))
'''
    
    execution_result = execute_python_code(test_code)
    print("Execution Result:", execution_result)