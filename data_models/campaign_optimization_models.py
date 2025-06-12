from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class CampaignContentType(str, Enum):
    EMAIL_SUBJECT = "EMAIL_SUBJECT"
    AD_HEADLINE = "AD_HEADLINE"
    SOCIAL_MEDIA_POST_TEXT = "SOCIAL_MEDIA_POST_TEXT"
    EMAIL_BODY_SNIPPET = "EMAIL_BODY_SNIPPET"
    CALL_TO_ACTION_TEXT = "CALL_TO_ACTION_TEXT" # Added another common type

class CampaignContentInput(BaseModel):
    content_type: CampaignContentType = Field(..., description="The type of campaign content being analyzed.")
    original_content: str = Field(..., min_length=10, description="The original text content to be reviewed and optimized.")
    target_audience_description: str = Field(..., min_length=10, description="A description of the target audience for this content.")
    desired_outcome: str = Field(..., min_length=10, description="The primary goal of this content (e.g., 'increase open rates', 'improve click-through rate', 'drive engagement').")
    additional_context: Optional[str] = Field(None, description="Any other relevant context, like brand voice, key product features to highlight, or specific campaign details.") # Added for more robust input

class CampaignContentOutput(BaseModel):
    original_content: str = Field(..., description="A copy of the original content that was analyzed.")
    content_type: CampaignContentType = Field(..., description="The type of campaign content that was analyzed.")
    target_audience_description: str = Field(..., description="The target audience considered during analysis.")
    desired_outcome: str = Field(..., description="The desired outcome considered during analysis.")

    suggested_improvements: List[str] = Field(default_factory=list, description="Specific, actionable suggestions for improving the original content.")
    optimized_versions: List[str] = Field(default_factory=list, description="One or more alternative versions of the content with improvements applied.")
    analysis_summary: str = Field(..., description="A brief explanation of the rationale behind the suggested improvements and optimized versions.")
    confidence_score: Optional[float] = Field(None, ge=0, le=1, description="An optional score indicating the AI's confidence in its suggestions (0.0 to 1.0).") # Added optional confidence
    error_message: Optional[str] = Field(None, description="Field to store any error messages if processing fails.")
