from pydantic_settings import BaseSettings, SettingsConfigDict
from cryptography.fernet import Fernet

class Settings(BaseSettings):
    
     # 프로젝트 정보
    PROJECT_NAME: str
    VERSION: str
    API_V1_PREFIX: str
    DEBUG: bool = True

    # JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    ENCRYPT_KEY: str

    # DB
    DATABASE_URL:str
    
    # 노트 생성
    SUMMARY_WORKDIR: str
    PDF_SCRIPT_PATH: str
    URL_SCRIPT_PATH: str
    CANVAS_DOWNLOADER_PATH: str
    
    # 스크립트 타임아웃
    PDF_TIMEOUT: int
    VIDEO_TIMEOUT: int
    
    # OPENAI API
    OPENAI_API_KEY: str
    
    # CANVAS
    CANVAS_LOGIN_URL: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )
    
    @property
    def fernet(self):
        return Fernet(self.ENCRYPT_KEY)


settings = Settings()
