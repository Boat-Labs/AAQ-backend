from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AAQ Backend"
    env: str = "dev"

    database_host: str = "localhost"
    database_port: int = 5432
    database_user: str = ""
    database_password: str = ""
    database_name: str = "postgres"

    model_config = {"env_file": ".env"}


settings = Settings()
