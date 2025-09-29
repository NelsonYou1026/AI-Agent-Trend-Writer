import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from unittest.mock import patch, MagicMock

from tools.web_search import WebSearch

class TestWebSearch(unittest.TestCase):

    @patch('tools.web_search.TavilyClient')
    def test_search_success(self, MockTavilyClient):
        """Test successful web search."""
        mock_instance = MockTavilyClient.return_value
        mock_instance.search.return_value = {
            'results': [
                {'title': 'Result 1', 'url': 'http://example.com/1', 'content': 'Content 1'},
                {'title': 'Result 2', 'url': 'http://example.com/2', 'content': 'Content 2'}
            ]
        }
        
        with patch('tools.web_search.settings') as mock_settings:
            mock_settings.TAVILY_API_KEY = "fake_key"
            search_tool = WebSearch()
            results = search_tool.search("test query")
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['title'], 'Result 1')
        mock_instance.search.assert_called_once_with(query="test query", search_depth="advanced", max_results=5)

    @patch('tools.web_search.TavilyClient')
    def test_search_failure(self, MockTavilyClient):
        """Test failure in web search."""
        mock_instance = MockTavilyClient.return_value
        mock_instance.search.side_effect = Exception("API Error")
        
        with patch('tools.web_search.settings') as mock_settings:
            mock_settings.TAVILY_API_KEY = "fake_key"
            search_tool = WebSearch()
            results = search_tool.search("test query")
            
        self.assertEqual(results, [])

if __name__ == '__main__':
    unittest.main()
