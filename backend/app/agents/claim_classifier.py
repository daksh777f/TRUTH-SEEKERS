"""
Claim Classifier Agent - Filters and classifies claims
"""
from typing import List, Dict, Any
import json
import structlog
from groq import AsyncGroq

from app.core.config import settings

logger = structlog.get_logger()


CLASSIFICATION_PROMPT = """Analyze these claims and determine if each is objectively verifiable.

A claim is VERIFIABLE if:
- It makes a factual assertion that can be checked against external sources
- It contains specific, measurable details (numbers, names, dates)
- It could theoretically be proven true or false

A claim is NOT VERIFIABLE if:
- It's a pure opinion or subjective preference
- It's too vague to check
- It's about personal experiences
- It's a prediction about the future
- It's rhetorical or promotional fluff

Claims to analyze:
{claims}

For each claim, respond with JSON array:
[
    {{"claim_id": "clm_xxx", "is_verifiable": true, "reason": "contains specific numbers"}}
]

Return ONLY the JSON array, no other text.
"""


class ClaimClassifierAgent:
    """
    Filters claims to keep only verifiable ones.
    Uses Groq's fast Llama model (FREE) for quick classification.
    """
    
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = settings.LLM_MODEL_FAST  # Use faster model for classification
    
    async def filter_claims(
        self,
        claims: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Filter claims to keep only verifiable ones.
        
        Args:
            claims: List of extracted claims
            
        Returns:
            Filtered list of verifiable claims
        """
        if not claims:
            return []
        
        logger.info("Classifying claims", count=len(claims))
        
        try:
            # Format claims for prompt
            claims_text = "\n".join([
                f"- ID: {c['id']}, Text: {c['text']}"
                for c in claims
            ])
            
            prompt = CLASSIFICATION_PROMPT.format(claims=claims_text)
            
            # Call Groq API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a claim classifier. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            
            # Find JSON array in response
            start = content.find('[')
            end = content.rfind(']') + 1
            if start >= 0 and end > start:
                classifications = json.loads(content[start:end])
            else:
                # If parsing fails, keep all claims
                logger.warning("Could not parse classifications, keeping all claims")
                return claims
            
            # Build lookup of verifiability
            verifiable_ids = set()
            for c in classifications:
                if c.get("is_verifiable", True):
                    verifiable_ids.add(c.get("claim_id"))
            
            # Filter claims
            filtered = [c for c in claims if c["id"] in verifiable_ids]
            
            # Mark remaining as not verifiable for reference
            for c in claims:
                c["is_verifiable"] = c["id"] in verifiable_ids
            
            logger.info(
                "Claims classified",
                total=len(claims),
                verifiable=len(filtered)
            )
            
            return filtered
            
        except Exception as e:
            logger.error("Classification failed", error=str(e))
            # On failure, return all claims (conservative approach)
            return claims
