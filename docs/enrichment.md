# Enrichment

O enrichment atual usa Groq para produzir dados estruturados a partir de título, empresa e descrição.

## Saídas atuais

- fit score
- rationale
- skills
- nível de inglês
- sugestão de senioridade
- setor

## Fluxo

1. buscar vagas pendentes no banco
2. aplicar blocklist antes da chamada ao LLM
3. montar contexto da vaga
4. chamar o modelo Groq
5. validar JSON com Pydantic
6. persistir os campos enriquecidos

## Relação com browser AI

ChatGPT e Gemini web não substituem o enrichment por API. Eles existem como automação complementar, útil para testes, análise manual assistida e futuras rotinas experimentais.
