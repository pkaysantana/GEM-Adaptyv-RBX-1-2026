#!/usr/bin/env python3
"""
Observability Analysis Dashboard
Real-time monitoring and analysis of agent behavior.
"""

import json
import pandas as pd
from langfuse_integration import LangFuseTracker
from openrouter_client import OpenRouterClient
import structlog
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from datetime import datetime, timedelta

logger = structlog.get_logger()
console = Console()

class ObservabilityDashboard:
    """Dashboard for analyzing agent behavior patterns."""

    def __init__(self):
        self.tracker = LangFuseTracker()
        self.client = OpenRouterClient()

    def analyze_recent_activity(self, hours: int = 24):
        """Analyze recent agent activity patterns."""

        console.print(f"\n[bold]Agent Activity Analysis - Last {hours} Hours[/bold]")
        console.print("=" * 60)

        # Get performance analysis
        analysis = self.tracker.analyze_performance_patterns()

        if "error" in analysis:
            console.print(f"[red]Error analyzing patterns: {analysis['error']}[/red]")
            return

        # Display trace summary
        trace_table = Table(title="Trace Summary")
        trace_table.add_column("Trace Type", style="cyan")
        trace_table.add_column("Count", justify="right", style="magenta")

        for trace_type, count in analysis.get("trace_types", {}).items():
            trace_table.add_row(trace_type, str(count))

        console.print(trace_table)

        # Display errors if any
        if analysis.get("common_errors"):
            console.print("\n[red]Recent Errors:[/red]")
            for error in analysis["common_errors"][:5]:
                console.print(f"  • Trace {error['trace_id']}: {error.get('error_info', 'Unknown error')}")
        else:
            console.print("\n[green]No errors in recent activity[/green]")

        return analysis

    def identify_confusion_patterns(self):
        """Identify patterns where the agent gets confused."""

        console.print("\n[bold]Confusion Pattern Analysis[/bold]")
        console.print("=" * 40)

        # This would analyze LangFuse data for:
        # - Long reasoning traces without clear conclusions
        # - Repeated tool calls with similar inputs
        # - Error patterns in specific contexts
        # - Unclear or contradictory outputs

        patterns = {
            "tool_repetition": "Multiple calls to same tool with similar inputs",
            "long_reasoning": "Reasoning traces exceeding normal length",
            "error_clusters": "Multiple errors in similar contexts",
            "unclear_outputs": "Outputs with low confidence indicators"
        }

        for pattern_type, description in patterns.items():
            console.print(f"  • [yellow]{pattern_type}[/yellow]: {description}")

        console.print("\n[dim]Detailed pattern analysis requires LangFuse trace data[/dim]")

    def analyze_system_prompt_effectiveness(self):
        """Analyze system prompt effectiveness based on traces."""

        console.print("\n[bold]System Prompt Analysis[/bold]")
        console.print("=" * 35)

        # Analyze patterns that suggest prompt issues
        prompt_issues = [
            "Agent frequently asks for clarification",
            "Inconsistent tool usage patterns",
            "Reasoning traces show uncertainty",
            "Multiple attempts to complete simple tasks",
            "Tool calls don't match stated intentions"
        ]

        console.print("[yellow]Potential prompt optimization areas:[/yellow]")
        for i, issue in enumerate(prompt_issues, 1):
            console.print(f"  {i}. {issue}")

        recommendations = [
            "Add specific examples for common scenarios",
            "Clarify tool usage guidelines",
            "Improve error handling instructions",
            "Add confidence indicators to outputs",
            "Streamline decision-making framework"
        ]

        console.print("\n[green]Optimization recommendations:[/green]")
        for i, rec in enumerate(recommendations, 1):
            console.print(f"  {i}. {rec}")

    def generate_improvement_report(self):
        """Generate comprehensive improvement report."""

        console.print("\n[bold]Agent Improvement Report[/bold]")
        console.print("=" * 40)

        # Analyze recent activity
        activity = self.analyze_recent_activity()

        # Generate report
        report = {
            "timestamp": datetime.now().isoformat(),
            "analysis_summary": activity,
            "improvement_areas": [
                "Reduce reasoning complexity for simple tasks",
                "Improve tool selection accuracy",
                "Optimize prompt clarity",
                "Add better error recovery"
            ],
            "next_steps": [
                "Review top 10 confused interactions in LangFuse",
                "Identify most common error patterns",
                "Test prompt modifications",
                "Monitor improvement metrics"
            ]
        }

        # Save report
        with open(f"improvement_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json", 'w') as f:
            json.dump(report, f, indent=2, default=str)

        console.print("[green]Improvement report generated and saved[/green]")
        return report

def main():
    """Run observability analysis."""

    dashboard = ObservabilityDashboard()

    try:
        # Run analysis
        dashboard.analyze_recent_activity()
        dashboard.identify_confusion_patterns()
        dashboard.analyze_system_prompt_effectiveness()

        # Generate report
        report = dashboard.generate_improvement_report()

        console.print("\n[bold green]Observability analysis complete![/bold green]")
        console.print("Review LangFuse dashboard for detailed traces")

    except Exception as e:
        console.print(f"[red]Dashboard error: {e}[/red]")
        logger.error("Dashboard analysis failed", error=str(e))

if __name__ == "__main__":
    main()
