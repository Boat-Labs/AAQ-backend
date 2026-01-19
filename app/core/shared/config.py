from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AAQ Backend"
    env: str = "dev"


settings = Settings()
