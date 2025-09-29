import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from unittest.mock import patch, MagicMock

from agents.workflow import run_workflow

class TestAgentWorkflow(unittest.TestCase):

    @patch('agents.workflow.WebSearch')
    @patch('agents.workflow.UserProxyAgent')
    @patch('agents.workflow.AssistantAgent')
    @patch('agents.workflow.GroupChatManager')
    def test_run_workflow(self, MockManager, MockAssistantAgent, MockUserProxyAgent, MockWebSearch):
        """Test the agent workflow orchestration."""
        
        # Create separate mocks for each agent to avoid duplication warnings
        mock_researcher = MagicMock(name="Researcher")
        mock_script_writer = MagicMock(name="ScriptWriter")
        mock_social_writer = MagicMock(name="SocialWriter")
        MockAssistantAgent.side_effect = [mock_researcher, mock_script_writer, mock_social_writer]

        # Mock the final message from the agent interaction
        mock_user_proxy_instance = MockUserProxyAgent.return_value
        mock_user_proxy_instance.last_message.return_value = {
            "content": """
            FINAL_CONTENT
            ---VIDEO_SCRIPT_START---
            This is the video script.
            ---VIDEO_SCRIPT_END---
            ---SOCIAL_MEDIA_START---
            This is the social media post.
            ---SOCIAL_MEDIA_END---
            """
        }

        with patch('agents.workflow.settings') as mock_settings:
            mock_settings.OPENAI_MODEL_NAME = "test-model"
            mock_settings.OPENAI_API_KEY = "test-key"
            mock_settings.OPENAI_API_BASE = "http://localhost:5003/v1"

            result = run_workflow("test topic")

        self.assertIn("video_script", result)
        self.assertIn("social_media", result)
        self.assertEqual(result["video_script"], "This is the video script.")
        self.assertEqual(result["social_media"], "This is the social media post.")
        
        # Check if the chat was initiated
        mock_user_proxy_instance.initiate_chat.assert_called_once()


if __name__ == '__main__':
    unittest.main()
