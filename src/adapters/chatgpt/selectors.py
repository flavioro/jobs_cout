# src/adapters/chatgpt/selectors.py

CHATGPT_SELECTORS = {
    "prompt_textarea": "#prompt-textarea",
    "send_button": "[data-testid='send-button']",
    
    # Foca no conteúdo Markdown dentro da mensagem da IA
    "last_response": "div[data-message-author-role='assistant'] div.markdown",
    
    # O botão que aparece ENQUANTO a IA escreve
    "stop_button": "[data-testid='stop-button']"
}