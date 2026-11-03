# hen-Nave

Navegador desktop independente feito em Python, PySide6 e QtWebEngine
(Chromium embutido). O projeto foi organizado para rodar no computador do
usuário; o preview web da Replit não consegue exibir uma janela desktop Qt.

## Estrutura

```text
hen-Navi/
├── main.py
├── browser.py
├── storage.py
├── startpage.py
├── dialogs.py
├── utils.py
├── requirements.txt
├── README.md
├── _APP_/
│   ├── main_window.py
│   └── Navegador/
│       ├── __init__.py
│       └── abas.py
├── _APPDATA_/
├── _CONFIGURA_/
├── _LOGS_/
├── _THREADS_/
├── _ULTILIDADES_/
├── nucleo/
│   └── _DOC_PROJETO.txt
└── tests/
    ├── test_startpage.py
    ├── test_storage.py
    └── test_utils.py
```

## Instalar e iniciar

Use Python 3.10 ou superior. Comandos abaixo devem ser executados nesta pasta
do projeto.

### Windows (PowerShell)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -r requirements.txt
python main.py
```

### Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
python main.py
```

Se o Linux mostrar erro de plataforma gráfica (por exemplo, plugin `xcb`
ausente), instale as bibliotecas Qt/X11 exigidas pela distribuição. O pacote
PySide6 inclui QtWebEngine, mas não substitui todos os componentes gráficos do
sistema operacional.

### macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
python main.py
```

O Chromium embutido é atualizado junto com o PySide6. Atualize a dependência
periodicamente com `python -m pip install -U PySide6`; para repetir a instalação
com o conjunto de dependências do projeto, use `python -m pip install -U -r requirements.txt`.

## Dados locais

O aplicativo guarda dados em `~/.hen-nave/` (no Windows, dentro da pasta do
perfil do usuário):

- cookies e armazenamento persistente do perfil WebEngine;
- cache do navegador e os arquivos HTML da página inicial;
- `config/config.json`, `config/sessao.json` e o banco `config/hen-nave.sqlite3`;
- logs em `logs/`.

Downloads são salvos inicialmente na pasta Downloads do sistema, mas o diálogo
permite escolher outro local.

## Recursos e atalhos

- Aba `Principal` fixa no índice zero; não pode ser fechada nem arrastada.
- `+` ou `Ctrl+T`: nova página inicial em uma aba.
- `Alt+Home`: atualiza e volta à aba Principal.
- Barra de endereço: URL HTTP(S), domínio, localhost/IP ou busca DuckDuckGo.
- `Ctrl+L`: focar e selecionar a barra de endereço.
- `Ctrl+H`: histórico; duplo clique abre em nova aba.
- `Ctrl+Shift+O`: favoritos; duplo clique abre em nova aba.
- `Ctrl+D`: adicionar/remover favorito.
- `Ctrl+N`: nova janela; `Ctrl+Shift+N`: nova janela anônima.
- `Ctrl+W`: fechar aba atual, exceto a Principal.
- `Ctrl+F`: localizar nesta página; `F5`: recarregar.
- `Ctrl+=`, `Ctrl+-`, `Ctrl+0`: aumentar, diminuir e restaurar zoom.
- O menu `☰` reúne histórico, favoritos, janelas, localizar, zoom,
  limpeza do histórico e informações do aplicativo.

Sessões normais são salvas no SQLite e restauradas ao iniciar, selecionando a
aba Principal. Janelas anônimas usam um perfil off-the-record em memória e não
salvam histórico nem sessão. A navegação anônima não esconde atividade dos
sites ou do provedor; ela apenas evita salvar os dados desta sessão neste
computador.

## Segurança e limitações

- A barra não executa `javascript:` nem esquemas digitados que não sejam
  HTTP(S); esses textos viram buscas.
- Favoritos, histórico e sessão aceitam somente URLs HTTP(S); consultas SQLite
  usam parâmetros.
- A página inicial é HTML local, escapa conteúdo salvo e não habilita acesso de
  arquivos locais a páginas remotas.
- O sandbox do Chromium permanece habilitado no código. Não há configuração
  de `--no-sandbox` para o navegador no computador do usuário.
- Se uma execução isolada na Replit falhar especificamente porque o ambiente
  headless exige desativar o sandbox, isso deve ser feito somente na
  configuração de execução da Replit, por exemplo em `[env]` no `.replit`:
  `QTWEBENGINE_CHROMIUM_FLAGS = "--no-sandbox"`. Essa exceção é exclusiva do
  ambiente Replit e não deve ser usada no computador do usuário nem incluída
  no código do aplicativo.
- Não há Navegação Segura do Google, extensões do Chrome ou gerenciador de
  senhas nesta versão.
- O modo anônimo não oculta o tráfego de sites, rede local, empregador ou
  provedor de internet.

## Testes sem interface

```bash
python -m unittest discover -s tests -v
python -m compileall -q .
```

Os testes cobrem resolução de endereços, gravação e filtragem SQLite, sessões,
favoritos, deduplicação de recentes e escape do HTML. Eles não substituem um
teste manual das janelas e do Chromium na plataforma desktop do usuário.
