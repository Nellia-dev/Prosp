import unittest
from unittest.mock import patch, MagicMock
import os
import json # Added import for json.dumps

# Adjust imports based on your project structure if models are not directly accessible
# This assumes data_models can be found relative to the execution path of the tests
# or that PYTHONPATH is set up accordingly.
try:
    from data_models.content_marketing_models import ContentMarketingInput, ContentMarketingOutput, BlogIdea, SocialMediaPost
    from agents.content_marketing_agent import ContentMarketingAgent
    from core_logic.llm_client import LLMProvider, LLMClientFactory # For potential setup
except ImportError:
    # This block is for local testing if the script is run directly and paths are an issue.
    # It's a fallback and ideally, your test environment should handle module resolution.
    import sys
    # Assuming the script is in tests/agents/ and root is two levels up
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
    from data_models.content_marketing_models import ContentMarketingInput, ContentMarketingOutput, BlogIdea, SocialMediaPost
    from agents.content_marketing_agent import ContentMarketingAgent
    from core_logic.llm_client import LLMProvider, LLMClientFactory


# Ensure API keys are available if you're making live LLM calls in tests.
# It's better to mock LLM calls in unit tests.
# For this example, we'll assume a live call is made by the agent as per its current design,
# but we'll mock `generate_llm_response` to control output and avoid actual API calls.

class TestContentMarketingAgent(unittest.TestCase):

    def setUp(self):
        # You might need to set up environment variables for LLMClientFactory
        # if it relies on them and they are not globally set in your test environment.
        os.environ["GEMINI_API_KEY"] = "dummy_test_key" # Set a dummy key for initialization
        # However, we will mock the actual LLM call.
        self.agent = ContentMarketingAgent(llm_provider=LLMProvider.GEMINI) # Or any provider

    @patch.object(ContentMarketingAgent, 'generate_llm_response')
    def test_process_valid_input_returns_structured_output(self, mock_generate_llm_response):
        # Define a realistic JSON string that the LLM might return, matching the agent's prompt structure
        mock_llm_json_output = {
            "blog_post_ideas": [
                {
                    "title": "Mock Blog Title 1: Urban Jungle",
                    "outline": ["Point A", "Point B", "Point C"],
                    "draft_intro_paragraph": "This is a mock intro for the urban jungle blog."
                },
                {
                    "title": "Mock Blog Title 2: Small Space Greenery",
                    "outline": ["Tip 1", "Tip 2", "Tip 3"]
                }
            ],
            "social_media_posts": [
                {
                    "platform": "LinkedIn",
                    "post_text": "Mock LinkedIn post about sustainable gardening...",
                    "hashtags": ["#sustainability", "#urbanfarming"]
                },
                {
                    "platform": "Twitter",
                    "post_text": "Quick tips for city gardeners! #gardeninghacks",
                    "hashtags": ["#urbangarden", "#twittertips"]
                },
                {
                    "platform": "Instagram",
                    "post_text": "Beautiful apartment garden inspiration. Image: lush green plants on a balcony.",
                    "hashtags": ["#instagarden", "#plantlover"]
                }
            ],
            "suggested_seo_keywords": ["urban gardening", "apartment plants", "sustainable practices"],
            "suggested_hashtags": ["#citygardening", "#ecofriendlyhome", "#growyourown"]
        }

        # The agent's parse_llm_json_response expects a string, so convert dict to JSON string
        mock_generate_llm_response.return_value = json.dumps(mock_llm_json_output)

        sample_input = ContentMarketingInput(
            topic="Sustainable Gardening for Urban Dwellers",
            target_audience="City residents with limited space, interested in eco-friendly living.",
            content_goals=["Increase website traffic", "Build community engagement"]
        )

        # Use execute() as it includes the full processing logic including metrics
        result = self.agent.execute(sample_input)

        self.assertIsInstance(result, ContentMarketingOutput)
        self.assertEqual(result.input_topic, sample_input.topic)

        # Check blog post ideas
        self.assertTrue(len(result.blog_post_ideas) >= 1) # We expect at least one idea
        for idea in result.blog_post_ideas:
            self.assertIsInstance(idea, BlogIdea)
            self.assertIsInstance(idea.title, str)
            self.assertIsInstance(idea.outline, list)
            if idea.draft_intro_paragraph: # It's optional
                self.assertIsInstance(idea.draft_intro_paragraph, str)

        # Check if at least one blog idea has a draft intro (as per mock)
        self.assertTrue(any(idea.draft_intro_paragraph for idea in result.blog_post_ideas))

        # Check social media posts
        self.assertTrue(len(result.social_media_posts) >= 1) # We expect at least one post
        for post in result.social_media_posts:
            self.assertIsInstance(post, SocialMediaPost)
            self.assertIsInstance(post.platform, str)
            self.assertIsInstance(post.post_text, str)
            self.assertIsInstance(post.hashtags, list)

        # Check SEO keywords
        self.assertTrue(len(result.suggested_seo_keywords) >= 1)
        for keyword in result.suggested_seo_keywords:
            self.assertIsInstance(keyword, str)

        # Check general hashtags
        self.assertTrue(len(result.suggested_hashtags) >= 1)
        for hashtag in result.suggested_hashtags:
            self.assertIsInstance(hashtag, str)

        self.assertEqual(result.generation_summary, "Content ideas generated successfully.")
        mock_generate_llm_response.assert_called_once() # Ensure LLM was called

    @patch.object(ContentMarketingAgent, 'generate_llm_response')
    def test_process_llm_error(self, mock_generate_llm_response):
        mock_generate_llm_response.side_effect = Exception("LLM API Failure")

        sample_input = ContentMarketingInput(
            topic="Test Topic",
            target_audience="Test Audience",
            content_goals=["Test Goal"]
        )

        result = self.agent.execute(sample_input) # execute should catch the error

        self.assertIsInstance(result, ContentMarketingOutput)
        self.assertEqual(result.input_topic, sample_input.topic)
        self.assertTrue("Error during LLM generation: LLM API Failure" in result.generation_summary)
        self.assertEqual(len(result.blog_post_ideas), 0) # No content should be generated
        self.assertEqual(len(result.social_media_posts), 0)

    @patch.object(ContentMarketingAgent, 'generate_llm_response')
    def test_process_llm_returns_malformed_json(self, mock_generate_llm_response):
        mock_generate_llm_response.return_value = "This is not valid JSON { " # Malformed JSON

        sample_input = ContentMarketingInput(
            topic="Test Topic JSON",
            target_audience="Test Audience JSON",
            content_goals=["Test Goal JSON"]
        )

        result = self.agent.execute(sample_input)

        self.assertIsInstance(result, ContentMarketingOutput)
        self.assertEqual(result.input_topic, sample_input.topic)
        self.assertTrue("Error parsing LLM response" in result.generation_summary)
        # Check that the raw response snippet is included in the summary
        self.assertTrue("Raw response: This is not valid JSON { " in result.generation_summary)

if __name__ == '__main__':
    unittest.main()
