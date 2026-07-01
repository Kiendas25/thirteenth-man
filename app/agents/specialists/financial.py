from __future__ import annotations

from app.agents.base import BaseAgent


class FinancialAgent(BaseAgent):
    id = "financial"
    name = "Quant / Financial"
    role = "Specialist - Financial Analysis"
    description = (
        "Analyses financial data, models, markets, and economic trends. "
        "Never executes orders without human approval and regulatory "
        "layer. Provides analysis, not investment advice."
    )
    capabilities = [
        "financial_analysis",
        "market_research",
        "risk_modelling",
        "portfolio_evaluation",
        "economic_forecasting",
        "data_visualisation",
    ]
    system_prompt = (
        "You are a quantitative financial analyst. You analyse financial data, "
        "market trends, risk metrics, and economic indicators. You provide "
        "data-driven analysis but NEVER give direct investment advice. Always "
        "include disclaimers about the limitations of your analysis. Flag any "
        "action that could have financial consequences for human review."
    )

    def _build_user_prompt(self, task: str, context: dict) -> str:
        parts = [f"Financial analysis request: {task}"]
        if data := context.get("financial_data"):
            parts.append(f"Available data: {data}")
        if timeframe := context.get("timeframe"):
            parts.append(f"Timeframe: {timeframe}")
        return "\n".join(parts)
