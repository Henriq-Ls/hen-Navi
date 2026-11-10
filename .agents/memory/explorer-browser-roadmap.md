---
name: Explorer e prévias locais
description: Requisitos do usuário para a saída de estrutura, abertura local de arquivos e inspeção do AppData.
---

No Explorador local, escolher uma pasta gera automaticamente a estrutura inteira, mantendo a raiz na primeira linha; os itens começam marcados e desmarcá-los remove arquivos ou ramos sem remover a raiz. Clique simples mostra prévia local compacta; duplo clique abre em aba interna. A ação de pasta de dados deve continuar começando em `appdata.pasta_raiz`, em um modo de inspeção sem busca ou edição destrutiva.

Os componentes e configurações próprios dos botões da barra direita devem ficar em `_APP_/barra_direita_tools/`; a janela principal deve instanciar um coordenador de alto nível, não montar cada ferramenta individualmente. Evitar cópias duplicadas de captura e dependências circulares entre a barra e o núcleo do navegador.

O plano detalhado e a sequência de implementação ficam em `PLANO_IMPLEMENTACAO_EXPLORADOR_BROWSER.txt`.

**Why:** o usuário definiu estes comportamentos e a organização da barra, depois confirmou que a estrutura completa deve aparecer automaticamente ao escolher a pasta.

**How to apply:** leia o plano antes de alterar o Explorador, a barra direita ou reorganizar `browser.py`; preserve o envio normal de arquivos para sites e não declare reprodução de vídeo sem validação no Windows.
