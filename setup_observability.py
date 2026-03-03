#!/usr/bin/env python3
"""
OpenRouter + LangFuse Observability Setup
Complete monitoring infrastructure for agent development.
"""

import os
import json
from pathlib import Path

def setup_environment():
    """Setup environment configuration for OpenRouter and LangFuse."""

    print("OpenRouter + LangFuse Observability Setup")
    print("=" * 42)

    # Create environment template
    env_template = """# OpenRouter Configuration
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_HTTP_REFERER=http://localhost:3000
OPENROUTER_X_TITLE=Claude-Code-Agent-Analysis

# LangFuse Configuration (Free Plan)
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key_here
LANGFUSE_SECRET_KEY=your_langfuse_secret_key_here
LANGFUSE_HOST=https://cloud.langfuse.com

# Agent Monitoring Settings
ENABLE_OBSERVABILITY=true
LOG_LEVEL=DEBUG
TRACE_ALL_CALLS=true
ANALYZE_REASONING=true
MONITOR_TOOL_USAGE=true
"""

    # Write environment file
    with open('.env.observability', 'w') as f:
        f.write(env_template)

    print("Created .env.observability template")
    print("Please update with your actual API keys")

    # Create requirements file
    requirements = """# Observability Dependencies
openai>=1.3.0
langfuse>=2.0.0
python-dotenv>=1.0.0
requests>=2.31.0

# Data Analysis
pandas>=2.0.0
numpy>=1.24.0

# Monitoring & Logging
structlog>=23.2.0
rich>=13.0.0
"""

    with open('requirements_observability.txt', 'w') as f:
        f.write(requirements)

    print("Created requirements_observability.txt")

def create_openrouter_client():
    """Create OpenRouter client configuration."""

    client_config = '''import os
from openai import OpenAI
from dotenv import load_dotenv
import structlog

load_dotenv('.env.observability')

logger = structlog.get_logger()

class OpenRouterClient:
    """OpenRouter client with built-in observability."""

    def __init__(self):
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment")

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
            default_headers={
                "HTTP-Referer": os.getenv('OPENROUTER_HTTP_REFERER', ''),
                "X-Title": os.getenv('OPENROUTER_X_TITLE', 'Agent-Observability'),
            }
        )

        logger.info("OpenRouter client initialized", api_key_prefix=self.api_key[:8])

    def create_completion(self, model="anthropic/claude-3-haiku",
                         messages=None, **kwargs):
        """Create completion with automatic logging."""

        logger.info("OpenRouter API call initiated",
                   model=model,
                   message_count=len(messages) if messages else 0)

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages or [],
                **kwargs
            )

            logger.info("OpenRouter API call completed",
                       model=model,
                       usage=response.usage._asdict() if response.usage else None)

            return response

        except Exception as e:
            logger.error("OpenRouter API call failed",
                        model=model,
                        error=str(e))
            raise

# Example usage
if __name__ == "__main__":
    client = OpenRouterClient()

    test_messages = [
        {"role": "user", "content": "What is observability in AI agents?"}
    ]

    response = client.create_completion(
        model="anthropic/claude-3-haiku",
        messages=test_messages,
        max_tokens=100
    )

    print("Test response:", response.choices[0].message.content)
'''

    with open('openrouter_client.py', 'w') as f:
        f.write(client_config)

    print("Created openrouter_client.py")

