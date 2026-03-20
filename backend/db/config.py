from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/an577"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    assemblee_api_base_url: str = "https://data.assemblee-nationale.fr/api"
    gouv_api_base_url: str = "https://www.data.gouv.fr/api/1"
    nosdeputes_api_base_url: str = "https://www.nosdeputes.fr"


settings = Settings()
