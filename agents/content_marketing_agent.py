from typing import List, Optional
from loguru import logger
from pydantic import ValidationError

from agents.base_agent import BaseAgent, LLMProvider
from data_models.content_marketing_models import (
    ContentMarketingInput,
    ContentMarketingOutput,
    BlogIdea,
    SocialMediaPost,
)

class ContentMarketingAgent(BaseAgent[ContentMarketingInput, ContentMarketingOutput]):
    """
    Agent for generating content marketing ideas including blog posts,
    social media content, SEO keywords, and hashtags based on a given topic,
    target audience, and content goals.
    """

    DEFAULT_LLM_PROVIDER = LLMProvider.GEMINI # Or your preferred default

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        config: Optional[dict] = None,
    ):
        super().__init__(
            name="Content Marketing Agent",
            description="Generates content marketing ideas (blog posts, social media, SEO keywords).",
            llm_provider=llm_provider or self.DEFAULT_LLM_PROVIDER,
            config=config,
        )

    def _build_llm_prompt(self, input_data: ContentMarketingInput) -> str:
        prompt = f"""
You are an expert Content Marketing Strategist. Your task is to generate creative and effective content ideas based on the provided information.

**Topic:** {input_data.topic}
**Target Audience:** {input_data.target_audience}
**Content Goals:** {', '.join(input_data.content_goals) if input_data.content_goals else 'Not specified'}

Please generate the following, ensuring variety and relevance:

1.  **Blog Post Ideas (2-3 ideas):**
    *   For each idea, provide:
        *   A catchy `title`.
        *   A brief `outline` (3-5 key bullet points).
        *   Draft an `introductory paragraph` for ONE of these blog ideas. Make it engaging.

2.  **Social Media Posts (1 idea for each platform: LinkedIn, Twitter/X, Instagram):**
    *   For each platform:
        *   Craft engaging `post_text` suitable for the platform and audience.
        *   Suggest 2-3 relevant `hashtags`.

3.  **SEO Keywords (3-5 keywords):**
    *   Suggest relevant SEO keywords that the target audience might use to search for content on this topic.

4.  **General Hashtags (5-7 hashtags):**
    *   Suggest a list of general hashtags relevant to the core topic.

Present your response in a structured JSON format. The main keys should be "blog_post_ideas", "social_media_posts", "suggested_seo_keywords", and "suggested_hashtags".

Example JSON structure:
{{
    "blog_post_ideas": [
        {{
            "title": "Example Blog Title 1",
            "outline": ["Point 1", "Point 2", "Point 3"],
            "draft_intro_paragraph": "This is an engaging intro for Blog Title 1..."
        }},
        {{
            "title": "Example Blog Title 2",
            "outline": ["Key Aspect A", "Key Aspect B", "Key Aspect C"]
            // No draft_intro_paragraph for this one, as only one is requested.
        }}
    ],
    "social_media_posts": [
        {{
            "platform": "LinkedIn",
            "post_text": "Professional insight on {{input_data.topic}} for LinkedIn...",
            "hashtags": ["#business", "#linkedin"]
        }},
        {{
            "platform": "Twitter", // Or X
            "post_text": "Quick take on {{input_data.topic}} for Twitter/X! #shortandsweet",
            "hashtags": ["#twittertip", "#X"]
        }},
        {{
            "platform": "Instagram",
            "post_text": "Visually engaging angle for {{input_data.topic}} on Instagram. Image idea: [describe image]",
            "hashtags": ["#instacontent", "#visual"]
        }}
    ],
    "suggested_seo_keywords": ["keyword1", "keyword2", "long tail keyword3"],
    "suggested_hashtags": ["#generaltopic", "#relevanttag", "#anotherone"]
}}
Ensure the output is a valid JSON object.
"""
        return prompt

    def process(self, input_data: ContentMarketingInput) -> ContentMarketingOutput:
        logger.info(
            f"[{self.name}] Starting content generation for topic: {input_data.topic}"
        )

        prompt = self._build_llm_prompt(input_data)
        logger.debug(f"[{self.name}] Generated LLM prompt: {prompt[:500]}...") # Log first 500 chars

        try:
            llm_response_str = self.generate_llm_response(prompt)
            logger.debug(f"[{self.name}] LLM raw response: {llm_response_str[:500]}...")
        except Exception as e:
            logger.error(f"[{self.name}] LLM generation failed: {e}")
            # Return a partial output or raise an error, depending on desired handling
            return ContentMarketingOutput(
                input_topic=input_data.topic,
                generation_summary=f"Error during LLM generation: {e}",
            )

        try:
            # Using the parse_llm_json_response from BaseAgent
            # BaseAgent's method already handles common JSON extraction issues (like markdown code blocks)
            parsed_response = self.parse_llm_json_response(llm_response_str, dict)

            # Now, map this dictionary to our Pydantic models
            # We need to be careful with potential missing fields or structure mismatches
            # from the LLM if it doesn't perfectly follow instructions.

            blog_ideas_data = parsed_response.get("blog_post_ideas", [])
            blog_ideas = []
            for idea_data in blog_ideas_data:
                try:
                    blog_ideas.append(BlogIdea.parse_obj(idea_data))
                except ValidationError as ve:
                    logger.warning(f"[{self.name}] Validation error for a blog idea: {ve}. Data: {idea_data}")
                    # Optionally skip this item or add with partial data

            social_posts_data = parsed_response.get("social_media_posts", [])
            social_posts = []
            for post_data in social_posts_data:
                try:
                    social_posts.append(SocialMediaPost.parse_obj(post_data))
                except ValidationError as ve:
                    logger.warning(f"[{self.name}] Validation error for a social post: {ve}. Data: {post_data}")

            output = ContentMarketingOutput(
                input_topic=input_data.topic,
                blog_post_ideas=blog_ideas,
                social_media_posts=social_posts,
                suggested_seo_keywords=parsed_response.get("suggested_seo_keywords", []),
                suggested_hashtags=parsed_response.get("suggested_hashtags", []),
                generation_summary="Content ideas generated successfully.",
            )
            logger.info(f"[{self.name}] Successfully parsed LLM response and created output object.")
            return output

        except (ValueError, ValidationError) as e: # Catch parsing or Pydantic validation errors
            logger.error(f"[{self.name}] Failed to parse or validate LLM JSON response: {e}")
            logger.debug(f"Problematic LLM response string: {llm_response_str}")
            # Consider how to handle this - maybe return output with an error message
            return ContentMarketingOutput(
                input_topic=input_data.topic,
                generation_summary=f"Error parsing LLM response: {e}. Raw response: {llm_response_str[:1000]}..."
            )
        except Exception as e:
            logger.error(f"[{self.name}] An unexpected error occurred during processing: {e}")
            return ContentMarketingOutput(
                input_topic=input_data.topic,
                generation_summary=f"Unexpected error: {e}",
            )

