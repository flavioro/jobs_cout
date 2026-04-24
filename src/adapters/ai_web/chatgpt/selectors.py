CHATGPT_SELECTORS = {
    "prompt_input": [
        "#prompt-textarea",
        "textarea[placeholder*='Message']",
        "textarea[placeholder*='Enviar']",
        "textarea",
        "div[contenteditable='true']",
        "[contenteditable='true'][data-lexical-editor='true']",
    ],
    "send_button": [
        "[data-testid='send-button']",
        "button[aria-label*='Send']",
        "button[aria-label*='Enviar']",
        "button[data-testid*='send']",
    ],
    "response_blocks": [
        "div[data-message-author-role='assistant'] div.markdown",
        "div[data-message-author-role='assistant'] .prose",
        "div[data-message-author-role='assistant']",
        "article[data-testid*='conversation-turn'] div.markdown",
    ],
    "stop_button": [
        "[data-testid='stop-button']",
        "button[aria-label*='Stop']",
        "button[aria-label*='Parar']",
    ],
    "new_chat": [
        "a[href='/']",
        "button[aria-label*='New chat']",
        "button[aria-label*='Novo chat']",
        "a[aria-label*='New chat']",
    ],
}
