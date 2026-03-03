# OpenRouter + LangFuse Observability Setup

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
