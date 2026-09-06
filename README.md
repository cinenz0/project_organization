# Central — Python File Organizer

Organize files from different source directories into one persistent central
folder. The Windows executable includes Python. The command-line interface
requires Python 3.10 or newer and uses only its standard library.

## Interface desktop (Windows)

Abra o atalho **Central** na Área de Trabalho com duplo clique. A interface abre
em uma janela própria, sem aba do navegador nem terminal. O aplicativo instalado
fica em `%LOCALAPPDATA%\Programs\Central\Central.exe` e inclui seu próprio Python.
Ele usa Microsoft Edge WebView2 e .NET Framework 4.6.2+ do Windows, já disponíveis
no computador validado. Não é necessário instalar pacotes Python para usá-lo.

Para executar a partir do código, instale as dependências no ambiente do projeto
e use `Abrir Central.pyw` ou:

```powershell
.\.venv\Scripts\python.exe desktop.py
```

1. Em **Pasta central**, clique em **Escolher pasta** e confirme o destino.
   Ele será salvo para as próximas aberturas. Na instalação inicial, a configuração
   existente do projeto é copiada, incluindo o destino antigo com `Documents`.
2. Em **Origem**, escolha a pasta a organizar. Os arquivos e destinos aparecem
   automaticamente na revisão. Cancelar o seletor mantém a seleção anterior.
3. Confira os nomes e clique em **Mover arquivos**. Somente os arquivos incluídos
   naquela revisão serão movidos. **Atualizar prévia** inclui arquivos que
   chegaram depois. Se um arquivo revisado mudar, a aplicação pede nova revisão.
4. O resultado distingue arquivos movidos, itens mantidos e falhas. **Tentar
   novamente** atua somente sobre falhas de cópia seguras. Uma cópia já concluída
   cujo original não pôde ser removido não é copiada novamente por esse botão.
5. Use **Organizar outra pasta** para continuar com a mesma central. Ao terminar,
   clique em **Encerrar** ou no **X** da janela. Ambos encerram o aplicativo.

A interface e os arquivos permanecem locais; o servidor aceita conexões apenas
em `127.0.0.1`, com porta e sessão próprias a cada abertura. A interface não exige
internet nem Tk. A execução funciona em segundo plano enquanto
a tela informa o andamento; não há porcentagem estimada nem cancelamento no meio
da cópia. O encerramento é bloqueado enquanto há operação ou seleção de pasta ativa.

Evite editar ou reorganizar os mesmos arquivos em outros programas durante uma
movimentação. A verificação da prévia não substitui um bloqueio de arquivos pelo
sistema operacional. Não há desfazer automático. A interface desktop destina-se
ao Windows; a CLI abaixo é preservada.

As preferências do aplicativo instalado ficam em `%LOCALAPPDATA%\Central\config.json`,
fora do executável. A CLI e a execução pelo código continuam usando o `config.json`
do projeto; depois da cópia inicial, essas configurações são independentes.

## Configure your central folder once

Run these commands from the directory containing `main.py`:

```powershell
python main.py --set-central "D:\Documentos"
```

This saves the destination without moving any files. The selected folder is the
category root: PDFs go to `D:\Documentos\PDF`, images to
`D:\Documentos\Images`, and so on. No extra `Documents` folder is appended.
The folder can be new; it is created when files are actually organized.

## Preview, then organize

```powershell
python main.py --source "C:\Users\YourName\Downloads" --dry-run
python main.py --source "C:\Users\YourName\Downloads"
python main.py --source "C:\AnotherFolder"
```

Each source uses the same saved central folder. Only files directly inside the
source are considered; subdirectories are not scanned recursively. Unknown
extensions and symbolic links are skipped. Extensions are case-insensitive.

`--dry-run` lists planned destinations and a summary without creating folders,
changing configuration, or moving files. It cannot be combined with options
that save configuration. Each normal run reports moved, skipped, and failed
files. Failures produce a nonzero exit code.

## Other options

