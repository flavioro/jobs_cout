
def build_web_enrichment_prompt(
    *,
    title: str,
    company: str | None,
    description_text: str | None,
    current_seniority: str | None,
    user_profile_context: str | None,
) -> str:
    company_text = company or "Não informado"
    description = (description_text or "")[:6000]
    seniority = current_seniority or "Não informado"
    user_profile = user_profile_context or "Não informado"

    return f"""
Analise a vaga abaixo e responda APENAS com JSON válido, sem markdown, sem explicações e sem texto extra.

Campos obrigatórios:
- skills: lista de até 10 strings
- fit_score: inteiro de 0 a 100
- fit_rationale: string curta
- seniority_suggestion: um de ["intern", "junior", "mid", "senior", "staff", "none"]
- english_level: um de ["basic", "intermediate", "advanced", "fluent", "not mentioned"]
- sector: EXATAMENTE um destes valores:
  - Consultoria de TI e Outsourcing
  - Produto de Software e SaaS
  - Cibersegurança
  - Dados e Inteligência Artificial
  - Finanças, Bancos e Fintechs
  - Varejo e E-commerce
  - Saúde e Healthtechs
  - Educação e Edtechs
  - Indústria e Manufatura
  - Logística e Supply Chain
  - Setor Público e Governo
  - Agronegócio
  - Outros
  - Desconhecido

Regras:
- Nunca invente um valor diferente para sector.
- Se houver ambiguidade, escolha o setor mais próximo da lista acima.
- Se não houver evidência suficiente, use "Desconhecido".
- Se inglês não for mencionado, use "not mentioned".
- Responda somente com JSON válido.

Perfil do candidato:
{user_profile}

Vaga:
Título: {title}
Empresa: {company_text}
Senioridade atual: {seniority}
Descrição:
{description}
""".strip()
