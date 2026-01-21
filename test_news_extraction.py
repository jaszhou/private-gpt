import unittest
from unittest.mock import patch, MagicMock
from news_lambda_function import fetch_html, extract_article_with_bedrock, scrape_article_content

class TestNewsExtraction(unittest.TestCase):
    
    @patch('news_lambda_function.requests.get')
    def test_fetch_html(self, mock_get):
        """Test HTML fetching from URL"""
        mock_response = MagicMock()
        mock_response.text = "<html>test content</html>"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = fetch_html("http://test.com")
        self.assertEqual(result, "<html>test content</html>")
    
    @patch('news_lambda_function.boto3.client')
    def test_extract_article_with_bedrock(self, mock_bedrock):
        """Test article extraction using Bedrock"""
        mock_client = MagicMock()
        mock_bedrock.return_value = mock_client
        mock_client.invoke_model.return_value = {
            "body": MagicMock(read=lambda: json.dumps({
                "content": [{"text": "extracted article text"}]
            }).encode('utf-8'))
        }
        
        result = extract_article_with_bedrock("<html>test</html>")
        self.assertEqual(result, "extracted article text")
    
    @patch('news_lambda_function.fetch_html')
    @patch('news_lambda_function.extract_article_with_bedrock')
    def test_scrape_article_content(self, mock_extract, mock_fetch):
        """Test full article content scraping"""
        mock_fetch.return_value = "<html>test</html>"
        mock_extract.return_value = "extracted article text"
        
        result = scrape_article_content("http://test.com/article")
        self.assertEqual(result, "extracted article text")

if __name__ == '__main__':
    unittest.main()