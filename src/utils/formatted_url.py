import re

# Cole seu texto bruto aqui dentro das aspas triplas
texto_bruto = """
https://linkedin.com/comm/jobs/view/4399068226/
https://linkedin.com/comm/jobs/view/4399788834/
https://linkedin.com/comm/jobs/view/4401536665/
https://linkedin.com/comm/jobs/view/4399644111/
https://linkedin.com/comm/jobs/view/4401594884/
https://linkedin.com/comm/jobs/view/4400740159/
https://linkedin.com/comm/jobs/view/4399663660/
https://linkedin.com/comm/jobs/view/4401378681/
https://linkedin.com/comm/jobs/view/4399774075/
https://linkedin.com/comm/jobs/view/4401066796/
https://linkedin.com/comm/jobs/view/4399645540/
https://linkedin.com/comm/jobs/view/4364005493/


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