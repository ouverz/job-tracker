import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    cv_path: str = "../cv.txt"
    db_path: str = "./data/jobs.db"
    search_roles: list[str] = ["AI Engineer", "Data Engineer", "Analytics Engineer"]
    search_location: str = "Germany"
    dach_locations: list[str] = [
        "Germany",
        "Austria",
        "Switzerland",
        "Deutschland",
        "Österreich",
        "Schweiz",
        "Remote",
        "DACH",
    ]
    max_jobs_per_source: int = 50

    # Candidate profile — used to personalise ATS scoring prompts.
    # Set these in your .env file to match your own situation.
    candidate_location: str = "your city, Country"
    candidate_max_commute_min: int = 45
    candidate_language_requirement: str = "Language B1"

    model_config = {
        "env_file": str(Path(__file__).resolve().parent.parent.parent / ".env")
    }

    def get_cv_text(self) -> str:
        cv_path = Path(self.cv_path)
        if not cv_path.is_absolute():
            # config.py lives at backend/app/config.py → .parent.parent = backend/
            # so backend/ + "../cv.txt" = project root cv.txt
            cv_path = Path(__file__).resolve().parent.parent / self.cv_path
        if cv_path.exists():
            return cv_path.read_text(encoding="utf-8")
        return ""


settings = Settings()
