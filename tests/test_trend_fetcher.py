import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

from tools.trend_fetcher import TrendFetcher

class TestTrendFetcher(unittest.TestCase):

    @patch('tools.trend_fetcher.TrendReq')
    def test_get_google_trends_success(self, MockTrendReq):
        """Test successful fetching of Google Trends."""
        mock_instance = MockTrendReq.return_value
        mock_df = pd.DataFrame({'title': ['Trend 1', 'Trend 2']})
        mock_instance.trending_searches.return_value = mock_df
        
        fetcher = TrendFetcher()
        result = fetcher.get_google_trends()
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        mock_instance.trending_searches.assert_called_once_with(pn='taiwan')

    @patch('tools.trend_fetcher.TrendReq')
    def test_get_google_trends_failure(self, MockTrendReq):
        """Test failure in fetching Google Trends."""
        mock_instance = MockTrendReq.return_value
        mock_instance.trending_searches.side_effect = Exception("API Error")
        
        fetcher = TrendFetcher()
        result = fetcher.get_google_trends()
        
        self.assertTrue(result.empty)

    @patch('tools.trend_fetcher.NewsApiClient')
    def test_get_news_trends_success(self, MockNewsApiClient):
        """Test successful fetching of NewsAPI trends."""
        mock_instance = MockNewsApiClient.return_value
        mock_instance.get_top_headlines.return_value = {
            'articles': [{'title': 'News 1'}, {'title': 'News 2'}]
        }
        
        fetcher = TrendFetcher()
        # This will fail if NEWS_API_KEY is not set, so we mock settings
        with patch('tools.trend_fetcher.settings') as mock_settings:
            mock_settings.NEWS_API_KEY = "fake_key"
            result = fetcher.get_news_trends()
        
        self.assertEqual(len(result), 2)
        mock_instance.get_top_headlines.assert_called_once()

    @patch('tools.trend_fetcher.NewsApiClient')
    def test_get_news_trends_failure(self, MockNewsApiClient):
        """Test failure in fetching NewsAPI trends."""
        mock_instance = MockNewsApiClient.return_value
        mock_instance.get_top_headlines.side_effect = Exception("API Error")
        
        fetcher = TrendFetcher()
        with patch('tools.trend_fetcher.settings') as mock_settings:
            mock_settings.NEWS_API_KEY = "fake_key"
            result = fetcher.get_news_trends()
        
        self.assertEqual(result, [])

if __name__ == '__main__':
    unittest.main()
