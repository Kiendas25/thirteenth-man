"""AI Auditor — EU AI Act compliance checker and AI output auditor."""

from __future__ import annotations

import logging
from typing import Any

from app.llm import chat_json

log = logging.getLogger(__name__)

# EU AI Act risk categories (simplified for MVP)
EU_AI_ACT_CHECKLIST = [
    {
        "id": "transparency",
        "title": "Transparency Obligations",
        "description": "AI systems must inform users they are interacting with AI",
        "article": "Article 52",
        "checks": [
            "Users are informed when interacting with an AI system",
            "AI-generated content is labelled as such",
            "Deepfakes are disclosed",
        ],
    },
    {
        "id": "data_governance",
        "title": "Data Governance",
        "description": "Training data must be relevant, representative, and free of errors",
        "article": "Article 10",
        "checks": [
            "Training data is documented and traceable",
            "Data biases are identified and mitigated",
            "Personal data processing complies with GDPR",
        ],
    },
    {
        "id": "human_oversight",
        "title": "Human Oversight",
        "description": "High-risk AI must allow human oversight and intervention",
        "article": "Article 14",
        "checks": [
            "Human can override AI decisions",
            "AI decisions can be reviewed and reversed",
            "Clear escalation path exists",
        ],
    },
    {
        "id": "accuracy",
        "title": "Accuracy & Robustness",
        "description": "AI must maintain appropriate levels of accuracy and robustness",
        "article": "Article 15",
        "checks": [
            "Accuracy metrics are defined and monitored",
            "System is robust against adversarial inputs",
            "Failure modes are documented",
        ],
    },
    {
        "id": "risk_management",
        "title": "Risk Management System",
        "description": "Continuous risk identification and mitigation process",
        "article": "Article 9",
        "checks": [
            "Risks are identified and documented",
            "Mitigation measures are implemented",
            "Residual risks are communicated to users",
        ],
    },
    {
        "id": "documentation",
        "title": "Technical Documentation",
        "description": "Comprehensive technical documentation must be maintained",
        "article": "Article 11",
        "checks": [
            "System design and architecture is documented",
            "Training methodology is described",
            "Performance benchmarks are recorded",
        ],
    },
    {
        "id": "record_keeping",
        "title": "Record-Keeping & Logging",
        "description": "AI systems must maintain logs for traceability",
        "article": "Article 12",
        "checks": [
            "System events are logged automatically",
            "Logs are retained for appropriate period",
            "Audit trail exists for decisions",
        ],
    },
    {
        "id": "cybersecurity",
        "title": "Cybersecurity",
        "description": "AI systems must be resilient against cyber threats",
        "article": "Article 15",
        "checks": [
            "Data encryption in transit and at rest",
            "Access controls are implemented",
            "Vulnerability management process exists",
        ],
    },
]

AUDIT_SYSTEM = """\
You are an AI Auditor specialised in the EU AI Act (Regulation 2024/1689).
You are reviewing an AI system or AI-generated output for compliance.

Evaluate the provided information against each checklist item.
For each item, determine if it PASSES, FAILS, or is UNCLEAR.

Respond with a JSON object:
{{
  "risk_classification": "minimal|limited|high|unacceptable",
  "overall_compliance": "compliant|partially_compliant|non_compliant",
  "score": 0-100,
  "findings": [
    {{
      "checklist_id": "id",
      "status": "pass|fail|unclear",
      "evidence": "specific evidence for this finding",
      "recommendation": "what to do if failing"
    }}
  ],
  "summary": "Executive summary of compliance status",
  "critical_issues": ["list of critical non-compliance issues"],
  "next_steps": ["prioritised actions to achieve compliance"]
}}

Be thorough, cite specific evidence, and provide actionable recommendations.
"""


async def run_ai_audit(
    description: str,
    ai_output: str | None = None,
) -> dict[str, Any]:
    """Run an EU AI Act compliance audit."""
    parts = [f"System/Product Description:\n{description}"]
    if ai_output:
        parts.append(f"\nAI Output to Audit:\n{ai_output}")
    parts.append("\n\nChecklist to evaluate:")
    for item in EU_AI_ACT_CHECKLIST:
        parts.append(f"\n- [{item['id']}] {item['title']} ({item['article']})")
        for check in item["checks"]:
            parts.append(f"  - {check}")

    user_msg = "\n".join(parts)
    data = await chat_json(AUDIT_SYSTEM, user_msg, temperature=0.2)

    # Normalise findings
    findings = data.get("findings", [])
    normalised = []
    for f in findings:
        if isinstance(f, dict):
            normalised.append({
                "checklist_id": str(f.get("checklist_id", "")),
                "status": str(f.get("status", "unclear")),
                "evidence": str(f.get("evidence", "")),
                "recommendation": str(f.get("recommendation", "")),
            })
        elif isinstance(f, str):
            normalised.append({
                "checklist_id": "general",
                "status": "unclear",
                "evidence": f,
                "recommendation": "",
            })

    return {
        "risk_classification": str(data.get("risk_classification", "limited")),
        "overall_compliance": str(data.get("overall_compliance", "partially_compliant")),
        "score": int(data.get("score", 0)),
        "findings": normalised,
        "summary": str(data.get("summary", "")),
        "critical_issues": [str(i) for i in data.get("critical_issues", [])],
        "next_steps": [str(s) for s in data.get("next_steps", [])],
        "checklist": EU_AI_ACT_CHECKLIST,
    }


