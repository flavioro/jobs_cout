GEMINI_SELECTORS = {
    "prompt_input": [
        "div[contenteditable='true']",
        "div[role='textbox']",
        "textarea",
    ],
    "send_button": [
        "button[aria-label*='Send message']",
        "button[aria-label*='Enviar mensagem']",
        "button.send-button",
    ],
    "response_blocks": [
        "message-content",
        "model-response",
        "div.response-content",
        "div.markdown",
    ],
    "stop_button": [
        "button[aria-label*='Stop']",
        "button[aria-label*='Parar']",
    ],
    "new_chat": [
        "button[aria-label*='New chat']",
        "button[aria-label*='Nova conversa']",
        "a[href='/app']",
    ],
}
