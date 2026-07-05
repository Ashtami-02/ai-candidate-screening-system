"""
Central place to read environment variables.

Why this file exists: instead of scattering os.getenv() calls across every
file, every other module imports `settings` from here. If a config value
ever changes (say, you switch models), you edit exactly one place.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash"
    chroma_persist_dir: str = "./data/chroma_store"
    database_url: str = "sqlite:///./data/interview_system.db"

    class Config:
        env_file = ".env"


settings = Settings()
