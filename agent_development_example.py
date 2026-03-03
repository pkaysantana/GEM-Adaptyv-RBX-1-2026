#!/usr/bin/env python3
"""
Agent Development Example with Full Observability
Demonstrates practical usage of OpenRouter + LangFuse monitoring.
"""

from langfuse_integration import LangFuseTracker, track_with_langfuse
from openrouter_client import OpenRouterClient
import time
import structlog
from typing import Dict, List

logger = structlog.get_logger()

class ObservableAgent:
    """Example agent with comprehensive observability."""

    def __init__(self):
        self.tracker = LangFuseTracker()
        self.client = OpenRouterClient()
        self.conversation_history = []

    @track_with_langfuse("protein_analysis")
    def analyze_protein_sequence(self, sequence: str) -> Dict:
        """Analyze protein sequence with full observability."""

        start_time = time.time()

        # Track the analysis request
        self.tracker.track_agent_interaction(
            interaction_type="sequence_analysis_request",
            input_data={"sequence": sequence[:50] + "...", "length": len(sequence)},
            output_data={},  # Will update after analysis
            metadata={"analysis_type": "protein_properties"}
        )

        try:
            # Create analysis prompt
            analysis_prompt = f"""Analyze this protein sequence and provide insights:

Sequence: {sequence}

Please provide:
1. Length and basic composition
2. Predicted function based on composition
3. Potential binding characteristics
4. Structural predictions

Be concise but thorough."""

            # Track reasoning process
            reasoning_steps = [
                "Received protein sequence for analysis",
                f"Sequence length: {len(sequence)} amino acids",
                "Preparing comprehensive analysis prompt",
                "Sending to LLM for analysis"
            ]

            # Make API call through OpenRouter
            messages = [
                {"role": "system", "content": "You are a expert protein biochemist. Provide detailed but concise analysis."},
                {"role": "user", "content": analysis_prompt}
            ]

            response = self.client.create_completion(
                model="anthropic/claude-3-haiku",
                messages=messages,
                max_tokens=500
            )

            analysis_result = response.choices[0].message.content
            execution_time = time.time() - start_time

            # Track the successful analysis
            self.tracker.track_agent_interaction(
                interaction_type="sequence_analysis_complete",
                input_data={"sequence_length": len(sequence)},
                output_data={"analysis": analysis_result[:200] + "..."},
                metadata={
                    "success": True,
                    "execution_time": execution_time,
                    "tokens_used": response.usage.total_tokens if response.usage else None
                }
            )

            # Track reasoning trace
            reasoning_steps.extend([
                "Received comprehensive analysis from LLM",
                "Analysis covers composition, function, and structure",
                "Successfully completed protein analysis"
            ])

            self.tracker.track_reasoning_trace(
                reasoning_steps=reasoning_steps,
                decision_points=[
                    {"step": "model_selection", "decision": "claude-3-haiku", "reasoning": "Good balance of speed and quality for analysis"},
                    {"step": "prompt_design", "decision": "structured_analysis", "reasoning": "Ensures comprehensive coverage"}
                ],
                final_decision="Provide detailed protein analysis"
            )

            return {
                "success": True,
                "analysis": analysis_result,
                "execution_time": execution_time,
                "sequence_length": len(sequence)
            }

        except Exception as e:
            # Track the error
            self.tracker.track_agent_interaction(
                interaction_type="sequence_analysis_error",
                input_data={"sequence_length": len(sequence)},
                output_data={"error": str(e)},
                metadata={"success": False, "execution_time": time.time() - start_time}
            )

            logger.error("Protein analysis failed", error=str(e), sequence_length=len(sequence))
            return {"success": False, "error": str(e)}

    @track_with_langfuse("tool_selection")
    def select_optimization_tool(self, task_description: str) -> str:
        """Demonstrate tool selection with observability."""

        start_time = time.time()

        # Available tools
        available_tools = {
            "rfdiffusion": "Generate novel protein structures",
            "proteinmpnn": "Design protein sequences",
            "esmfold": "Predict protein structure from sequence",
            "molecular_docking": "Predict protein-ligand interactions"
        }

        # Track tool selection process
        reasoning_steps = [
            f"Task received: {task_description}",
            f"Available tools: {list(available_tools.keys())}",
            "Analyzing task requirements for optimal tool selection"
        ]

        # Simple tool selection logic (in real scenario, this would be more sophisticated)
        if "structure" in task_description.lower() and "predict" in task_description.lower():
            selected_tool = "esmfold"
            reasoning = "Task involves structure prediction"
        elif "design" in task_description.lower() or "generate" in task_description.lower():
            selected_tool = "rfdiffusion"
            reasoning = "Task involves generative design"
        elif "binding" in task_description.lower() or "docking" in task_description.lower():
            selected_tool = "molecular_docking"
            reasoning = "Task involves binding analysis"
        else:
            selected_tool = "proteinmpnn"
            reasoning = "Default to sequence design tool"

        execution_time = time.time() - start_time

        # Track tool selection
        self.tracker.track_tool_usage(
            tool_name="tool_selector",
            tool_input={"task": task_description, "available_tools": list(available_tools.keys())},
            tool_output={"selected_tool": selected_tool, "reasoning": reasoning},
            execution_time=execution_time
        )

        reasoning_steps.extend([
            f"Selected tool: {selected_tool}",
            f"Reasoning: {reasoning}",
            "Tool selection completed successfully"
        ])

        # Track reasoning
        self.tracker.track_reasoning_trace(
            reasoning_steps=reasoning_steps,
            decision_points=[{
                "step": "tool_analysis",
                "decision": selected_tool,
                "reasoning": reasoning,
                "alternatives": [tool for tool in available_tools.keys() if tool != selected_tool]
            }],
            final_decision=f"Use {selected_tool} for: {task_description}"
        )

        return selected_tool

    def demonstrate_common_patterns(self):
        """Demonstrate patterns that observability helps identify."""

        print("Demonstrating observable agent patterns...")

        # Pattern 1: Successful task completion
        result1 = self.analyze_protein_sequence("MKVLFKFWYLHVSGTKRDEAILVFMKNQP")
        print(f"Analysis 1 success: {result1['success']}")

        # Pattern 2: Tool selection reasoning
        tool1 = self.select_optimization_tool("predict protein structure from sequence")
        tool2 = self.select_optimization_tool("design new protein binder")
        tool3 = self.select_optimization_tool("analyze binding affinity")

        print(f"Tool selections: {tool1}, {tool2}, {tool3}")

        # Pattern 3: Multiple attempts (shows persistence/confusion patterns)
        for i in range(3):
            tool = self.select_optimization_tool("optimize something complex")
            print(f"Attempt {i+1}: {tool}")

        print("Pattern demonstration complete - check LangFuse for traces!")

def run_observability_demo():
    """Run demonstration of observability features."""

    print("OpenRouter + LangFuse Observability Demo")
    print("=" * 42)

    try:
        agent = ObservableAgent()
        agent.demonstrate_common_patterns()

        print("\nDemo complete! Check your LangFuse dashboard at:")
        print("https://cloud.langfuse.com")

        print("\nLook for these trace patterns:")
        print("1. sequence_analysis_* traces - Full analysis workflows")
        print("2. tool_selection traces - Decision-making processes")
        print("3. Reasoning traces - Step-by-step logic")
        print("4. Tool usage spans - Individual function calls")

        print("\nAnalyze for:")
        print("- Long reasoning traces (potential confusion)")
        print("- Repeated similar tool calls (inefficiency)")
        print("- Error patterns in specific contexts")
        print("- Inconsistent decision-making")

    except Exception as e:
        print(f"Demo failed - likely missing API keys: {e}")
        print("Update .env.observability with your OpenRouter and LangFuse keys")

if __name__ == "__main__":
    run_observability_demo()