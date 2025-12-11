import unittest
from unittest.mock import patch, MagicMock
from jr_dev_agent.utils.load_ticket_metadata import load_from_text_template

class TestManualFallback(unittest.TestCase):
    
    @patch('jr_dev_agent.utils.load_ticket_metadata.REPO_TEMPLATE_FILE')
    @patch('jr_dev_agent.utils.load_ticket_metadata.FALLBACK_TEMPLATE_FILE')
    def test_success_parsing(self, mock_fallback_file, mock_repo_file):
        # Arrange
        sample_content = """Jira_Ticket: CEPG-67890

Paste Template below
------------------------------------------------------------------------------------------------------
Name: feature_schema_change
Description: |
  Update schema.
Prompt_Text: |
  You are a dev.
Reference_Files:
  - "src/file1.ts"
"""
        # Mock repo file to not exist, fallback file to exist with content
        mock_repo_file.exists.return_value = False
        mock_fallback_file.exists.return_value = True
        mock_fallback_file.read_text.return_value = sample_content
        
        # Act
        result = load_from_text_template("CEPG-REQUESTED")
        
        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result['ticket_id'], "CEPG-67890")
        self.assertEqual(result['template_name'], "feature_schema_change")
        self.assertEqual(result['files_affected'], ["src/file1.ts"])
        self.assertEqual(result['_fallback_used'], "text_template")

    @patch('jr_dev_agent.utils.load_ticket_metadata.REPO_TEMPLATE_FILE')
    @patch('jr_dev_agent.utils.load_ticket_metadata.FALLBACK_TEMPLATE_FILE')
    def test_file_not_exists(self, mock_fallback_file, mock_repo_file):
        mock_repo_file.exists.return_value = False
        mock_fallback_file.exists.return_value = False
        result = load_from_text_template("CEPG-123")
        self.assertIsNone(result)

    @patch('jr_dev_agent.utils.load_ticket_metadata.REPO_TEMPLATE_FILE')
    @patch('jr_dev_agent.utils.load_ticket_metadata.FALLBACK_TEMPLATE_FILE')
    def test_empty_file(self, mock_fallback_file, mock_repo_file):
        mock_repo_file.exists.return_value = False
        mock_fallback_file.exists.return_value = True
        mock_fallback_file.read_text.return_value = "   "
        result = load_from_text_template("CEPG-123")
        self.assertIsNone(result)

    @patch('jr_dev_agent.utils.load_ticket_metadata.REPO_TEMPLATE_FILE')
    @patch('jr_dev_agent.utils.load_ticket_metadata.FALLBACK_TEMPLATE_FILE')
    def test_case_insensitivity(self, mock_fallback_file, mock_repo_file):
        # Arrange - Weird casing
        sample_content = """JIRA_TICKET: CEPG-999

Paste Template below
-------------------
name: bugfix
reference_files:
  - "src/bug.ts"
"""
        mock_repo_file.exists.return_value = False
        mock_fallback_file.exists.return_value = True
        mock_fallback_file.read_text.return_value = sample_content
        
        # Act
        result = load_from_text_template("CEPG-999")
        
        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result['template_name'], "bugfix")
        self.assertEqual(result['files_affected'], ["src/bug.ts"])

if __name__ == '__main__':
    unittest.main()

