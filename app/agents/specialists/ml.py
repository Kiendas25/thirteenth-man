from __future__ import annotations

from app.agents.base import BaseAgent


class MLAgent(BaseAgent):
    id = "ml"
    name = "Machine Learning"
    role = "Specialist - Models & Data"
    description = (
        "Designs ML pipelines, evaluates models, analyses datasets. "
        "Good for pipeline architecture and model evaluation. "
        "Less suited as a permanent conversational agent."
    )
    capabilities = [
        "model_design",
        "pipeline_architecture",
        "dataset_analysis",
        "evaluation_metrics",
        "feature_engineering",
        "experiment_design",
    ]
    system_prompt = (
        "You are a machine learning engineer and data scientist. You design "
        "ML pipelines, select appropriate models, evaluate performance, and "
        "analyse datasets. Focus on practical, production-ready solutions. "
        "Include evaluation criteria, potential biases, and deployment "
        "considerations in your recommendations."
    )

    def _build_user_prompt(self, task: str, context: dict) -> str:
        parts = [f"ML task: {task}"]
        if dataset := context.get("dataset"):
            parts.append(f"Dataset info: {dataset}")
        if objective := context.get("objective"):
            parts.append(f"Objective: {objective}")
        return "\n".join(parts)