def create_langfuse_integration():
    """Create LangFuse integration for trace analysis."""

    langfuse_config = '''import os
from langfuse import Langfuse
from langfuse.decorators import observe, langfuse_context
from dotenv import load_dotenv
import json
import structlog
from datetime import datetime
from typing import Dict, List, Any

load_dotenv('.env.observability')

logger = structlog.get_logger()

class LangFuseTracker:
    """LangFuse integration for comprehensive agent monitoring."""

    def __init__(self):
        self.public_key = os.getenv('LANGFUSE_PUBLIC_KEY')
        self.secret_key = os.getenv('LANGFUSE_SECRET_KEY')
        self.host = os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')

        if not all([self.public_key, self.secret_key]):
            raise ValueError("LangFuse keys not found in environment")

        self.langfuse = Langfuse(
            public_key=self.public_key,
            secret_key=self.secret_key,
            host=self.host
        )

        logger.info("LangFuse tracker initialized",
                   host=self.host,
                   public_key_prefix=self.public_key[:8])

    @observe()
    def track_agent_interaction(self, interaction_type: str,
                              input_data: Dict,
                              output_data: Dict,
                              metadata: Dict = None):
        """Track agent interactions with detailed context."""

        langfuse_context.update_current_trace(
            name=f"agent_{interaction_type}",
            input=input_data,
            output=output_data,
            metadata={
                "timestamp": datetime.now().isoformat(),
                "interaction_type": interaction_type,
                **(metadata or {})
            }
        )

        logger.info("Interaction tracked in LangFuse",
                   interaction_type=interaction_type,
                   input_size=len(str(input_data)),
                   output_size=len(str(output_data)))

    @observe()
    def track_tool_usage(self, tool_name: str,
                        tool_input: Dict,
                        tool_output: Any,
                        execution_time: float = None):
        """Track tool usage patterns."""

        langfuse_context.update_current_span(
            name=f"tool_{tool_name}",
            input=tool_input,
            output={"result": str(tool_output)[:1000]},  # Truncate large outputs
            metadata={
                "tool_name": tool_name,
                "execution_time_ms": execution_time * 1000 if execution_time else None,
                "timestamp": datetime.now().isoformat()
            }
        )

        logger.info("Tool usage tracked",
                   tool_name=tool_name,
                   execution_time_ms=execution_time * 1000 if execution_time else None)

    @observe()
    def track_reasoning_trace(self, reasoning_steps: List[str],
                             decision_points: List[Dict],
                             final_decision: str):
        """Track reasoning patterns for analysis."""

        langfuse_context.update_current_trace(
            name="reasoning_trace",
            input={"reasoning_steps": reasoning_steps},
            output={"final_decision": final_decision},
            metadata={
                "decision_points": decision_points,
                "reasoning_length": len(reasoning_steps),
                "timestamp": datetime.now().isoformat()
            }
        )

        logger.info("Reasoning trace recorded",
                   steps_count=len(reasoning_steps),
                   decision_points_count=len(decision_points))

    def analyze_performance_patterns(self, session_id: str = None):
        """Retrieve and analyze performance patterns from LangFuse."""

        try:
            # Get traces for analysis
            traces = self.langfuse.get_traces(
                user_id=session_id,
                limit=100
            )

            analysis = {
                "total_traces": len(traces.data),
                "trace_types": {},
                "common_errors": [],
                "performance_metrics": {}
            }

            for trace in traces.data:
                # Analyze trace patterns
                trace_name = trace.name or "unknown"
                analysis["trace_types"][trace_name] = analysis["trace_types"].get(trace_name, 0) + 1

                # Check for errors
                if hasattr(trace, 'level') and trace.level == 'ERROR':
                    analysis["common_errors"].append({
                        "trace_id": trace.id,
                        "error_info": trace.output if hasattr(trace, 'output') else None
                    })

            logger.info("Performance analysis completed",
                       total_traces=analysis["total_traces"],
                       trace_types=len(analysis["trace_types"]))

            return analysis

        except Exception as e:
            logger.error("Failed to analyze performance patterns", error=str(e))
            return {"error": str(e)}

# Decorator for easy function tracking
def track_with_langfuse(interaction_type: str):
    """Decorator to automatically track function calls."""
    def decorator(func):
        @observe()
        def wrapper(*args, **kwargs):
            tracker = LangFuseTracker()

            input_data = {
                "function": func.__name__,
                "args": [str(arg)[:100] for arg in args],  # Truncate long args
                "kwargs": {k: str(v)[:100] for k, v in kwargs.items()}
            }

            try:
                result = func(*args, **kwargs)

                output_data = {
                    "result": str(result)[:500],  # Truncate large results
                    "success": True
                }

                tracker.track_agent_interaction(
                    interaction_type=interaction_type,
                    input_data=input_data,
                    output_data=output_data
                )

                return result

            except Exception as e:
                output_data = {
                    "error": str(e),
                    "success": False
                }

                tracker.track_agent_interaction(
                    interaction_type=interaction_type,
                    input_data=input_data,
                    output_data=output_data
                )

                raise

        return wrapper
    return decorator

# Example usage
if __name__ == "__main__":
    tracker = LangFuseTracker()

    # Test interaction tracking
    tracker.track_agent_interaction(
        interaction_type="test",
        input_data={"message": "Hello, world!"},
        output_data={"response": "Hello! How can I help you?"}
    )

    print("LangFuse tracking test completed")
'''

    with open('langfuse_integration.py', 'w') as f:
        f.write(langfuse_config)

    print("Created langfuse_integration.py")

