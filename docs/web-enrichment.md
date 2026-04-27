# Web Enrichment

Este documento descreve o enrichment de vagas usando providers web.

## Objetivo

Permitir que o pipeline de enrichment use automação web como alternativa ao provider por API, aproveitando ChatGPT e Gemini quando necessário.

## Providers suportados

- `chatgpt_web`
- `gemini_web`

O provider é selecionado por configuração:

```env
ENRICHMENT_PROVIDER=groq
# ou
ENRICHMENT_PROVIDER=chatgpt_web
# ou
ENRICHMENT_PROVIDER=gemini_web
```

## Configurações principais

Exemplos de variáveis relevantes:

```env
ENRICHMENT_PROVIDER=gemini_web
ENRICHMENT_WEB_CHAT_MODE=new_chat
ENRICHMENT_WEB_RESPONSE_TIMEOUT_S=45
ENRICHMENT_WEB_MAX_RETRIES=1
ENRICHMENT_WEB_FORCE_NEW_CHAT=true
```

## Fluxo interno

1. selecionar vagas pendentes
2. montar prompt estruturado de enrichment
3. abrir ou reutilizar sessão do provider web
4. enviar prompt
5. aguardar resposta finalizar
6. extrair o primeiro objeto JSON válido
7. normalizar campos variáveis
8. validar com Pydantic
9. persistir no banco

## Por que usar `new_chat`

Para enrichment, `new_chat` é o modo recomendado porque reduz:
- contaminação de contexto
- respostas influenciadas por histórico anterior
- imprevisibilidade entre execuções

## Normalização de payload

Mesmo quando o provider responde JSON, ele pode retornar valores livres demais.

O projeto já trata isso para campos como:
- `sector`
- `english_level`
- `seniority_suggestion`

Isso permite manter enums rígidos no schema sem depender de respostas perfeitas do provider.

## Logs e debug

Quando há falha, verifique:

- `data/debug/gemini_page.html`
- `data/debug/gemini_page.png`
- `data/debug/chatgpt_page.html`
- `data/debug/chatgpt_page.png`
- logs de `ai_enrichment.json_error`
- logs de `ai_enrichment.api_error`

## Erros comuns

### 1. `Nenhum objeto JSON encontrado na resposta`
Causas prováveis:
- resposta ainda estava sendo gerada
- provider respondeu texto livre
- seletor capturou conteúdo parcial

### 2. Erro de enum
Causa:
- provider respondeu valor fora do schema
- camada de normalização ainda não cobre aquele caso

### 3. Sessão inválida
Causa:
- perfil persistente expirado
- login perdido
- bloqueio intermediário do provider

## Estratégia recomendada de rollout

### Fase 1
- usar `limit` pequeno
- testar com poucas vagas
- comparar com Groq

### Fase 2
- validar qualidade dos campos persistidos
- revisar logs de erro
- ajustar prompt/normalização

### Fase 3
- usar de forma mais contínua
- manter `groq` como fallback ou baseline de comparação

## Quando usar cada provider

### `groq`
Melhor quando:
- você quer velocidade
- maior previsibilidade
- menor dependência de sessão web

### `chatgpt_web`
Melhor quando:
- você quer testar outra qualidade de resposta
- comparar raciocínio/fit
- rodar análises assistidas

### `gemini_web`
Melhor quando:
- você quer alternativa web adicional
- comparar qualidade de classificação com ChatGPT/Groq

## Recomendações finais

- mantenha `groq` como baseline
- use providers web com `new_chat`
- monitore logs e respostas normalizadas
- trate browser AI como capacidade complementar, não infraestrutura totalmente determinística
