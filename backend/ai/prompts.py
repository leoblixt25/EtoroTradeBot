SYSTEM_PROMPT = """You are an expert investment analyst assistant for eToro portfolio management. Your role is to provide clear, risk-aware, evidence-based analysis and recommendations. You prioritize capital preservation and long-term consistency. You NEVER recommend emotional trading, revenge trading, or excessive risk-taking. Always explain reasoning and provide confidence levels."""

PORTFOLIO_ANALYSIS_PROMPT = """Analyze the following eToro portfolio and provide structured recommendations focused on capital preservation and risk management.

PORTFOLIO SUMMARY:
{portfolio_summary}

RISK METRICS:
{risk_metrics}

COPIED TRADERS:
{trader_data}

Your analysis must:
1. Identify concentration risks and overexposure to any single trader, sector, or instrument type
2. Flag traders showing sustained underperformance
3. Suggest rebalancing opportunities to improve diversification
4. Identify positions with significant unrealized gains that may warrant profit-taking
5. Highlight any risk limit violations or approaching thresholds

Return ONLY a valid JSON object with this exact structure:
{{
    "analysis": "string - detailed analysis summary",
    "risks": ["list of risk descriptions"],
    "recommendations": [
        {{
            "type": "string (rebalance|reduce|pause|take_profit|monitor)",
            "title": "string",
            "summary": "string",
            "reasoning": "string",
            "priority": "high|medium|low"
        }}
    ],
    "confidence_score": "float between 0 and 1"
}}"""

TRADER_ANALYSIS_PROMPT = """Analyze the following eToro trader based on their performance history and risk metrics.

TRADER HISTORY:
{trader_history}

METRICS:
{metrics}

Evaluate the trader's:
1. Performance consistency and sustainability
2. Risk management approach based on historical drawdowns
3. Warning signs (increasing volatility, declining win rate, larger drawdowns)
4. Overall suitability for capital preservation-focused portfolios

Return ONLY a valid JSON object with this exact structure:
{{
    "strengths": ["list of trader strengths"],
    "weaknesses": ["list of weaknesses or concerns"],
    "warning_signs": ["any warning indicators"],
    "sustainability_assessment": "string assessment of whether performance is sustainable",
    "overall_grade": "string (A|B|C|D|F)"
}}"""

WEEKLY_SUMMARY_PROMPT = """Generate a weekly performance summary for the eToro portfolio based on the following data:

WEEKLY DATA:
{weekly_data}

Provide a comprehensive weekly review covering:
1. Performance review with key metrics
2. Key events and market conditions that affected the portfolio
3. Current risk assessment and any changes from prior week
4. Actionable recommendations for the coming week
5. Forward outlook based on current positioning

Return ONLY a valid JSON object with this exact structure:
{{
    "performance_review": "string - summary of weekly performance",
    "key_events": ["list of key events affecting performance"],
    "risk_assessment": "string - current risk assessment",
    "recommendations": ["list of actionable recommendations"],
    "outlook": "string - forward outlook"
}}"""

RISK_ALERT_PROMPT = """Generate a clear, actionable risk alert explanation based on the following risk data:

RISK DATA:
{risk_data}

The alert should:
1. Clearly explain what risk threshold has been breached
2. Explain the potential impact on the portfolio
3. Provide specific recommended actions to mitigate the risk
4. Indicate the urgency level of the situation

Return ONLY a valid JSON object with this exact structure:
{{
    "alert_title": "string - clear title for the alert",
    "explanation": "string - detailed explanation of the risk",
    "potential_impact": "string - what could happen if unaddressed",
    "recommended_actions": ["list of specific actions to mitigate"],
    "urgency": "immediate|high|medium|low",
    "timeframe": "string - suggested timeframe for action"
}}"""
