#!/usr/bin/env python3
"""13th Man CLI — Run analyses from the terminal.

Usage:
    python cli.py "Analyse this Python code for security issues"
    python cli.py --mode code --lang python --file script.py
    python cli.py --mode github --owner facebook --repo react
    python cli.py --mode github --owner facebook --repo react --pr 123
    python cli.py --mode audit --product "My AI System" --desc "An AI chatbot..."
    python cli.py --history
    python cli.py --task <task_id>
"""

from __future__ import annotations

import argparse
import json
import sys

import httpx

DEFAULT_BASE = "http://localhost:8000"


def coloured(text: str, colour: str) -> str:
    """Apply ANSI colour if terminal supports it."""
    codes = {
        "green": "\033[92m",
        "red": "\033[91m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "reset": "\033[0m",
    }
    if not sys.stdout.isatty():
        return text
    return f"{codes.get(colour, '')}{text}{codes.get('reset', '')}"


def print_header(text: str) -> None:
    print(f"\n{coloured(text, 'bold')}")
    print(coloured("─" * min(len(text), 60), "dim"))


def print_badge(label: str, value: str, colour: str = "blue") -> None:
    print(f"  {coloured(label + ':', 'dim')} {coloured(value, colour)}")


def make_client(base_url: str, token: str | None = None) -> httpx.Client:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.Client(base_url=base_url, headers=headers, timeout=300.0)


def cmd_query(client: httpx.Client, content: str) -> None:
    """Submit a text query."""
    print(coloured("Sending task to Jarvis...", "cyan"))
    res = client.post("/api/tasks", json={"content": content})
    if res.status_code != 200:
        print(coloured(f"Error {res.status_code}: {res.text}", "red"))
        sys.exit(1)
    data = res.json()
    render_response(data)


def cmd_code_review(client: httpx.Client, code: str, lang: str, instruction: str) -> None:
    """Submit code for review."""
    content = f"{instruction}\n\n```{lang}\n{code}\n```"
    print(coloured(f"Sending {lang} code review to Jarvis...", "cyan"))
    res = client.post("/api/tasks", json={"content": content})
    if res.status_code != 200:
        print(coloured(f"Error {res.status_code}: {res.text}", "red"))
        sys.exit(1)
    render_response(res.json())


def cmd_github_repo(client: httpx.Client, owner: str, repo: str, ref: str) -> None:
    """Analyse a GitHub repository."""
    print(coloured(f"Analysing {owner}/{repo} ({ref})...", "cyan"))
    res = client.post("/api/github/analyse-repo", json={"owner": owner, "repo": repo, "ref": ref})
    if res.status_code != 200:
        print(coloured(f"Error {res.status_code}: {res.text}", "red"))
        sys.exit(1)
    render_response(res.json())


def cmd_github_pr(client: httpx.Client, owner: str, repo: str, pr_number: int, post_comment: bool) -> None:
    """Analyse a GitHub PR."""
    print(coloured(f"Reviewing PR #{pr_number} on {owner}/{repo}...", "cyan"))
    res = client.post("/api/github/analyse-pr", json={
        "owner": owner, "repo": repo,
        "pr_number": pr_number, "post_comment": post_comment,
    })
    if res.status_code != 200:
        print(coloured(f"Error {res.status_code}: {res.text}", "red"))
        sys.exit(1)
    render_response(res.json())


def cmd_audit(client: httpx.Client, product_name: str, description: str, ai_output: str | None) -> None:
    """Run an EU AI Act compliance audit."""
    print(coloured(f"Running EU AI Act audit for '{product_name}'...", "cyan"))
    body = {"description": description, "product_name": product_name}
    if ai_output:
        body["ai_output"] = ai_output
    res = client.post("/api/audit", json=body)
    if res.status_code != 200:
        print(coloured(f"Error {res.status_code}: {res.text}", "red"))
        sys.exit(1)
    data = res.json()
    render_audit(data, product_name)


def cmd_history(client: httpx.Client, limit: int) -> None:
    """Show task history."""
    res = client.get(f"/api/tasks?limit={limit}")
    if res.status_code != 200:
        print(coloured(f"Error {res.status_code}: {res.text}", "red"))
        sys.exit(1)
    tasks = res.json()
    if not tasks:
        print(coloured("No tasks yet.", "dim"))
        return
    print_header("Task History")
    for t in tasks:
        v = "PASS" if t.get("verification_passed") == 1 else "FAIL" if t.get("verification_passed") == 0 else "—"
        v_colour = "green" if v == "PASS" else "red" if v == "FAIL" else "dim"
        specs = "—"
        try:
            specs = ", ".join(json.loads(t.get("specialists_used", "[]")))
        except (json.JSONDecodeError, TypeError):
            pass
        print(f"  {coloured(t['id'], 'cyan')}  {t.get('status', '—'):12s}  {coloured(v, v_colour):6s}  {coloured(specs, 'dim')}")


def cmd_task_detail(client: httpx.Client, task_id: str) -> None:
    """Show full detail for a task."""
    res = client.get(f"/api/tasks/{task_id}")
    if res.status_code != 200:
        print(coloured(f"Error {res.status_code}: {res.text}", "red"))
        sys.exit(1)
    render_response(res.json())


def render_response(data: dict) -> None:
    """Pretty-print a task response."""
    print_header("13th Man Report")
    print_badge("Task ID", data.get("task_id", "—"))
    print_badge("Status", data.get("status", "—"),
                "green" if data.get("status") == "completed" else "yellow")

    specs = data.get("specialists_used", [])
    if specs:
        print_badge("Specialists", ", ".join(specs), "magenta")

    # Final answer
    answer = data.get("final_answer", "")
    if answer:
        print_header("Final Answer")
        print(answer)

    # Specialist results
    results = data.get("specialist_results", [])
    if results:
        print_header(f"Specialist Outputs ({len(results)})")
        for r in results:
            name = r.get("agent_name", "Unknown")
            print(f"\n  {coloured(f'--- {name} ---', 'blue')}")
            content = r.get("content", "")
            # Truncate for terminal readability
            if len(content) > 500:
                content = content[:500] + "..."
            for line in content.split("\n"):
                print(f"  {coloured(line, 'dim')}")

    # Verification
    v = data.get("verification")
    if v:
        passed = v.get("passed", False)
        risk = v.get("risk_level", "low")
        print_header("13th Man Verification")
        print_badge("Verdict", "PASSED" if passed else "FAILED",
                    "green" if passed else "red")
        print_badge("Risk Level", str(risk).upper(),
                    "green" if risk == "low" else "yellow" if risk == "medium" else "red")
        if v.get("reasoning"):
            print(f"\n  {coloured(v['reasoning'], 'dim')}")
        if v.get("issues"):
            print(f"\n  {coloured('Issues:', 'red')}")
            for issue in v["issues"]:
                print(f"    - {issue}")
        if v.get("recommendations"):
            print(f"\n  {coloured('Recommendations:', 'yellow')}")
            for rec in v["recommendations"]:
                print(f"    - {rec}")

    # Trace
    trace = data.get("trace", [])
    if trace:
        print_header("Execution Trace")
        for t in trace:
            agent = t.get("agent", "")
            dur = t.get("duration_ms", 0)
            action = t.get("action", "")
            print(f"  {coloured(agent, 'blue'):20s} {action:12s} {coloured(f'{dur}ms', 'dim')}")


def render_audit(data: dict, product_name: str) -> None:
    """Pretty-print an audit result."""
    score = data.get("score", 0)
    score_colour = "green" if score >= 80 else "yellow" if score >= 50 else "red"

    print_header(f"EU AI Act Compliance Audit — {product_name}")
    print_badge("Score", f"{score}/100", score_colour)
    print_badge("Risk Classification", data.get("risk_classification", "—").upper())
    print_badge("Overall Compliance", data.get("overall_compliance", "—").upper(),
                "green" if data.get("overall_compliance") == "compliant" else "red")

    if data.get("summary"):
        print(f"\n  {data['summary']}")

    findings = data.get("findings", [])
    if findings:
        print_header("Findings")
        for f in findings:
            if isinstance(f, dict):
                status = f.get("status", "—")
                s_colour = "green" if status == "pass" else "red" if status == "fail" else "yellow"
                print(f"  {coloured(f.get('checklist_id', ''), 'cyan'):20s} {coloured(status.upper(), s_colour):8s}  {coloured(f.get('evidence', ''), 'dim')}")

    critical = data.get("critical_issues", [])
    if critical:
        print_header("Critical Issues")
        for c in critical:
            print(f"  {coloured('!', 'red')} {c}")

    steps = data.get("next_steps", [])
    if steps:
        print_header("Next Steps")
        for i, s in enumerate(steps, 1):
            print(f"  {i}. {s}")


def main():
    parser = argparse.ArgumentParser(
        prog="13thman",
        description="13th Man CLI — Multi-Agent Cognitive OS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py "Analyse the risks of migrating to microservices"
  python cli.py --mode code --lang python --file app.py
  python cli.py --mode github --owner Kiendas25 --repo thirteenth-man
  python cli.py --mode github --owner Kiendas25 --repo thirteenth-man --pr 1
  python cli.py --mode audit --product "ChatBot Pro" --desc "An AI chatbot for customer support"
  python cli.py --history
  python cli.py --task abc123def456
""",
    )

    parser.add_argument("query", nargs="?", help="Text query to analyse")
    parser.add_argument("--mode", choices=["text", "code", "github", "audit"],
                        default="text", help="Analysis mode (default: text)")
    parser.add_argument("--base-url", default=DEFAULT_BASE,
                        help=f"Server URL (default: {DEFAULT_BASE})")
    parser.add_argument("--token", help="JWT auth token")

    # Code review options
    parser.add_argument("--file", help="File to review (code mode)")
    parser.add_argument("--lang", default="python", help="Language for code review (default: python)")
    parser.add_argument("--instruction", default="Perform a comprehensive code review. Find bugs, security vulnerabilities, performance issues.",
                        help="Review instruction")

    # GitHub options
    parser.add_argument("--owner", help="GitHub repo owner")
    parser.add_argument("--repo", help="GitHub repo name")
    parser.add_argument("--ref", default="main", help="Git ref/branch (default: main)")
    parser.add_argument("--pr", type=int, help="PR number to review")
    parser.add_argument("--post-comment", action="store_true", help="Post review as PR comment")

    # Audit options
    parser.add_argument("--product", default="AI System", help="Product name for audit")
    parser.add_argument("--desc", help="System description for audit")
    parser.add_argument("--ai-output", help="AI output to audit")

    # History
    parser.add_argument("--history", action="store_true", help="Show task history")
    parser.add_argument("--task", help="Show details for a specific task ID")
    parser.add_argument("--limit", type=int, default=10, help="Number of history items (default: 10)")

    args = parser.parse_args()
    client = make_client(args.base_url, args.token)

    # Check server is reachable
    try:
        client.get("/api/settings")
    except httpx.ConnectError:
        print(coloured(f"Cannot connect to {args.base_url}", "red"))
        print(coloured("Make sure the server is running: python main.py", "dim"))
        sys.exit(1)

    if args.history:
        cmd_history(client, args.limit)
    elif args.task:
        cmd_task_detail(client, args.task)
    elif args.mode == "code":
        if args.file:
            try:
                with open(args.file, "r") as f:
                    code = f.read()
            except FileNotFoundError:
                print(coloured(f"File not found: {args.file}", "red"))
                sys.exit(1)
        elif args.query:
            code = args.query
        else:
            print(coloured("Provide code with --file or as argument", "red"))
            sys.exit(1)
        cmd_code_review(client, code, args.lang, args.instruction)
    elif args.mode == "github":
        if not args.owner or not args.repo:
            print(coloured("--owner and --repo required for github mode", "red"))
            sys.exit(1)
        if args.pr:
            cmd_github_pr(client, args.owner, args.repo, args.pr, args.post_comment)
        else:
            cmd_github_repo(client, args.owner, args.repo, args.ref)
    elif args.mode == "audit":
        if not args.desc:
            print(coloured("--desc required for audit mode", "red"))
            sys.exit(1)
        cmd_audit(client, args.product, args.desc, args.ai_output)
    elif args.query:
        cmd_query(client, args.query)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
