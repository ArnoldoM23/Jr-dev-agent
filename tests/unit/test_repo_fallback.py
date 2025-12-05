import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from jr_dev_agent.utils.load_ticket_metadata import load_ticket_metadata, load_from_text_template

class TestFallbackLogic(unittest.TestCase):
    
    def test_explicit_content_priority(self):
        """Test that explicitly provided content takes precedence over everything"""
        # Arrange
        explicit_content = "Jira_Ticket: EXPLICIT-123\nPaste Template below\n---\nName: explicit_template\n"
        
        # Act
        # No mocking needed for file system as we provide content directly
        result = load_ticket_metadata("ANY-ID", fallback_content=explicit_content)
        
        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result['ticket_id'], "EXPLICIT-123")
        self.assertEqual(result['template_name'], "explicit_template")
        self.assertEqual(result['_fallback_used'], "client_provided_content")

    @patch('jr_dev_agent.utils.load_ticket_metadata.REPO_TEMPLATE_FILE')
    @patch('jr_dev_agent.utils.load_ticket_metadata.FALLBACK_TEMPLATE_FILE')
    def test_repo_file_priority(self, mock_fallback, mock_repo):
        """Test that repo file is used if it exists (via load_from_text_template)"""
        # Arrange
        mock_repo.exists.return_value = True
        mock_repo.read_text.return_value = "Jira_Ticket: REPO-123\nPaste Template below\n---\nName: repo_template\n"
        
        mock_fallback.exists.return_value = True
        mock_fallback.read_text.return_value = "Jira_Ticket: FALLBACK-123\nPaste Template below\n---\nName: fallback_template\n"
        
        # Act
        result = load_from_text_template("ANY-ID")
        
        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result['ticket_id'], "REPO-123")
        self.assertEqual(result['template_name'], "repo_template")
        mock_fallback.read_text.assert_not_called()

if __name__ == '__main__':
    unittest.main()
