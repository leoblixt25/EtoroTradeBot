import json
import structlog
import time
from typing import Any, Dict, List, Optional
from datetime import datetime

from backend.ai.prompts import (
    SYSTEM_PROMPT,
    PORTFOLIO_ANALYSIS_PROMPT,
    TRADER_ANALYSIS_PROMPT,
    WEEKLY_SUMMARY_PROMPT,
    RISK_ALERT_PROMPT,
)

logger = structlog.get_logger(__name__)


class ClaudeClient:
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key
        self.model = model
        self._base_url = "https://api.anthropic.com/v1/messages"

    def analyze_portfolio(
        self,
        portfolio_data: Dict[str, Any],
        risk_data: Dict[str, Any],
        trader_data: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        prompt = PORTFOLIO_ANALYSIS_PROMPT.format(
            portfolio_summary=json.dumps(portfolio_data, indent=2, default=str),
            risk_metrics=json.dumps(risk_data, indent=2, default=str),
            trader_data=json.dumps(trader_data, indent=2, default=str),
        )
        response = self._call_claude(prompt, SYSTEM_PROMPT)
        return self._parse_response(response)

    def analyze_trader(
        self,
        trader_data: Dict[str, Any],
        performance_history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        prompt = TRADER_ANALYSIS_PROMPT.format(
            trader_history=json.dumps(performance_history, indent=2, default=str),
            metrics=json.dumps(trader_data, indent=2, default=str),
        )
        response = self._call_claude(prompt, SYSTEM_PROMPT)
        return self._parse_response(response)

    def generate_weekly_summary(self, weekly_data: Dict[str, Any]) -> Dict[str, Any]:
        prompt = WEEKLY_SUMMARY_PROMPT.format(
            weekly_data=json.dumps(weekly_data, indent=2, default=str),
        )
        response = self._call_claude(prompt, SYSTEM_PROMPT)
        return self._parse_response(response)

    def explain_recommendation(self, recommendation_data: Dict[str, Any]) -> str:
        prompt = f"""Provide a clear, concise explanation for the following portfolio recommendation:

RECOMMENDATION:
{json.dumps(recommendation_data, indent=2, default=str)}

Explain why this recommendation is being made, what the expected outcome is, and any risks involved. Keep the explanation to 2-3 paragraphs."""
        response = self._call_claude(prompt, SYSTEM_PROMPT, max_tokens=1000)
        return response if response else "Unable to generate explanation at this time."

    def generate_risk_alert(self, risk_data: Dict[str, Any]) -> Dict[str, Any]:
        prompt = RISK_ALERT_PROMPT.format(
            risk_data=json.dumps(risk_data, indent=2, default=str),
        )
        response = self._call_claude(prompt, SYSTEM_PROMPT)
        return self._parse_response(response)

    def _call_claude(self, prompt: str, system_prompt: str, max_tokens: int = 2000) -> str:
        if not self.api_key:
            logger.warning("no claude api key configured, returning fallback")
            return self._fallback_response(prompt)

        import httpx

        max_retries = 3
        base_delay = 1.0

        for attempt in range(max_retries):
            try:
                headers = {
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                }
                body = {
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": prompt}],
                }
                with httpx.Client(timeout=60.0) as client:
                    resp = client.post(self._base_url, headers=headers, json=body)
                    resp.raise_for_status()
                    data = resp.json()
                    content_blocks = data.get("content", [])
                    text = ""
                    for block in content_blocks:
                        if block.get("type") == "text":
                            text += block.get("text", "")
                    return text
            except httpx.HTTPStatusError as e:
                logger.error("claude api http error", status=e.response.status_code, attempt=attempt + 1)
                if e.response.status_code in (429, 500, 502, 503):
                    if attempt < max_retries - 1:
                        time.sleep(base_delay * (2 ** attempt))
                        continue
                return self._fallback_response(prompt)
            except httpx.RequestError as e:
                logger.error("claude api request error", error=str(e), attempt=attempt + 1)
                if attempt < max_retries - 1:
                    time.sleep(base_delay * (2 ** attempt))
                    continue
                return self._fallback_response(prompt)
            except Exception as e:
                logger.error("claude api unexpected error", error=str(e))
                return self._fallback_response(prompt)

        return self._fallback_response(prompt)

    def _parse_response(self, response: str) -> Dict[str, Any]:
        if not response:
            return {"error": "empty response", "analysis": "Unable to generate analysis at this time."}
        try:
            json_start = response.index("{")
            json_end = response.rindex("}") + 1
            json_str = response[json_start:json_end]
            return json.loads(json_str)
        except (ValueError, json.JSONDecodeError):
            logger.warning("failed to parse claude response as json")
            return {"error": "parse_failed", "raw_response": response[:500]}

    def validate_recommendation(self, rec: Dict[str, Any]) -> bool:
        dangerous_keywords = [
            "margin_call", "liquidate all", "sell everything", "all in",
            "double down", "maximum leverage", "bet", "gamble",
        ]
        text = json.dumps(rec).lower()
        for kw in dangerous_keywords:
            if kw in text:
                logger.warning("recommendation blocked - dangerous content", keyword=kw)
                return False
        return True

    def _fallback_response(self, prompt: str) -> str:
        if "PORTFOLIO_ANALYSIS" in prompt or "portfolio_summary" in prompt:
            return json.dumps({
                "analysis": "AI analysis unavailable - API key not configured. Review risk metrics manually.",
                "risks": ["Unable to perform AI-driven risk analysis"],
                "recommendations": [{
                    "type": "monitor",
                    "title": "Configure AI Integration",
                    "summary": "Set CLAUDE_API_KEY environment variable for AI-powered recommendations",
                    "reasoning": "AI analysis provides deeper insights than automated metrics alone",
                    "priority": "low",
                }],
                "confidence_score": 0.0,
            })
        if "TRADER_ANALYSIS" in prompt or "trader_history" in prompt:
            return json.dumps({
                "strengths": ["Analysis unavailable without API key"],
                "weaknesses": ["Enable Claude API for detailed trader analysis"],
                "warning_signs": [],
                "sustainability_assessment": "Unable to assess - AI analysis not configured",
                "overall_grade": "N/A",
            })
        if "WEEKLY_SUMMARY" in prompt or "weekly_data" in prompt:
            return json.dumps({
                "performance_review": "Weekly summary generation requires Claude API configuration",
                "key_events": ["AI analysis unavailable"],
                "risk_assessment": "Review risk metrics manually in dashboard",
                "recommendations": ["Configure CLAUDE_API_KEY for automated summaries"],
                "outlook": "Enable AI features for detailed forward outlook",
            })
        if "RISK_DATA" in prompt or "risk_data" in prompt:
            return json.dumps({
                "alert_title": "Risk Alert Generation Unavailable",
                "explanation": "Configure Claude API key for detailed risk explanations",
                "potential_impact": "Limited risk assessment detail without AI",
                "recommended_actions": ["Enable Claude API integration"],
                "urgency": "medium",
                "timeframe": "Configure at earliest convenience",
            })
        return json.dumps({"error": "unable to analyze - AI service not configured"})
