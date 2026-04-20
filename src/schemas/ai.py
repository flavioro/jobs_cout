from pydantic import BaseModel

from src.core.enums import JobSector

# Schema interno para validar a resposta exata da Groq
class GroqJobAnalysis(BaseModel):
    skills: list[str]
    fit_score: int
    fit_rationale: str
    seniority_suggestion: str | None
    english_level: str
    sector: JobSector | None = None