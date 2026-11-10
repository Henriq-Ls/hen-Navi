---
name: Layout da janela e das abas
description: Requisitos confirmados para a faixa de abas e a barra sem título nativo.
---

A janela continua sem a barra de título nativa. A barra horizontal mantém marca,
voltar, avançar, recarregar, endereço, Bloqueador (escudo), Economia de dados e
Favoritos, seguidos por um separador e pelos controles Minimizar,
Maximizar/restaurar e Fechar. Não criar botão de encaixe separado: o Maximizar
normal também dá acesso aos Snap Layouts nativos do Windows ao passar o mouse. Os
controles não ficam na barra vertical direita. A faixa de abas e o botão “+” não
mudam.

O usuário pediu que a pasta `_APP_/barra_direita_tools/` organize também os módulos
funcionais da barra (por exemplo, downloads, captura e diálogos), e não apenas um
componente visual que continue dependendo de módulos soltos no pacote `_APP_`.
Não manter cópias dos módulos antigos quando eles forem movidos.

Na barra vertical, o rodapé deve ter Limpar cache seguido de Abrir pasta de dados,
após um espaço expansível e um separador. Não exibir o botão de pega de
redimensionamento; o redimensionamento pelas bordas continua disponível.

Na faixa inferior horizontal, os favoritos ocupam a esquerda e o espaço compacto
à direita alterna entre CPU/RAM e mensagens temporárias de carregamento/aviso. Não
manter uma faixa de status separada em toda a largura.

**Why:** após pedir os controles na barra vertical ao ver uma captura, o usuário
escolheu explicitamente a barra horizontal superior. Depois esclareceu que o
controle de encaixe separado era redundante e que precisa do botão padrão de
maximizar/restaurar. Também pediu para substituir a pega de redimensionamento no
rodapé da barra vertical pelas ações de limpeza e abertura da pasta de dados.
Mais tarde pediu que avisos de carregamento e CPU/RAM compartilhem o espaço direito
da faixa inferior, sem a barra de status separada.
Em 2026-11-09, confirmou que essa organização da faixa inferior ficou boa.

**How to apply:** mantenha escudo, economia de dados e favoritos no topo, depois
adicione o separador e Minimizar, Maximizar/restaurar e Fechar. Não acrescente botão
de encaixe personalizado; mantenha o hit-test nativo do botão Maximizar para
Snap Layouts do Windows. Não coloque controles de janela na barra vertical.
Preserve ações e atalhos. A coluna deve encostar à direita sem faixa vazia; invalide
o estado Qt salvo antigo quando ele puder conservar uma área lateral obsoleta.
Mantenha abas e o botão “+”. Organize os módulos funcionais em
`barra_direita_tools` sem cópias antigas. Mantenha Limpar cache e Abrir pasta de
dados no rodapé depois do espaçador, sem `QSizeGrip`.
Na faixa inferior, mantenha favoritos à esquerda e o indicador de CPU/RAM como
widget não permanente do `QStatusBar`, para que mensagens temporárias o substituam.
