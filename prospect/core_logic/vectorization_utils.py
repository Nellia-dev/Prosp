from typing import List, Optional, Any, Dict
import numpy as np
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from data_models.core import AnalyzedLead # Assuming this is the correct path

# Initialize a sentence transformer model
# Using a multilingual model as a default, can be configured
# Ensure this model is suitable for Portuguese
model = SentenceTransformer('all-MiniLM-L6-v2')

def generate_lead_vector(analyzed_lead: AnalyzedLead) -> Optional[List[float]]:
    """
    Generates a vector embedding for a given AnalyzedLead.
    Combines text embedding from cleaned_text_content with structured data.
    """
    if not analyzed_lead:
        return None

    vectors_to_combine = []

    # 1. Text embedding
    text_to_embed = analyzed_lead.validated_lead.cleaned_text_content
    if text_to_embed and len(text_to_embed.strip()) > 10: # Basic check for meaningful text
        try:
            text_embedding = model.encode(text_to_embed, convert_to_tensor=False)
            vectors_to_combine.append(text_embedding)
        except Exception as e:
            print(f"Error encoding text: {e}") # Replace with logger in real implementation
            pass # Or handle more gracefully

    # 2. Structured data embedding (simple example)
    # This part can be significantly enhanced based on specific needs
    structured_features = []
    if analyzed_lead.analysis:
        # Relevance score (numerical)
        structured_features.append(analyzed_lead.analysis.relevance_score or 0.0)

        # Company sector (categorical - needs proper encoding)
        # For simplicity, we'll use a placeholder length or a simple mapping if available
        # Example: map sector to a number, or use one-hot encoding
        # For now, just adding a placeholder value if sector exists
        if analyzed_lead.analysis.company_sector:
            structured_features.append(1.0) # Placeholder for sector presence
        else:
            structured_features.append(0.0)

        # Potential challenges (boolean-like: present or not)
        if analyzed_lead.analysis.potential_challenges and len(analyzed_lead.analysis.potential_challenges) > 0:
            structured_features.append(1.0)
        else:
            structured_features.append(0.0)

    if structured_features:
        # Ensure structured features are in a numpy array of the same type as text_embedding if it exists
        structured_embedding = np.array(structured_features, dtype=np.float32)
        # Normalize or scale structured_embedding if necessary, especially if concatenating with text_embedding
        # For now, direct append for simplicity if text_embedding is also 1D
        vectors_to_combine.append(structured_embedding)

    if not vectors_to_combine:
        return None

    # Combine embeddings (e.g., concatenation)
    # Ensure all embeddings are 1D arrays before concatenation
    final_vector_parts = []
    for v in vectors_to_combine:
        if isinstance(v, np.ndarray):
            final_vector_parts.extend(v.tolist()) # Convert numpy arrays to list
        elif isinstance(v, list):
            final_vector_parts.extend(v)

    if not final_vector_parts:
        return None

    # It's crucial that the final vector has a consistent dimension.
    # The current approach of simple concatenation will result in variable length if not all parts are present.
    # A more robust strategy would be to ensure fixed length for each part,
    # e.g., zero-padding for missing text embedding or fixed-size one-hot encoding for categoricals.
    # For this initial step, we'll return the concatenated list.
    # Consider standardizing the length of the final_vector in a future step.
    return final_vector_parts

# Example Usage (for testing purposes, can be removed or put in a __main__ block)
# class MockValidatedLead(BaseModel):
#     cleaned_text_content: Optional[str] = None
# class MockLeadAnalysis(BaseModel):
#     company_sector: Optional[str] = None
#     main_services: List[str] = []
#     potential_challenges: List[str] = []
#     relevance_score: float = 0.0
# class MockAnalyzedLead(BaseModel):
#     validated_lead: MockValidatedLead
#     analysis: MockLeadAnalysis

# if __name__ == '__main__':
#     sample_lead_data = {
#         "validated_lead": {
#             "cleaned_text_content": "Esta é uma empresa de tecnologia que oferece soluções de software."
#         },
#         "analysis": {
#             "company_sector": "Tecnologia",
#             "main_services": ["Desenvolvimento de Software", "Consultoria TI"],
#             "potential_challenges": ["Concorrência acirrada"],
#             "relevance_score": 0.8
#         }
#     }
#     mock_lead = MockAnalyzedLead(**sample_lead_data)
#     vector = generate_lead_vector(mock_lead)
#     if vector:
#         print(f"Generated vector (first 10 dims): {vector[:10]}")
#         print(f"Vector dimension: {len(vector)}")
#     else:
#         print("Could not generate vector.")
