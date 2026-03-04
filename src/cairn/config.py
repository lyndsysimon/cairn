from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://cairn:cairn@localhost:5432/cairn"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    encryption_key: str = ""
    default_runtime: str = "docker"
    default_timeout_seconds: int = 300

    model_config = {"env_prefix": "CAIRN_"}


settings = Settings()
