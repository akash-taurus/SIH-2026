import os
from pathlib import Path
from typing import List, Optional

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class Settings(BaseSettings):
        PROJECT_NAME: str = "NER Landslide Early Warning System (NER-LEWS)"
        API_V1_STR: str = "/api/v1"
        CORS_ORIGINS: List[str] = ["*"]
        ENVIRONMENT: str = "development"
        DEFAULT_ZONE_CODE: str = "Z-SHL-01"

        # Background Monitoring & Alerting Settings
        MONITORING_INTERVAL_SECONDS: float = 30.0
        ALERT_COOLDOWN_SECONDS: int = 900
        ENABLE_BACKGROUND_WORKER: bool = True

        # Optional 3rd-Party Production API Keys (Adapter Pattern)
        WEATHER_API_KEY: Optional[str] = None
        MAPBOX_ACCESS_TOKEN: Optional[str] = None
        TWILIO_ACCOUNT_SID: Optional[str] = None
        TWILIO_AUTH_TOKEN: Optional[str] = None
        TWILIO_PHONE_NUMBER: Optional[str] = None
        CDAC_CAP_API_KEY: Optional[str] = None
        AI_MODEL_API_KEY: Optional[str] = None
        ELEVENLABS_API_KEY: Optional[str] = None

        model_config = SettingsConfigDict(
            case_sensitive=True,
            extra="ignore",
            env_file=str(ENV_PATH) if ENV_PATH.exists() else ".env"
        )

except Exception:
    from pydantic import BaseModel

    class Settings(BaseModel):
        PROJECT_NAME: str = "NER Landslide Early Warning System (NER-LEWS)"
        API_V1_STR: str = "/api/v1"
        CORS_ORIGINS: List[str] = ["*"]
        ENVIRONMENT: str = "development"
        DEFAULT_ZONE_CODE: str = "Z-SHL-01"

        # Background Monitoring & Alerting Settings
        MONITORING_INTERVAL_SECONDS: float = 30.0
        ALERT_COOLDOWN_SECONDS: int = 900
        ENABLE_BACKGROUND_WORKER: bool = True

        WEATHER_API_KEY: Optional[str] = None
        MAPBOX_ACCESS_TOKEN: Optional[str] = None
        TWILIO_ACCOUNT_SID: Optional[str] = None
        TWILIO_AUTH_TOKEN: Optional[str] = None
        TWILIO_PHONE_NUMBER: Optional[str] = None
        CDAC_CAP_API_KEY: Optional[str] = None
        AI_MODEL_API_KEY: Optional[str] = None
        ELEVENLABS_API_KEY: Optional[str] = None

        def __init__(self, **data):
            env_vars = {}
            if ENV_PATH.exists():
                try:
                    with open(ENV_PATH, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                k, v = line.split("=", 1)
                                env_vars[k.strip()] = v.strip().strip('"').strip("'")
                except Exception:
                    pass
            for field in self.__class__.model_fields:
                if field not in data:
                    val = os.environ.get(field, env_vars.get(field))
                    if val is not None:
                        data[field] = val
            super().__init__(**data)

settings = Settings()
