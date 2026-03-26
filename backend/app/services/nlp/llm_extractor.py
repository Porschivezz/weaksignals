"""Level 2/3 deep entity extraction using Anthropic Claude models."""

import json
import logging

import anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

L2_MODEL = "claude-haiku-4-5-20251001"
L3_MODEL = "claude-opus-4-6"

EXTRACTION_PROMPT_TEMPLATE = """Analyze the following academic paper and extract structured information.

Title: {title}

Abstract: {abstract}

Extract the following in JSON format:
{{
  "entities": [
    {{
      "name": "entity name",
      "type": "technology|method|algorithm|framework|material",
      "confidence": 0.0-1.0,
      "description": "brief description of the entity"
    }}
  ],
  "relations": [
    {{
      "source": "entity name",
      "target": "entity name",
      "relation_type": "uses|improves|extends|competes_with|enables|part_of|applied_to",
      "description": "brief description of the relationship"
    }}
  ],
  "methods": [
    {{
      "name": "method name",
      "category": "training|inference|data_processing|evaluation|optimization",
      "novelty": "novel|incremental|established"
    }}
  ],
  "algorithms": [
    {{
      "name": "algorithm name",
      "type": "optimization|search|learning|inference",
      "complexity": "description if mentioned"
    }}
  ],
  "hardware_requirements": [
    {{
      "type": "GPU|TPU|CPU|FPGA|other",
      "details": "specific hardware mentioned"
    }}
  ],
  "significance_narrative": "A 2-3 sentence summary of why this work is significant and what it contributes to the field.",
  "novelty_assessment": {{
    "is_novel": true or false,
    "novelty_type": "new_method|new_application|new_architecture|incremental_improvement|survey|benchmark",
    "reasoning": "brief explanation of novelty assessment"
  }},
  "domains": ["list of application domains this relates to"]
}}

Return ONLY valid JSON, no additional text or markdown formatting."""

L3_EXTRACTION_PROMPT_TEMPLATE = """You are an expert scientific analyst. Perform a comprehensive deep analysis of this academic paper.

Title: {title}

Abstract: {abstract}

Provide a thorough analysis in JSON format:
{{
  "entities": [
    {{
      "name": "entity name",
      "type": "technology|method|algorithm|framework|material",
      "confidence": 0.0-1.0,
      "description": "detailed description of the entity",
      "maturity": "emerging|developing|mature|declining",
      "impact_potential": "high|medium|low"
    }}
  ],
  "relations": [
    {{
      "source": "entity name",
      "target": "entity name",
      "relation_type": "uses|improves|extends|competes_with|enables|part_of|applied_to|supersedes|inspired_by",
      "strength": 0.0-1.0,
      "description": "detailed description of the relationship",
      "evidence": "quote or reference from the text supporting this relation"
    }}
  ],
  "methods": [
    {{
      "name": "method name",
      "category": "training|inference|data_processing|evaluation|optimization",
      "novelty": "novel|incremental|established",
      "advantages": ["list of advantages"],
      "limitations": ["list of limitations"]
    }}
  ],
  "algorithms": [
    {{
      "name": "algorithm name",
      "type": "optimization|search|learning|inference",
      "complexity": "description if mentioned",
      "improvements_over": "what it improves upon"
    }}
  ],
  "hardware_requirements": [
    {{
      "type": "GPU|TPU|CPU|FPGA|other",
      "details": "specific hardware mentioned",
      "scale": "single device|multi-device|distributed"
    }}
  ],
  "significance_narrative": "A comprehensive 3-5 sentence analysis of the paper's significance, its position in the broader research landscape, potential real-world impact, and implications for future research directions.",
  "novelty_assessment": {{
    "is_novel": true or false,
    "novelty_type": "new_method|new_application|new_architecture|incremental_improvement|survey|benchmark|theoretical_breakthrough",
    "novelty_score": 0.0-1.0,
    "reasoning": "detailed explanation of novelty assessment",
    "prior_work_connections": ["list of likely related prior works or approaches"]
  }},
  "domains": ["list of application domains this relates to"],
  "weak_signal_indicators": {{
    "cross_domain_potential": true or false,
    "unconventional_combination": true or false,
    "early_stage_indicator": true or false,
    "explanation": "why this might represent a weak signal of future trends"
  }},
  "timeline_estimate": {{
    "research_maturity": "theoretical|experimental|practical|deployed",
    "estimated_years_to_mainstream": "1-2|3-5|5-10|10+|uncertain"
  }}
}}

Return ONLY valid JSON, no additional text or markdown formatting."""


