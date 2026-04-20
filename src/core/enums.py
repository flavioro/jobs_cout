from enum import Enum

class JobSector(str, Enum):
    # Tecnologia Pura
    TI_CONSULTING = "Consultoria de TI e Outsourcing"
    SOFTWARE_PRODUCT = "Produto de Software e SaaS"
    CYBERSECURITY = "Cibersegurança"
    DATA_AI = "Dados e Inteligência Artificial"
    
    # Setores Tradicionais com forte área tech
    FINANCE = "Finanças, Bancos e Fintechs"
    RETAIL_ECOMMERCE = "Varejo e E-commerce"
    HEALTHCARE = "Saúde e Healthtechs"
    EDUCATION = "Educação e Edtechs"
    INDUSTRY_MANUFACTURING = "Indústria e Manufatura"
    LOGISTICS = "Logística e Supply Chain"
    GOVERNMENT = "Setor Público e Governo"
    AGROTECH = "Agronegócio"
    
    # Fallback
    OTHER = "Outros"
    UNKNOWN = "Desconhecido"

class JobSource(str, Enum):
    LINKEDIN = "linkedin"


class WorkplaceType(str, Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"


class SeniorityLevel(str, Enum):
    INTERN = "intern"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    MANAGER = "manager"


class JobStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    NOT_FOUND = "not_found"
    LAYOUT_CHANGED = "layout_changed"
    POPUP_FAILED = "popup_failed"
    ERROR = "error"
    APPLIED = "applied"


class AvailabilityStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    UNKNOWN = "unknown"


class ClosedReason(str, Enum):
    DOES_NOT_ACCEPT_APPLICATIONS = "does_not_accept_applications"
    REMOVED = "removed"
    UNKNOWN = "unknown"


class ConfirmationStatus(str, Enum):
    MATCH = "match"
    NORMALIZED_MATCH = "normalized_match"
    MISMATCH = "mismatch"
    MISSING = "missing"
    USER_PROVIDED_HINT = "user_provided_hint"


class EnglishLevel(str, Enum):
    NOT_MENTIONED = "not_mentioned"
    NONE_REQUIRED = "none_required"
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    FLUENT = "fluent"
    IMPLICIT = "implicit"