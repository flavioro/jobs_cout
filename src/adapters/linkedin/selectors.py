LINKEDIN_SELECTORS = {
    "title": [
        "main p[class*='_07f7caa4']",
        "section p[class*='_07f7caa4']",
        "main p[class*='ff51c93b']",
        "section p[class*='ff51c93b']",
        ".top-card-layout__title",
        "[data-testid='job-title']",
        ".job-details-jobs-unified-top-card__job-title h1",
        ".job-details-jobs-unified-top-card__job-title",

       # 3. Tags Genéricas
        "h1.t-24",
        "h1.t-bold",
        "main h1",
        "h1",
        
        # 4. ÚLTIMO RECURSO: O Alerta de Vagas (Fallback sugerido)
        "h2:-soup-contains('Ative um alerta para vagas semelhantes') + div p",        
        "h2:-soup-contains('Ative um alerta para vagas semelhantes') + p",
    ],
    "company": [
        "a[href*='/company/']",
        ".topcard__org-name-link",
        ".topcard__flavor a",
        ".job-details-jobs-unified-top-card__company-name a",
    ],
    "location": [
        "p[class*='_31a95749']",
        "span[class*='_31a95749']",
        ".topcard__flavor--bullet",
        ".job-details-jobs-unified-top-card__primary-description-container",
        ".job-details-jobs-unified-top-card__tertiary-description-container",
    ],
    "description": [
        "[data-testid='expandable-text-box']",
        ".show-more-less-html__markup",
        ".jobs-description__content",
        ".description__text",
    ],
    "closed_texts": [
        "não aceita mais candidaturas",
        "nao aceita mais candidaturas",
    ],
    "easy_apply_texts": [
        "candidatura simplificada",
        "easy apply",
    ],
}
