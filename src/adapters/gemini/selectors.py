GEMINI_SELECTORS = {
    # Campo principal de prompt no Gemini Web. Mantemos múltiplos fallbacks por instabilidade de DOM.
    "prompt_input": [
        "textarea[aria-label*='Enter a prompt']",
        "textarea[placeholder*='Enter a prompt']",
        "rich-textarea textarea",
        "div[contenteditable='true']",
    ],
    # Elementos candidatos para blocos de resposta.
    "response_blocks": [
        "message-content",
        "model-response",
        "div.response-content",
        "div.markdown",
    ],
    # Botões que sinalizam envio/geração em andamento.
    "send_button": [
        "button[aria-label*='Send message']",
        "button[aria-label*='Submit']",
        "button.send-button",
    ],
    "stop_button": [
        "button[aria-label*='Stop']",
        "button[mattooltip*='Stop']",
    ],
}
