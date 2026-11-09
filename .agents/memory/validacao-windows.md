---
name: Validação no Windows
description: Como interpretar diferenças entre a execução Windows e o workspace Replit.
---

O navegador pode ser executado de uma cópia local do Windows que não recebe automaticamente as alterações feitas no workspace Replit. Compare o símbolo e o fluxo citados nos logs com o código atual antes de concluir que uma correção não funcionou.

**Why:** os logs enviados pelo usuário apontaram um NameError de uma constante que já estava importada e definida no workspace, indicando uma cópia diferente ou desatualizada.

**How to apply:** quando um problema continuar no Windows, confirme que a cópia executada contém as alterações atuais; trate mensagens de uma versão diferente separadamente do comportamento do código atual.
