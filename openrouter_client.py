import os
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