class LLMExtractor:
    """Level 2/3 deep entity extractor using Anthropic Claude models.

    L2 uses Claude Haiku for fast, structured extraction.
    L3 uses Claude Opus for comprehensive analysis with deeper insights.
    """

    def __init__(self, api_key: str) -> None:
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    @retry(
        retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.APIConnectionError)),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def _call_claude(self, model: str, prompt: str, max_tokens: int = 4096) -> str:
        """Call the Claude API with retry logic for transient errors.

        Args:
            model: The model identifier to use.
            prompt: The user prompt to send.
            max_tokens: Maximum tokens in the response.

        Returns:
            The text content of the response.
        """
        response = await self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )
        text_blocks = [block.text for block in response.content if block.type == "text"]
        return "".join(text_blocks)

    async def extract_deep(
        self, abstract: str, title: str, level: str = "L2"
    ) -> dict:
        """Perform deep extraction of entities, relations, and significance.

        Args:
            abstract: The paper abstract text.
            title: The paper title.
            level: Extraction level - "L2" for fast (Haiku) or "L3" for comprehensive (Opus).

        Returns:
            Structured dict with entities, relations, significance_narrative,
            novelty_assessment, and other analysis fields.
        """
        if not abstract and not title:
            logger.warning("Both abstract and title are empty, skipping LLM extraction")
            return self._empty_result()

        if level == "L3":
            model = L3_MODEL
            prompt = L3_EXTRACTION_PROMPT_TEMPLATE.format(title=title, abstract=abstract)
            max_tokens = 8192
        else:
            model = L2_MODEL
            prompt = EXTRACTION_PROMPT_TEMPLATE.format(title=title, abstract=abstract)
            max_tokens = 4096

        try:
            raw_response = await self._call_claude(model, prompt, max_tokens)
            result = self._parse_json_response(raw_response)
            logger.info(
                "LLM extraction (%s) completed: %d entities, %d relations",
                level,
                len(result.get("entities", [])),
                len(result.get("relations", [])),
            )
            return result
        except anthropic.APIError as exc:
            logger.error("Anthropic API error during %s extraction: %s", level, exc)
            return self._empty_result()
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse LLM response as JSON: %s", exc)
            return self._empty_result()

    @staticmethod
    def _parse_json_response(raw: str) -> dict:
        """Parse a JSON response from the LLM, handling markdown code blocks.

        Args:
            raw: The raw text response from the LLM.

        Returns:
            Parsed dict from the JSON response.
        """
        text = raw.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json or ```) and last line (```)
            start_idx = 1
            end_idx = len(lines)
            for i in range(len(lines) - 1, 0, -1):
                if lines[i].strip() == "```":
                    end_idx = i
                    break
            text = "\n".join(lines[start_idx:end_idx])

        return json.loads(text)

    @staticmethod
    def _empty_result() -> dict:
        """Return an empty result structure matching the expected schema."""
        return {
            "entities": [],
            "relations": [],
            "methods": [],
            "algorithms": [],
            "hardware_requirements": [],
            "significance_narrative": "",
            "novelty_assessment": {
                "is_novel": False,
                "novelty_type": "unknown",
                "reasoning": "Extraction failed or no content provided.",
            },
            "domains": [],
        }
