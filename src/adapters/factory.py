from src.adapters.linkedin.adapter import LinkedInAdapter
from src.utils.url import is_supported_linkedin_url


class AdapterFactory:
    @staticmethod
    def get_adapter(url: str):
        if is_supported_linkedin_url(url):
            return LinkedInAdapter()
        raise ValueError("Fonte não suportada na v1")
