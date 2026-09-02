from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"

class Settings(BaseSettings):
    app_name: str = "WeChat Content Publisher"
    api_v1_prefix: str = "/api/v1"

    opencode_api_key: str = ""
    opencode_model: str = "muse-spark-1.2-contributor"
    opencode_base_url: str = "https://opencode.ai/zen/go/v1"

    database_url: str = f"sqlite:///{Path(DATA_DIR / 'app.db').as_posix()}"
    data_dir: str = str(DATA_DIR)

    host: str = "127.0.0.1"
    port: int = 8000

    class Config:
        env_file = str(BASE_DIR / "backend" / ".env")
        env_file_encoding = "utf-8"

settings = Settings()
