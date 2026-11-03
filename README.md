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
- Janelas anônimas com perfil temporário.
- Bloqueador simples de anúncios com lista local e exceções por site.
- Capturas da área visível, página inteira e exportação em PDF.
- Download de vídeos com análise de título, canal, duração e qualidades.
- Temas, busca na página e atalhos de teclado.
- Ações no rodapé para abrir a pasta de dados e limpar o cache.

## Requisitos

- Python 3.10 ou superior.
- PySide6 6.8 ou superior (inclui QtWebEngine).
- QtAwesome 1.3 ou superior, usado para os ícones da interface.
- yt-dlp, usado para consultar e baixar vídeos.
- openai-whisper, usado como alternativa quando o vídeo não tem legendas.
- Windows, macOS ou Linux com ambiente gráfico.
- FFmpeg local para baixar/mesclar mídia, converter áudio e transcrever quando
  não houver legendas.

As dependências Python estão em `requirements.txt`.

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

Os botões da barra incluem favoritos, bloqueador, download de vídeo, ferramentas
e menu.
Capturas e anotações ficam em **Ferramentas**; temas, bloqueador, dados e atalhos
ficam em **Configurações**. A lista completa de atalhos também abre com `F1`.

O botão de download abre um painel à direita. Ele analisa o link da aba atual ou
um endereço colado no painel, permite escolher a qualidade máxima, o formato e a
pasta de destino. Também pode baixar áudio, salvar transcrições e gerar legendas
SRT. A transcrição usa legendas disponíveis primeiro e recorre ao Whisper quando
necessário. As tarefas selecionadas rodam em segundo plano.

### FFmpeg

Coloque o executável `ffmpeg.exe` (ou `ffmpeg` em outros sistemas) em
`FFmpeg/` ou `FFmpeg/bin/` na raiz do projeto, ou disponibilize-o no `PATH`.
Os executáveis não são incluídos no repositório. A transcrição tenta usar legendas
primeiro; se não houver, precisa do Whisper e do FFmpeg. O modelo Whisper pode ser
baixado automaticamente para o cache do hen-Nave na primeira utilização. O suporte
depende dos sites reconhecidos pelo yt-dlp e do acesso permitido pelo site de origem.

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

Janelas normais mantêm cookies, histórico e sessão de abas entre execuções.
Janelas anônimas usam um perfil temporário e não salvam cookies, histórico ou
sessão; favoritos continuam disponíveis. Anotações ficam desativadas nelas.
O modo anônimo não oculta a atividade dos sites nem do provedor de internet.

## Bloqueador de anúncios

O bloqueador começa com uma lista local pequena; nenhuma lista pública vem
configurada. É possível informar uma URL HTTPS nas configurações. O parser
aceita arquivos hosts e regras simples como `||dominio^`, incluindo
subdomínios. Não implementa filtros cosméticos nem toda a sintaxe do Adblock
Plus, e não substitui uma extensão completa.

## Segurança

- Endereços, favoritos, histórico e sessão aceitam apenas URLs HTTP(S).
- Consultas ao SQLite usam parâmetros.
- A página inicial local escapa conteúdo dinâmico e não concede acesso a
  arquivos locais para páginas remotas.
- O sandbox do Chromium permanece habilitado.

## Estrutura do projeto

```text
.
├── _APP_/                 Janelas e recursos da interface
├── _APPDATA_/             Pastas e arquivos de dados do usuário
├── _CONFIGURA_/           Textos, temas, cores e atalhos
├── _LOGS_/                Registro de eventos e falhas
├── _THREADS_/             Threads e gerenciamento de execução
├── _ULTILIDADES_/         Ícones e componentes reutilizáveis
├── midias/                Logo do navegador e ícone do aplicativo
├── nucleo/                Documentação do projeto
├── tests/                 Testes automatizados
├── browser.py             Navegação, janelas e perfis
├── video_download.py      Consulta e download de vídeos
├── storage.py             Persistência SQLite
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
