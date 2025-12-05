"""
Verification Agent - Generates verdicts for claims based on evidence
"""
from typing import List, Dict, Any
import json
import structlog
from groq import AsyncGroq

from app.core.config import settings

logger = structlog.get_logger()


VERIFICATION_PROMPT = """You are an expert fact-checker. Analyze this claim against the provided evidence.

CLAIM TO VERIFY:
{claim_text}

EVIDENCE:
{evidence_text}

Based on the evidence, provide your verdict:

1. **Verdict** (choose one):
   - strongly_supported: Multiple authoritative sources confirm this claim
   - supported: Evidence generally supports this claim
   - mixed: Evidence is conflicting or partial
   - weak: Limited or unreliable evidence
   - contradicted: Evidence contradicts this claim
   - outdated: Evidence suggests information is no longer current
   - not_verifiable: Cannot find sufficient evidence to verify

2. **Confidence** (0.0 to 1.0): How confident are you in this verdict?

3. **Reasoning**: Brief explanation (2-3 sentences) of why you reached this verdict.

4. **Supporting Sources**: List URLs that support the claim (if any)

5. **Contradicting Sources**: List URLs that contradict the claim (if any)

Respond in JSON format:
{{
    "verdict": "...",
    "confidence": 0.X,
    "reasoning": "...",
    "supporting_sources": ["url1", "url2"],
    "contradicting_sources": ["url1"]
}}

IMPORTANT:
- Base your verdict ONLY on the provided evidence
- If evidence is insufficient, say so honestly
- Don't assume facts not in the evidence
- Be conservative - use "mixed" or "weak" if uncertain
- Return ONLY valid JSON, no other text"""


class VerificationAgent:
    """
    Generates verdicts for claims based on retrieved evidence.
    
    Uses Groq's Llama 3.1 70B (FREE) for high-quality reasoning.
    """
    
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = settings.LLM_MODEL
    
    async def verify_claims(
        self,
        claims: List[Dict[str, Any]],
        evidence: Dict[str, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Generate verdicts for all claims.
        
        Args:
            claims: List of claims to verify
            evidence: Dictionary of claim_id to evidence items
            
        Returns:
            List of verdicts
        """
        if not claims:
            return []
        
        logger.info("Verifying claims", count=len(claims))
        
        verdicts = []
        
        for claim in claims:
            claim_id = claim["id"]
            claim_evidence = evidence.get(claim_id, [])
            
            try:
                verdict = await self._verify_single_claim(claim, claim_evidence)
                verdict["claim_id"] = claim_id
                verdicts.append(verdict)
                
            except Exception as e:
                logger.error(
                    "Verification failed for claim",
                    claim_id=claim_id,
                    error=str(e)
                )
                # Add fallback verdict
                verdicts.append({
                    "claim_id": claim_id,
                    "verdict": "not_verifiable",
                    "confidence": 0.0,
                    "reasoning": "Verification failed due to an error.",
                    "supporting_sources": [],
                    "contradicting_sources": [],
                    "model_used": self.model
                })
        
        logger.info("Claims verified", count=len(verdicts))
        return verdicts
    
    async def _verify_single_claim(
        self,
        claim: Dict[str, Any],
        evidence: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Verify a single claim against its evidence."""
        
        # Format evidence for prompt
        if not evidence:
            evidence_text = "No evidence found for this claim."
        else:
            evidence_parts = []
            for i, e in enumerate(evidence[:5], 1):  # Limit to top 5
                evidence_parts.append(
                    f"Source {i}:\n"
                    f"  URL: {e.get('url', 'N/A')}\n"
                    f"  Domain: {e.get('domain', 'N/A')} (reputation: {e.get('domain_reputation', 0.5):.2f})\n"
                    f"  Published: {e.get('published_at', 'Unknown')}\n"
                    f"  Content: {e.get('snippet', 'N/A')}"
                )
            evidence_text = "\n\n".join(evidence_parts)
        
        # Format prompt
        prompt = VERIFICATION_PROMPT.format(
            claim_text=claim["text"],
            evidence_text=evidence_text
        )
        
        # Call Groq API
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a fact-checking expert. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=1000
        )
        
        # Parse response
        content = response.choices[0].message.content
        
        # Extract JSON from response
        start = content.find('{')
        end = content.rfind('}') + 1
        if start >= 0 and end > start:
            result = json.loads(content[start:end])
        else:
            raise ValueError("Could not parse verdict JSON")
        
        # Validate and normalize
        result["verdict"] = result.get("verdict", "not_verifiable").lower()
        result["confidence"] = max(0.0, min(1.0, float(result.get("confidence", 0.5))))
        result["reasoning"] = result.get("reasoning", "")
        result["supporting_sources"] = result.get("supporting_sources", [])
        result["contradicting_sources"] = result.get("contradicting_sources", [])
        result["model_used"] = self.model
        
        return result