def create_analysis_dashboard():
    """Create analysis dashboard for monitoring insights."""

    dashboard_code = '''#!/usr/bin/env python3
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

        console.print(f"\\n[bold]Agent Activity Analysis - Last {hours} Hours[/bold]")
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
            console.print("\\n[red]Recent Errors:[/red]")
            for error in analysis["common_errors"][:5]:
                console.print(f"  • Trace {error['trace_id']}: {error.get('error_info', 'Unknown error')}")
        else:
            console.print("\\n[green]No errors in recent activity[/green]")

        return analysis

    def identify_confusion_patterns(self):
        """Identify patterns where the agent gets confused."""

        console.print("\\n[bold]Confusion Pattern Analysis[/bold]")
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

        console.print("\\n[dim]Detailed pattern analysis requires LangFuse trace data[/dim]")

    def analyze_system_prompt_effectiveness(self):
        """Analyze system prompt effectiveness based on traces."""

        console.print("\\n[bold]System Prompt Analysis[/bold]")
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

        console.print("\\n[green]Optimization recommendations:[/green]")
        for i, rec in enumerate(recommendations, 1):
            console.print(f"  {i}. {rec}")

    def generate_improvement_report(self):
        """Generate comprehensive improvement report."""

        console.print("\\n[bold]Agent Improvement Report[/bold]")
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

        console.print("\\n[bold green]Observability analysis complete![/bold green]")
        console.print("Review LangFuse dashboard for detailed traces")

    except Exception as e:
        console.print(f"[red]Dashboard error: {e}[/red]")
        logger.error("Dashboard analysis failed", error=str(e))

if __name__ == "__main__":
    main()
'''

    with open('observability_dashboard.py', 'w') as f:
        f.write(dashboard_code)

    print("Created observability_dashboard.py")

def create_setup_instructions():
    """Create setup and usage instructions."""

    instructions = """# OpenRouter + LangFuse Observability Setup

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements_observability.txt
   ```

2. **Get API Keys**

   **OpenRouter:**
   - Sign up at https://openrouter.ai/
   - Get API key from dashboard
   - Add credits for usage

   **LangFuse (Free Plan):**
   - Sign up at https://langfuse.com/
   - Create new project
   - Copy public/secret keys

3. **Configure Environment**
   ```bash
   cp .env.observability .env
   # Edit .env with your actual API keys
   ```

4. **Test Setup**
   ```bash
   python openrouter_client.py
   python langfuse_integration.py
   ```

5. **Run Dashboard**
   ```bash
   python observability_dashboard.py
   ```

## Usage Patterns

### Track Agent Interactions
```python
from langfuse_integration import LangFuseTracker

tracker = LangFuseTracker()

# Track any agent interaction
tracker.track_agent_interaction(
    interaction_type="protein_optimization",
    input_data={"sequence": "MKVL...", "task": "optimize_binding"},
    output_data={"optimized_sequence": "FWYL...", "score": 0.85}
)
```

### Track Tool Usage
```python
# Track tool calls automatically
@track_with_langfuse("tool_usage")
def my_optimization_function(sequence):
    # Your optimization logic
    return optimized_sequence
```

### Monitor API Calls
```python
from openrouter_client import OpenRouterClient

client = OpenRouterClient()
response = client.create_completion(
    model="anthropic/claude-3.5-sonnet",
    messages=[{"role": "user", "content": "Analyze this protein sequence"}]
)
```

## Analysis Workflow

1. **Run Tasks** - Let your agent work normally
2. **Review LangFuse** - Check traces in web dashboard
3. **Identify Patterns** - Look for confusion, errors, inefficiencies
4. **Optimize Prompts** - Based on actual behavior data
5. **Test Changes** - Monitor improvement metrics

## Key Metrics to Monitor

- **Reasoning Trace Length** - Are responses unnecessarily complex?
- **Tool Call Patterns** - Are tools used efficiently?
- **Error Frequency** - What causes failures?
- **Response Quality** - Are outputs consistent?
- **Token Usage** - Are costs optimized?

## LangFuse Dashboard Features

- **Traces** - Full conversation flows
- **Spans** - Individual function/tool calls
- **Scores** - Quality metrics and feedback
- **Users** - Session-based analysis
- **Playground** - Test prompt variations

## Common Issues to Look For

1. **Confused Reasoning**
   - Long, circular reasoning traces
   - Multiple attempts at simple tasks
   - Inconsistent logic patterns

2. **Tool Misuse**
   - Wrong tools for tasks
   - Repeated failed tool calls
   - Missing context in tool inputs

3. **Prompt Issues**
   - Frequent clarification requests
   - Ignoring system instructions
   - Inconsistent behavior patterns

## Next Steps

1. Set up the environment with your API keys
2. Run a few protein optimization tasks
3. Review the traces in LangFuse web dashboard
4. Identify top 3 confusion patterns
5. Modify prompts/system instructions
6. Monitor improvement with continued tracking
"""

    with open('OBSERVABILITY_SETUP.md', 'w') as f:
        f.write(instructions)

    print("Created OBSERVABILITY_SETUP.md")

def main():
    """Main setup function."""

    print("Setting up comprehensive observability infrastructure...")

    setup_environment()
    create_openrouter_client()
    create_langfuse_integration()
    create_analysis_dashboard()
    create_setup_instructions()

    print("\nObservability setup complete!")
    print("\nNext steps:")
    print("1. Update .env.observability with your API keys")
    print("2. Install dependencies: pip install -r requirements_observability.txt")
    print("3. Test setup: python openrouter_client.py")
    print("4. Run dashboard: python observability_dashboard.py")
    print("5. Review traces in LangFuse web dashboard")

if __name__ == "__main__":
    main()