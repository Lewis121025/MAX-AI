"""项目配置中心：基于 Pydantic 的设置管理。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import AliasChoices, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """从环境变量或 .env 文件加载的应用设置。"""

    environment: str = Field(default="development", validation_alias=AliasChoices("APP_ENV", "ENVIRONMENT"))
    log_level: str = Field(default="INFO", validation_alias=AliasChoices("LOG_LEVEL", "APP_LOG_LEVEL"))

    # LLM API 配置（优先使用 OpenRouter）
    openrouter_api_key: Optional[str] = Field(default=None, validation_alias=AliasChoices("OPENROUTER_API_KEY", "OPENROUTER_TOKEN"))
    gemini_api_key: Optional[str] = Field(default=None, validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_GEMINI_API_KEY"))
    openai_api_key: Optional[str] = Field(default=None, validation_alias=AliasChoices("OPENAI_API_KEY", "LLM_API_KEY"))
    
    # 工具 API
    e2b_api_key: Optional[str] = Field(default=None, validation_alias=AliasChoices("E2B_API_KEY", "E2B_TOKEN"))
    tavily_api_key: Optional[str] = Field(default=None, validation_alias=AliasChoices("TAVILY_API_KEY", "TAVILY_TOKEN"))
    firecrawl_api_key: Optional[str] = Field(default=None, validation_alias=AliasChoices("FIRECRAWL_API_KEY", "FIRECRAWL_TOKEN"))
    zapier_api_key: Optional[str] = Field(default=None, validation_alias=AliasChoices("ZAPIER_NLA_API_KEY", "ZAPIER_API_KEY"))

    # 向量存储
    weaviate_url: Optional[str] = Field(default=None, validation_alias=AliasChoices("WEAVIATE_URL", "WEAVIATE_ENDPOINT"))
    weaviate_api_key: Optional[str] = Field(default=None, validation_alias=AliasChoices("WEAVIATE_API_KEY", "WEAVIATE_TOKEN"))

    # 代理配置
    http_proxy: Optional[str] = Field(default=None, validation_alias=AliasChoices("HTTP_PROXY", "http_proxy"))
    https_proxy: Optional[str] = Field(default=None, validation_alias=AliasChoices("HTTPS_PROXY", "https_proxy"))

    # 其他服务
    llama_parse_api_key: Optional[str] = Field(default=None, validation_alias=AliasChoices("LLAMA_PARSE_API_KEY", "LLAMA_PARSE_TOKEN"))

    model_config = SettingsConfigDict(
        env_file=DEFAULT_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @computed_field
    def project_root(self) -> Path:
        """暴露项目根目录，方便构建文件路径。"""
        return PROJECT_ROOT

    @computed_field
    def configured_tooling(self) -> list[str]:
        """返回已配置凭据的外部集成列表。"""
        mapping = {
            "openrouter": self.openrouter_api_key,
            "gemini": self.gemini_api_key,
            "openai": self.openai_api_key,
            "e2b": self.e2b_api_key,
            "tavily": self.tavily_api_key,
            "firecrawl": self.firecrawl_api_key,
            "zapier": self.zapier_api_key,
            "weaviate": self.weaviate_url and self.weaviate_api_key,
            "llama_parse": self.llama_parse_api_key,
        }
        return [name for name, value in mapping.items() if value]

    @computed_field
    def missing_credentials(self) -> list[str]:
        """列出未配置的凭据，便于优先处理。"""
        required_pairs = {
            "GEMINI_API_KEY": self.gemini_api_key,
            "E2B_API_KEY": self.e2b_api_key,
            "TAVILY_API_KEY": self.tavily_api_key,
            "FIRECRAWL_API_KEY": self.firecrawl_api_key,
            "ZAPIER_NLA_API_KEY": self.zapier_api_key,
            "WEAVIATE_URL": self.weaviate_url,
            "WEAVIATE_API_KEY": self.weaviate_api_key,
        }
        return [key for key, value in required_pairs.items() if not value]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """返回缓存的设置实例，配置只读取一次。"""
    return Settings()


settings = get_settings()