```powershell
# Use another central folder for this run only.
python main.py -s "C:\Incoming" -d "D:\OtherDocuments"

# Save the selected source and central folder, then organize.
python main.py -s "C:\Incoming" -d "D:\Documentos" --set-default

# Interactive mode; reuse the saved central folder.
python main.py

python main.py --help
```

Source paths must be existing directories. Source and central folder must be
different. If no central folder has been configured, choose one explicitly
with `--set-central`, `--destination`, or the interactive setup.

## File preservation

An existing destination file is never intentionally overwritten. Name collisions
receive numbered prefixes, such as `1_report.pdf`, `2_report.pdf`. Files are
copied to an exclusively created destination before their source is removed;
this works across drives. A failed operation is reported, and processing
continues with the other files. If removing the source fails after copying,
both copies are preserved and the operation is reported as a failure.

Avoid editing files while they are being organized. An interrupted run can leave
a partial destination copy; the original is retained until copying completes.
There is no automatic undo or migration of files organized by earlier versions.

## Configuration and customization

`config.json` lives beside `default_paths.py`, regardless of the shell's working
directory. Configuration is read without writing it. Invalid configuration
produces an explicit error instead of being silently replaced.

The `source path` setting stores the default source. The `central path` setting
stores the direct category root. For compatibility, an old `destination path`
is interpreted as `<destination path>/Documents` until a new central folder is
explicitly saved. This preserves the old effective destination. For example,
an old destination `D:\` continues to target `D:\Documents`.

Edit `data_dict.py` to customize categories and extensions. Extensions must begin
with a dot. Category names must be single folder names. Current categories are
PDF, Excel, PowerPoint, Word, Images, Video, Audio, Zipped, and Calendar.

## Development

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\build-app.ps1
.\install-app.ps1
```

O build gera `dist\Central\Central.exe` com os recursos em `_internal`. Distribua
a pasta `dist\Central` inteira. O script de instalação copia esse pacote para
o usuário atual e cria o atalho; ele preserva preferências existentes e recusa
sobrescrever uma instalação ou atalho já presentes.

```powershell
python -B -m unittest discover -s tests -v
.\dist\Central\Central.exe --smoke-test app-smoke-exe.json
```

Tests use temporary directories and do not organize personal files. The opt-in
executable smoke test opens a hidden WebView2 window, clicks through a disposable
file movement, verifies the real result and closes the application. Its JSON
report records the checks. Normal double-click launch does not run this test.

- `main.py`: application flow and output.
- `paths.py`: command-line arguments, interactive input, and path validation.
- `default_paths.py`: persistent settings.
- `organize_by_suffix.py`: classification, planning, and file movement.
- `data_dict.py`: category definitions.
- `desktop.py`: loopback HTTP server, hosted inside the application.
- `app_window.py`: Windows window, user settings location and shutdown lifecycle.
- `app_smoke.py`: opt-in packaged application check with disposable documents.
- `Central.spec`, `build-app.ps1`: executable packaging and validation.
- `install-app.ps1`: current-user installation and Desktop shortcut.
- `requirements-desktop.txt`, `requirements-build.txt`: desktop/build dependencies.
- `native_folders.py`: Windows Common Item Dialog through standard-library ctypes.
- `desktop_service.py`: reviewed plans, stale-file checks and selective recovery.
- `ui/`: real HTML/CSS/JavaScript interface based on the approved desktop v3.
- `Abrir Central.pyw`: desktop entry point without a terminal window.
- `paths 1.py`: compatibility import for the former duplicate module.

Design decisions: keep the standard-library CLI, separate configuration from
organization, reuse one explicit central folder, preserve legacy destination
semantics, and provide a preview before movement.

Desktop validation includes temporary-directory service and HTTP tests, session
and origin checks, native Windows dialog initialization without showing it, and
browser smoke tests using disposable files. Interactive folder selection is wired
to the native dialog; automated browser smoke tests substitute only the selector
and never use personal folders. The COM integration follows Microsoft's
[Common Item Dialog documentation](https://learn.microsoft.com/windows/win32/shell/common-file-dialog).
