from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class BlogIdea(BaseModel):
    title: str = Field(..., description="Catchy title for the blog post.")
    outline: List[str] = Field(default_factory=list, description="Key points or a brief outline for the blog post.")
    draft_intro_paragraph: Optional[str] = Field(None, description="A short drafted introductory paragraph for one of the blog ideas.")

class SocialMediaPost(BaseModel):
    platform: str = Field(..., description="Target social media platform (e.g., LinkedIn, Twitter, Instagram).")
    post_text: str = Field(..., description="Text content for the social media post.")
    hashtags: List[str] = Field(default_factory=list, description="Suggested relevant hashtags for the post.")

class ContentMarketingInput(BaseModel):
    topic: str = Field(..., description="The central topic or keyword for content generation.")
    target_audience: str = Field(..., description="Description of the target audience.")
    content_goals: List[str] = Field(default_factory=list, description="List of goals for the content (e.g., 'increase engagement', 'generate leads').")

class ContentMarketingOutput(BaseModel):
    input_topic: str = Field(..., description="The topic provided as input.")
    blog_post_ideas: List[BlogIdea] = Field(default_factory=list, description="List of generated blog post ideas.")
    social_media_posts: List[SocialMediaPost] = Field(default_factory=list, description="List of generated social media post ideas.")
    suggested_seo_keywords: List[str] = Field(default_factory=list, description="List of suggested SEO keywords related to the topic.")
    suggested_hashtags: List[str] = Field(default_factory=list, description="General list of suggested hashtags for the topic.")
    generation_summary: Optional[str] = Field(None, description="A brief summary of the generation process or any overall notes.")
