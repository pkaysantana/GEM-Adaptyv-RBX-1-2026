import os
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
