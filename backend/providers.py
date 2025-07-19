import os
import requests
import json
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Cost rates per 1K tokens
COST_RATES = {
    "openai:gpt-4-1106-preview": {"input": 0.01, "output": 0.03},
    "openai:gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
    "openai:gpt-4.1-mini": {"input": 0.001, "output": 0.002},
    "anthropic:claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
    "anthropic:claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
}


class ProviderError(Exception):
    pass


class OpenAIProvider:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = "https://api.openai.com/v1"

    async def chat_completion(
        self, messages: list, model: str = "gpt-4-1106-preview"
    ) -> Dict[str, Any]:
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }

            # Filter out any messages with 'tool' role to prevent OpenAI API errors
            filtered_messages = [msg for msg in messages if msg.get("role") != "tool"]
            if len(filtered_messages) != len(messages):
                logger.info(
                    f"Filtered out {len(messages) - len(filtered_messages)} messages with 'tool' role"
                )

            payload = {
                "model": model,
                "messages": filtered_messages,
                "temperature": 0.7,
                "max_tokens": 2000,
            }

            # Log the request for debugging
            logger.info(f"OpenAI API Request - Model: {model}")
            logger.info(
                f"OpenAI API Request - Message count: {len(filtered_messages)} (filtered from {len(messages)})"
            )
            logger.info("=== ALL MESSAGES ===")
            for i, msg in enumerate(filtered_messages):
                logger.info(
                    f"Message {i}: role={msg.get('role')}, content_length={len(str(msg.get('content', '')))}"
                )
                # Log if there are any tool_calls or tool_call_id fields
                if "tool_calls" in msg:
                    logger.info(f"Message {i} has tool_calls: {msg.get('tool_calls')}")
                if "tool_call_id" in msg:
                    logger.info(
                        f"Message {i} has tool_call_id: {msg.get('tool_call_id')}"
                    )
                if len(str(msg.get("content", ""))) > 500:
                    logger.info(
                        f"Message {i} content preview: {str(msg.get('content', ''))[:500]}..."
                    )
                else:
                    logger.info(f"Message {i} content: {msg.get('content', '')}")
            logger.info("=== END MESSAGES ===")

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60,
            )

            try:
                response.raise_for_status()
                data = response.json()
            except requests.exceptions.HTTPError as e:
                logger.error(f"OpenAI API HTTP Error: {e}")
                logger.error(f"Response status: {response.status_code}")
                logger.error(f"Response headers: {response.headers}")
                try:
                    error_data = response.json()
                    logger.error(f"Response body: {error_data}")
                except:
                    logger.error(f"Response text: {response.text}")
                raise Exception(f"OpenAI API error: {e}")

            message = data["choices"][0]["message"]
            usage = data["usage"]
            prompt_tokens = usage["prompt_tokens"]
            completion_tokens = usage["completion_tokens"]
            content = message["content"]

            # Calculate cost
            cost_key = f"openai:{model}"
            if cost_key in COST_RATES:
                rates = COST_RATES[cost_key]
                cost = (
                    prompt_tokens * rates["input"] + completion_tokens * rates["output"]
                ) / 1000
            else:
                cost = 0.0

            return {
                "message": {"role": "assistant", "content": content},
                "usage": {
                    "tokens_in": prompt_tokens,
                    "tokens_out": completion_tokens,
                    "cost_usd": cost,
                },
            }
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise ProviderError(f"OpenAI API error: {str(e)}")


class AnthropicProvider:
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.base_url = "https://api.anthropic.com/v1"

    async def chat_completion(
        self, messages: list, model: str = "claude-3-haiku-20240307"
    ) -> Dict[str, Any]:
        try:
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            }

            # Convert messages to Anthropic format
            system_message = ""
            anthropic_messages = []

            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    anthropic_messages.append(
                        {"role": msg["role"], "content": msg["content"]}
                    )

            payload = {
                "model": model,
                "max_tokens": 2000,
                "temperature": 0.7,
                "messages": anthropic_messages,
            }

            if system_message:
                payload["system"] = system_message

            response = requests.post(
                f"{self.base_url}/messages", headers=headers, json=payload, timeout=60
            )

            response.raise_for_status()
            data = response.json()

            # Calculate cost
            cost_key = f"anthropic:{model}"
            if cost_key in COST_RATES:
                rates = COST_RATES[cost_key]
                cost = (
                    data["usage"]["input_tokens"] * rates["input"]
                    + data["usage"]["output_tokens"] * rates["output"]
                ) / 1000
            else:
                cost = 0.0

            return {
                "message": {"role": "assistant", "content": data["content"][0]["text"]},
                "usage": {
                    "tokens_in": data["usage"]["input_tokens"],
                    "tokens_out": data["usage"]["output_tokens"],
                    "cost_usd": cost,
                },
            }
        except Exception as e:
            logger.error(f"Anthropic API error: {str(e)}")
            raise ProviderError(f"Anthropic API error: {str(e)}")


class ProviderManager:
    def __init__(self):
        self.providers = {"openai": OpenAIProvider(), "anthropic": AnthropicProvider()}

    async def get_completion(
        self, provider: str, messages: list, model: str = None
    ) -> Dict[str, Any]:
        logger.info(
            f"ProviderManager.get_completion called with provider={provider}, model={model}"
        )

        if provider not in self.providers:
            raise ProviderError(f"Unknown provider: {provider}")

        provider_instance = self.providers[provider]

        # Use default model if not specified
        if model is None:
            model = "gpt-4o-mini" if provider == "openai" else "claude-3-haiku-20240307"
            logger.info(f"Using default model: {model} for provider: {provider}")

        logger.info(f"Calling {provider} provider with model {model}")
        return await provider_instance.chat_completion(messages, model)