def generate_certification_html(audit_result: dict, product_name: str) -> str:
    """Generate a certification seal HTML page."""
    score = audit_result.get("score", 0)
    compliance = audit_result.get("overall_compliance", "unknown")
    risk = audit_result.get("risk_classification", "unknown")

    if score >= 80:
        seal_color = "#22c55e"
        seal_text = "COMPLIANT"
    elif score >= 50:
        seal_color = "#f59e0b"
        seal_text = "PARTIALLY COMPLIANT"
    else:
        seal_color = "#ef4444"
        seal_text = "NON-COMPLIANT"

    findings_html = ""
    for f in audit_result.get("findings", []):
        status_color = {"pass": "#22c55e", "fail": "#ef4444"}.get(f["status"], "#f59e0b")
        findings_html += f"""
        <tr>
          <td>{f['checklist_id']}</td>
          <td><span style="color:{status_color};font-weight:600;">{f['status'].upper()}</span></td>
          <td>{f['evidence']}</td>
          <td>{f['recommendation']}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>13th Man Certification — {product_name}</title>
<style>
  body {{ font-family: 'Segoe UI', sans-serif; max-width: 900px; margin: 40px auto; padding: 20px; color: #1a1a2e; }}
  .seal {{ text-align: center; margin: 40px 0; }}
  .seal-badge {{ display: inline-block; width: 200px; height: 200px; border-radius: 50%;
    border: 6px solid {seal_color}; display: flex; align-items: center; justify-content: center;
    flex-direction: column; margin: 0 auto; }}
  .seal-text {{ font-size: 16px; font-weight: 700; color: {seal_color}; margin-top: 12px; }}
  .seal-score {{ font-size: 48px; font-weight: 700; color: {seal_color}; }}
  .seal-label {{ font-size: 12px; color: #64748b; }}
  h1 {{ color: #6366f1; }}
  h2 {{ color: #4f46e5; margin-top: 24px; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 12px; }}
  th, td {{ border: 1px solid #e2e8f0; padding: 8px 12px; text-align: left; font-size: 13px; }}
  th {{ background: #f8fafc; font-weight: 600; }}
  .summary {{ background: #f1f5f9; padding: 16px; border-radius: 8px; margin: 16px 0; line-height: 1.6; }}
  .badge {{ display: inline-block; padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
  .footer {{ margin-top: 40px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 11px; color: #94a3b8; text-align: center; }}
</style>
</head><body>
<h1>13th Man AI Compliance Certificate</h1>
<p><strong>Product:</strong> {product_name} | <strong>Risk Classification:</strong> {risk.upper()} | <strong>Standard:</strong> EU AI Act (2024/1689)</p>

<div class="seal">
  <div style="display:inline-flex;flex-direction:column;align-items:center;width:200px;height:200px;border-radius:50%;border:6px solid {seal_color};justify-content:center;">
    <span class="seal-label">COMPLIANCE SCORE</span>
    <span class="seal-score">{score}</span>
    <span class="seal-label">/ 100</span>
  </div>
  <div class="seal-text">{seal_text}</div>
  <p style="font-size:12px;color:#64748b;margin-top:8px;">Verified by 13th Man Multi-Agent OS</p>
</div>

<h2>Executive Summary</h2>
<div class="summary">{audit_result.get('summary', '')}</div>

<h2>Detailed Findings</h2>
<table>
  <tr><th>Check</th><th>Status</th><th>Evidence</th><th>Recommendation</th></tr>
  {findings_html}
</table>

<h2>Critical Issues</h2>
<ul>{''.join(f'<li>{i}</li>' for i in audit_result.get('critical_issues', [])) or '<li>None identified</li>'}</ul>

<h2>Next Steps</h2>
<ol>{''.join(f'<li>{s}</li>' for s in audit_result.get('next_steps', []))}</ol>

<div class="footer">
  This certificate was generated by 13th Man — Multi-Agent Cognitive Operating System.<br>
  This is an automated assessment and does not constitute legal advice. Consult qualified legal counsel for official compliance certification.
</div>
</body></html>"""
