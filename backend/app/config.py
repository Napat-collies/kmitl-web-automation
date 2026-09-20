"""Settings, read from environment (.env supported via pydantic-settings)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- LLM (the class proxy; your key comes from the course portal: Profile -> API key) ---
    llm_base_url: str = "https://llm.nat-d.uk/v1"
    llm_api_key: str = ""            # required to run the agent
    model: str = "gemma-4-E4B-it"

    # --- Web search (https://tavily.com -> free dev key) ---
    tavily_api_key: str = ""         # required for the search tool

    # --- agent guardrails ---
    max_steps: int = 6               # bounded tool-calling loop
    fetch_char_budget: int = 4000    # truncate extracted page text before spending tokens
    request_timeout: float = 15.0

    def require_llm(self) -> None:
        if not self.llm_api_key:
            raise RuntimeError("LLM_API_KEY is not set (get one from the course portal → Profile → API key).")

    def require_tavily(self) -> None:
        if not self.tavily_api_key:
            raise RuntimeError("TAVILY_API_KEY is not set (free dev key at https://tavily.com).")


@lru_cache
def get_settings() -> Settings:
    return Settings()
