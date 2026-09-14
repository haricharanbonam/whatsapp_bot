from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PORT: int = 8000
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_WHATSAPP_NUMBER: str
    MY_WHATSAPP_NUMBER: str
    AI_API_KEY: str = ""
    GOOGLE_CREDENTIALS_PATH: str = "credentials.json"
    GOOGLE_TOKEN_PATH: str = "token.json"
    GOOGLE_CALENDAR_ID: str = "primary"
    LEETCODE_USERNAME: str = ""
    SCHEDULER_TIMEZONE: str = "Asia/Kolkata"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()