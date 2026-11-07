# hen-Nave

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![PySide6 6.8+](https://img.shields.io/badge/PySide6-6.8%2B-41CD52?logo=qt&logoColor=white)
![SQLite](https://img.shields.io/badge/Storage-SQLite-003B57?logo=sqlite&logoColor=white)

**Navegador desktop independente**, desenvolvido em Python com PySide6 e
QtWebEngine (Chromium).

O hen-Nave foi feito para rodar como aplicativo no computador. Ele não é um
site, então a janela do navegador não aparece no preview web da Replit.

## Recursos

- Navegação HTTP(S), abas e página inicial local.
- Histórico, favoritos, anotações e sessão persistidos em SQLite.
- Histórico de downloads comuns, com abertura do arquivo e da pasta.
- Downloads da janela anônima visíveis somente enquanto ela estiver aberta.
- Janelas anônimas com perfil temporário.
- Bloqueador simples de anúncios com lista local e exceções por site.
- Capturas da área visível, página inteira e exportação em PDF.
- Download de vídeos com análise de título, canal, duração e qualidades.
- Temas, busca na página e atalhos de teclado.
- Diagnóstico local de suporte a codecs de vídeo pelo QtWebEngine, no menu do navegador.
- Ferramentas integradas de segurança: análise local de endereço, cabeçalhos HTTP
  e certificado HTTPS.
- DevTools do Chromium e central de privacidade por site.
- Gerenciador de senhas no cofre seguro do sistema operacional.
- Seletor Qt de arquivos e pastas para uploads em páginas web.
- Assistente opcional para resumir e responder perguntas sobre a página atual.
- Ações no rodapé para abrir a pasta de dados e limpar o cache.

## Requisitos

- Python 3.10 ou superior.
- PySide6 6.8 ou superior (inclui QtWebEngine).
- QtAwesome 1.3 ou superior, usado para os ícones da interface.
- `keyring`, usado para guardar chaves no cofre seguro do sistema operacional.
- yt-dlp, usado para consultar e baixar vídeos.
- openai-whisper, usado como alternativa quando o vídeo não tem legendas.
- Windows, macOS ou Linux com ambiente gráfico.
- FFmpeg local para baixar/mesclar mídia, converter áudio e transcrever quando
  não houver legendas.

As dependências Python estão em `requirements.txt`.

O suporte a MP4/H.264 depende de como o QtWebEngine foi compilado. Use
**Testar suporte a vídeo** no menu para consultar os formatos anunciados pela
versão instalada; o FFmpeg usado para downloads não altera a reprodução dentro
das páginas.

## Instalação e execução

Execute os comandos na raiz do projeto.

### Windows (PowerShell)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

### Linux e macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

No Linux, a distribuição pode exigir bibliotecas gráficas do Qt instaladas pelo
sistema operacional. Se a inicialização indicar que falta um plugin como `xcb`,
instale os componentes Qt/X11 correspondentes à sua distribuição.

## Interface e atalhos

Os botões da barra incluem favoritos, bloqueador, download de vídeo, captura,
anotações e o assistente de IA. O histórico de downloads comuns também pode ser
aberto pelo botão na barra lateral direita ou pelo menu. Capturas ficam em **Ferramentas**; temas,
bloqueador, dados, conexões de IA e atalhos ficam em **Configurações**. A lista
completa de atalhos também abre com `F1`.

### Ferramentas de segurança e privacidade

Essas ferramentas são recursos internos do hen-Nave, não plugins instaláveis nem
um sistema de extensões:

- **Ferramentas do desenvolvedor** abre o DevTools do Chromium na aba atual. Ao
  trocar de aba, o painel acompanha a página selecionada. O botão fica na barra
  vertical à direita.
- **Segurança do site**, no menu do hen-Nave, analisa sinais básicos do endereço
  localmente. Os botões de cabeçalhos e certificado só fazem uma consulta `HEAD`
  à raiz do mesmo domínio após o clique; não enviam cookies, não baixam o corpo
  da página e não seguem redirecionamentos. A ausência de um cabeçalho numa
  resposta `HEAD` é inconclusiva.
- **Privacidade do site**, também no menu do hen-Nave, mostra estados de
  permissões que o QtWebEngine expõe. Você pode redefini-los e, após confirmação,
  solicitar a limpeza dos cookies e dos armazenamentos locais da origem atual.
  Isso não apaga o cache HTTP geral nem os dados de outros domínios.

O hen-Nave já possui um inspetor DOM próprio para consultar e fazer alterações
temporárias na página; ele é diferente do DevTools completo do Chromium.

### Uploads de arquivos e pastas

Ao clicar num controle de upload de site, o hen-Nave abre um seletor Qt próprio,
modal à janela do navegador e sem usar o seletor nativo do sistema. Ele distingue
arquivo único, vários arquivos, pasta e seleção para salvar. Quando a página pede
uma pasta, o hen-Nave envia a lista de arquivos encontrados nela, preservando os
caminhos relativos. Para evitar que alguns sites tentem tratar marcadores de
diretório `/.` como arquivos, o seletor prepara essa lista diretamente quando a
pasta contém arquivos na raiz; pastas sem arquivos na raiz continuam usando o
modo de diretório do QtWebEngine. Em seleções comuns, usa os tipos MIME aceitos
pelo site quando disponíveis. Cancelar fecha o seletor sem enviar arquivos. Os
rótulos e controles do seletor estão em português, a lista aparece em ordem
alfabética e a barra lateral oferece atalhos para Área de Trabalho, Downloads e
Início.

O botão de download abre um painel à direita. Ele analisa o link da aba atual ou
um endereço colado no painel, permite escolher a qualidade máxima, o formato e a
pasta de destino. Também pode baixar áudio, salvar transcrições e gerar legendas
SRT. A transcrição usa legendas disponíveis primeiro e recorre ao Whisper quando
necessário. As tarefas selecionadas rodam em segundo plano.

### Assistente de página

1. Em **Configurações → Inteligência Artificial**, escolha **Adicionar**, selecione
   o provedor e informe a chave quando necessário.
2. Use **Buscar modelos** ou digite o identificador do modelo. **Testar conexão**
   verifica o serviço sem enviar texto da página. Salve e depois selecione
   **Ativar** na lista de conexões.
3. Abra o painel pelo botão de IA ou com `Ctrl+Shift+Y`. Use **Resumir página**
   ou faça uma pergunta; o painel também permite cancelar, copiar e limpar a
   conversa. A engrenagem abre as configurações; falta de conexão, modelo ou
   chave aparece como aviso no próprio painel, sem abrir outra janela.

Para Ollama, o hen-Nave preenche `http://localhost:11434` e consulta
automaticamente `/api/tags` ao abrir um cadastro Ollama ou selecioná-lo. O
serviço Ollama precisa estar instalado e em execução; a consulta lista os modelos
já disponíveis no serviço, não procura nem inicia o executável. Se a lista não
aparecer, inicie o Ollama e tente **Buscar modelos** novamente.

OpenRouter e os demais provedores compatíveis usam suas URLs base e modelos
editáveis. A chave fica no cofre seguro do sistema operacional. Anthropic e Gemini
não são oferecidos como presets nesta versão porque usam protocolos próprios.
O texto da página só é coletado após uma ação explícita; antes de enviar conteúdo
a um provedor de nuvem, o hen-Nave pede confirmação. A resposta aparece como
texto simples. Essa confirmação de privacidade é uma janela separada; em janelas
normais pode ser dispensada para aquela conexão, mas no modo anônimo aparece a
cada uso.

### FFmpeg

Coloque o executável `ffmpeg.exe` (ou `ffmpeg` em outros sistemas) em
`FFmpeg/` ou `FFmpeg/bin/` na raiz do projeto, ou disponibilize-o no `PATH`.
Em um executável PyInstaller de arquivo único, também pode colocá-lo ao lado do
`.exe`, dentro de `FFmpeg/` ou `FFmpeg/bin/`. Os executáveis não são incluídos no
repositório. A transcrição tenta usar legendas primeiro; se não houver, precisa
do Whisper e do FFmpeg. O modelo Whisper pode ser baixado automaticamente para o
cache do hen-Nave na primeira utilização. O suporte depende dos sites reconhecidos
pelo yt-dlp e do acesso permitido pelo site de origem.

| Ação | Atalho |
|---|---|
| Nova aba | `Ctrl+T` |
| Fechar aba atual | `Ctrl+W` |
| Focar a barra de endereço | `Ctrl+L` |
| Abrir a página inicial | `Alt+Home` |
| Abrir o histórico | `Ctrl+H` |
| Abrir os favoritos | `Ctrl+Shift+O` |
| Localizar na página | `Ctrl+F` |
| Capturar a página | `Ctrl+Shift+S` |
| Abrir o assistente da página | `Ctrl+Shift+Y` |
| Abrir a pasta de dados | `Ctrl+Shift+D` |
| Mostrar todos os atalhos | `F1` |

Os ícones da interface são definidos em `_ULTILIDADES_/icones.py`; textos,
atalhos e cores são centralizados em `_CONFIGURA_/`.

## Dados, cache e privacidade

Os dados ficam fora da pasta do código:

| Sistema | Pasta |
|---|---|
| Windows | `%APPDATA%\hen-nave\` |
| Linux e macOS | `~/.hen-nave/` |

A pasta contém configurações, banco SQLite, perfil persistente do WebEngine,
cache e logs. Use o botão de pasta no rodapé ou `Ctrl+Shift+D` para abri-la.
O botão **Limpar cache** remove o cache HTTP do navegador; cookies e histórico
não são apagados.

**Privacidade do site** limpa apenas os dados da origem atual após confirmação;
ela não substitui a limpeza geral do cache.

Janelas normais mantêm cookies, histórico e sessão de abas entre execuções.
Janelas anônimas usam um perfil temporário e não salvam cookies, histórico ou
sessão; favoritos continuam disponíveis. Anotações ficam desativadas nelas.
O modo anônimo não oculta a atividade dos sites nem do provedor de internet.

As conexões do assistente guardam somente metadados em
`config/ai_providers.json`; chaves e tokens ficam no keyring seguro do sistema,
nunca em JSON, logs ou arquivos `.env`. Se não houver um cofre do sistema
disponível, o hen-Nave recusa salvar a chave. Antes de enviar texto a um provedor
de nuvem, o app pede confirmação e recomenda consultar a política de dados do
serviço. Janelas anônimas pedem confirmação em cada uso de nuvem e mantêm
perguntas e respostas apenas em memória até serem fechadas.

## Bloqueador de anúncios

O bloqueador começa com uma lista local pequena; nenhuma lista pública vem
configurada. É possível informar uma URL HTTPS nas configurações. O parser
aceita arquivos hosts e regras simples como `||dominio^`, incluindo
subdomínios. Não implementa filtros cosméticos nem toda a sintaxe do Adblock
Plus, e não substitui uma extensão completa.

## Segurança

- Endereços, favoritos, histórico e sessão aceitam apenas URLs HTTP(S).
- Consultas ao SQLite usam parâmetros.
- Chaves de provedores ficam somente no keyring do sistema operacional.
- Logins de sites só são salvos após confirmação; usuário e senha ficam no
  keyring do sistema, e o arquivo local contém apenas origem e identificador.
- A proteção em repouso do login é responsabilidade do backend do sistema
  operacional. O hen-Nave não aplica uma camada própria de criptografia e não
  grava a senha em arquivo se o keyring seguro não estiver disponível.
- O preenchimento exige uma ação sua e funciona somente na origem HTTPS exata
  onde o login foi salvo. O gerenciador não funciona em janelas anônimas.
- HTTP é permitido apenas para localhost e IPs privados; destinos públicos
  precisam de HTTPS. Redirecionamentos são bloqueados para não encaminhar chaves.
- O assistente não recebe cookies, histórico, anotações, arquivos ou dados do
  perfil do navegador.
- A página inicial local escapa conteúdo dinâmico e não concede acesso a
  arquivos locais para páginas remotas.
- O sandbox do Chromium permanece habilitado.

Para salvar um login, abra o menu do hen-Nave, escolha **Senhas e logins** e
clique em **Salvar login desta página**. Confira os campos e confirme. Para
preencher depois, abra a mesma origem HTTPS, escolha a conta e clique em
**Preencher selecionado**. O navegador não envia o formulário automaticamente.

## Estrutura do projeto

```text
.
├── _APP_/                 Janelas, painéis e ferramentas integradas
├── _APPDATA_/             Pastas e arquivos de dados do usuário
├── _CONFIGURA_/           Textos, temas, cores e atalhos
├── _LOGS_/                Registro de eventos e falhas
├── _SERVICOS_/            Vídeo, IA, bloqueador e análise de segurança
├── _THREADS_/             Threads e gerenciamento de execução
├── _ULTILIDADES_/         Pop-ups, ícones e funções reutilizáveis
├── midias/                Logo do navegador e ícone do aplicativo
├── nucleo/                Documentação do projeto
├── tests/                 Testes automatizados
├── browser.py             Navegação, janelas e perfis
├── main.py                Inicialização do aplicativo
└── requirements.txt       Dependências Python
```

## Testes

Com as dependências instaladas, execute na pasta do projeto:

```bash
python -m unittest discover -s tests -v
python -m compileall -q .
```

Os testes automatizados não substituem a verificação manual da interface e do
QtWebEngine em um computador com ambiente gráfico.
