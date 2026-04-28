from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- FreshService --- #
    freshservice_domain: str
    freshservice_api_key: str

    model_config = SettingsConfigDict(
        env_file="./settings/settings.env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
    )

settings = Settings()