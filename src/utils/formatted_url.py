import re

# Cole seu texto bruto aqui dentro das aspas triplas
texto_bruto = """
https://www.linkedin.com/jobs/view/4403576258

https://www.linkedin.com/jobs/view/4400886931

https://www.linkedin.com/jobs/view/4400881057

https://www.linkedin.com/jobs/view/4400895044

https://www.linkedin.com/jobs/view/4403570312

https://www.linkedin.com/jobs/view/4402636670

https://www.linkedin.com/jobs/view/4402396738

https://www.linkedin.com/jobs/view/4403521473

https://www.linkedin.com/jobs/view/4402636670

https://www.linkedin.com/jobs/view/4400884142

https://www.linkedin.com/jobs/view/4403568199

https://www.linkedin.com/jobs/view/4403537511

https://www.linkedin.com/jobs/view/4362188533

https://www.linkedin.com/jobs/view/4403540019

https://www.linkedin.com/jobs/view/4400881955

https://www.linkedin.com/jobs/view/4400895050

"""

# 1. Extrai apenas o que parece URL, ignorando linhas vazias e espaços
links = re.findall(r'https?://[^\s]+', texto_bruto)

# 2. Formata a saída final
for i, link in enumerate(links):
    # Criamos a string com 4 espaços no início
    linha = f'    "{link}"'
    
    # Adiciona a vírgula se não for o último
    if i < len(links) - 1:
        print(linha + ",")
    else:
        print(linha)