if __name__ == "__main__":
    # This is a simple test block that can be run directly
    # For more comprehensive testing, use the test suite.
    logger.remove() # Remove default logger
    logger.add(lambda msg: print(msg), level="INFO") # Print to console

    # Ensure you have your LLM provider (e.g., Gemini) API key set in your environment
    # e.g., GEMINI_API_KEY or OPENAI_API_KEY
    # You might need to adjust LLMClientFactory or config if using specific settings

    agent = ContentMarketingAgent() # Uses default LLM provider from environment

    sample_input = ContentMarketingInput(
        topic="Sustainable Gardening for Urban Dwellers",
        target_audience="Millennials and Gen Z living in apartments, interested in eco-friendly practices and home decor.",
        content_goals=["Increase blog readership", "Boost social media engagement", "Promote new line of indoor gardening kits"]
    )

    logger.info(f"Testing agent with topic: {sample_input.topic}")
    try:
        result = agent.execute(sample_input) # Use execute for full process with metrics

        if result:
            logger.info(f"--- Generated Content for: {result.input_topic} ---")

            logger.info("\n**Blog Post Ideas:**")
            for idea in result.blog_post_ideas:
                logger.info(f"  Title: {idea.title}")
                logger.info(f"  Outline: {', '.join(idea.outline)}")
                if idea.draft_intro_paragraph:
                    logger.info(f"  Intro: {idea.draft_intro_paragraph[:100]}...") # Print snippet

            logger.info("\n**Social Media Posts:**")
            for post in result.social_media_posts:
                logger.info(f"  Platform: {post.platform}")
                logger.info(f"  Text: {post.post_text[:100]}...") # Print snippet
                logger.info(f"  Hashtags: {', '.join(post.hashtags)}")

            logger.info(f"\n**SEO Keywords:** {', '.join(result.suggested_seo_keywords)}")
            logger.info(f"**General Hashtags:** {', '.join(result.suggested_hashtags)}")
            logger.info(f"\nSummary: {result.generation_summary}")

            # Print metrics
            # metrics = agent.get_metrics_summary()
            # logger.info(f"\nExecution Metrics: {metrics}")

        else:
            logger.error("Agent execution returned no result.")

    except Exception as e:
        logger.error(f"Error during agent execution test: {e}")
