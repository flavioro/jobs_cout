# Enrichment

O enrichment do projeto adiciona inteligência estruturada às vagas já persistidas.

## Objetivo

A partir de título, empresa, descrição e contexto do candidato, o enrichment produz campos como:

- fit score
- rationale
- skills
- nível de inglês
- sugestão de senioridade
- setor

## Providers suportados

O provider é configurável por ambiente.

### 1. `groq`
Provider por API, mais rápido e previsível para produção.

### 2. `chatgpt_web`
Provider via automação web.

### 3. `gemini_web`
Provider via automação web.

## Fluxo

1. buscar vagas pendentes no banco
2. aplicar blocklist antes da chamada ao modelo
3. montar o contexto da vaga
4. escolher o provider configurado
5. obter resposta estruturada
6. validar dados
7. persistir os campos enriquecidos

## Enrichment por Groq

No modo `groq`, o serviço:
- monta mensagens para o modelo
- pede `json_object`
- valida a resposta com `GroqJobAnalysis`

Esse continua sendo o caminho mais estável quando o objetivo é throughput e previsibilidade.

## Enrichment web

Nos modos `chatgpt_web` e `gemini_web`, o serviço:

1. monta um prompt estruturado
2. pede apenas JSON válido
3. usa `BrowserAIProviderSession`
4. extrai o primeiro objeto JSON da resposta
5. normaliza campos variáveis
6. valida com `GroqJobAnalysis`
7. persiste no banco

## Normalização defensiva

Providers web podem retornar valores semanticamente corretos, mas fora do enum esperado.

Por isso o serviço normaliza campos como:

- `sector`
- `english_level`
- `seniority_suggestion`

Exemplos:
- `"Pleno"` → `"mid"`
- `"Não mencionado"` → `not_mentioned`
- `"Consultoria de TI / Construção Civil"` → valor canônico aceito pelo schema

## Boas práticas

- usar `new_chat` para enrichment
- rodar com poucos itens no início
- revisar logs em caso de `json_parsing_error`
- comparar qualidade entre `groq`, `chatgpt_web` e `gemini_web`

## Limitações

Enrichment web é mais suscetível a:
- mudanças de DOM
- lentidão de geração
- texto extra fora do JSON
- necessidade de sessão persistente válida

Por isso o projeto trata browser AI como provider configurável, e não como substituição automática da camada por API.
