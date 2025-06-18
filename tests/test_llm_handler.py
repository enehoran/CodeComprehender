import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the parent directory to sys.path to import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import llm_handler

class TestLLMHandler(unittest.TestCase):
    
    def test_configure_llm(self):
        """Test that configure_llm correctly configures the LLM client."""
        with patch('google.genai.Client') as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance
            
            client = llm_handler.configure_llm("fake_api_key")
            
            mock_client.assert_called_once_with(api_key="fake_api_key")
            self.assertEqual(client, mock_instance)
    
    def test_get_llm_comment_no_client(self):
        """Test that get_llm_comment returns a placeholder when no client is provided."""
        result = llm_handler.get_llm_comment(None, "code", "method")
        self.assertIn("LLM not configured", result)
        self.assertIn("method", result)
    
    @patch('google.genai.Client')
    def test_get_llm_comment_with_client(self, mock_client):
        """Test that get_llm_comment correctly calls the LLM API and processes the response."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.text = "This is a test comment"
        
        # Setup mock client
        mock_instance = MagicMock()
        mock_instance.models.generate_content.return_value = mock_response
        
        result = llm_handler.get_llm_comment(mock_instance, "def test():", "method", num_retries=1)
        
        # Verify the result is properly formatted
        self.assertIn("/**", result)
        self.assertIn("This is a test comment", result)
        self.assertIn("*/", result)
        
        # Verify the client was called correctly
        mock_instance.models.generate_content.assert_called_once()
    
    @patch('llm_handler.get_llm_comment')
    def test_generate_comments_for_structure(self, mock_get_llm_comment):
        """Test that generate_comments_for_structure correctly processes a parsed structure."""
        # Setup mock response
        mock_get_llm_comment.return_value = "/** Test comment */"
        
        # Create a test parsed structure
        parsed_structure = {
            'file_path': 'test.java',
            'classes': [
                {
                    'name': 'TestClass',
                    'code_snippet': 'class TestClass {}',
                    'methods': [
                        {
                            'name': 'testMethod',
                            'code_snippet': 'void testMethod() {}'
                        }
                    ]
                }
            ]
        }
        
        client = MagicMock()
        result = llm_handler.generate_comments_for_structure(parsed_structure, client)
        
        # Verify get_llm_comment was called for both class and method
        self.assertEqual(mock_get_llm_comment.call_count, 2)
        
        # Verify comments were added to the structure
        self.assertEqual(result['classes'][0]['comment'], "/** Test comment */")
        self.assertEqual(result['classes'][0]['methods'][0]['comment'], "/** Test comment */")

if __name__ == '__main__':
    unittest.main()