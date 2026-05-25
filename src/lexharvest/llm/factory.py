from pydantic_ai.models import Model


def build_model(provider: str, model_name: str, base_url: str | None = None) -> tuple[Model, bool]:
    """Returns (model, use_native_output).

    Ollama via OpenAI-compat needs NativeOutput (json_schema) because tool-call
    routing differs. OpenAI/Anthropic use tool calls (PydanticAI default).
    """

    if provider == "ollama":
        from openai import AsyncOpenAI
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        client = AsyncOpenAI(base_url=base_url or "http://localhost:11434/v1", api_key="ollama")

        model = OpenAIChatModel(model_name, provider=OpenAIProvider(openai_client=client))
        return model, True

    elif "openai" in provider:
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        return OpenAIChatModel(model_name, provider=OpenAIProvider()), False

    elif "anthropic" in provider:
        from anthropic import AsyncAnthropic
        from pydantic_ai.models.anthropic import AnthropicModel
        from pydantic_ai.providers.anthropic import AnthropicProvider

        return AnthropicModel(
            model_name, provider=AnthropicProvider(anthropic_client=AsyncAnthropic())
        ), False

    else:
        raise ValueError(
            f"Unknown LLM provider: '{provider}'. Expected ollama | openai | anthropic"
        )
