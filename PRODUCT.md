---
type: project
domain: projects
status: active
created: 2026-09-05
updated: 2026-09-05
---

# Product — Python File Organizer

<!-- impeccable:product-schema 1 -->

## Platform

desktop

Aplicativo Windows com janela própria e seletor nativo de pastas. A CLI Python
continua disponível. O usuário aprovou o desktop v3 e sua implementação em
2026-09-05; em seguida solicitou um aplicativo aberto pelo atalho na Área de Trabalho.

## Stack

- Aplicação existente: Python 3.10+, biblioteca padrão, CLI e configuração JSON.
- Interface real: HTML/CSS/JavaScript em `ui/`, servidos por Python em loopback.
- Janela própria: pywebview com WebView2; executável empacotado com PyInstaller.
- Seleção de pastas: Windows Common Item Dialog via `ctypes`, sem dependências.
- Inicializador instalado: atalho Central → `%LOCALAPPDATA%\Programs\Central\Central.exe`.
- Preferências instaladas: `%LOCALAPPDATA%\Central\config.json`, separadas do pacote.
- Código-fonte: `Abrir Central.pyw` ou `python desktop.py`, com dependências desktop.
- O esboço aprovado permanece separado, como referência visual histórica.

## Users

O solicitante precisa organizar arquivos de diferentes pastas do computador
em um destino central consistente. Público adicional, distribuição comercial
e necessidades de múltiplos usuários não foram definidos.

## Product Purpose

Permitir que a pessoa escolha uma pasta central uma vez e organize sucessivas
pastas de origem em categorias dentro dela, sem criar uma nova pasta de
documentos em cada origem.

O resultado verificável é encontrar arquivos de várias origens em uma mesma
central, com destinos compreensíveis e arquivos existentes preservados.

## Operating Context

O projeto é desenvolvido em Windows. O fluxo confirmado é definir a central,
selecionar a origem, revisar a prévia e executar a organização. Novas rodadas
reutilizam a central salva. A pasta de origem e a central têm funções distintas.

A implementação usa os arquivos reais da origem selecionada. O usuário escolhe
origem e central por cliques; não há campo para digitar caminhos. A prévia é
atualizada após a seleção. Resultados e tentativas de recuperação respeitam as
operações efetivamente executadas. O foco aprovado é desktop; trabalho específico
para mobile e auditoria ampla de acessibilidade ficaram fora desta etapa.

## Capabilities and Constraints

- Pasta central persistente; categorias são criadas diretamente dentro dela.
- Origem variável e destino alternativo por execução na CLI.
- Prévia sem movimentação nem gravação de configuração.
- Organização somente dos arquivos diretamente na origem, sem recursão.
- Classificação por extensão, sem distinção entre maiúsculas e minúsculas.
- Arquivos sem categoria e links simbólicos são preservados na origem.
- Colisões recebem prefixos numéricos; o arquivo existente é preservado.
- Na execução real, os arquivos movidos deixam a origem após a cópia terminar.
- Falhas são reportadas; falha ao remover a origem preserva ambas as cópias.
- Configuração antiga preserva seu destino efetivo com a pasta Documents.
- Não há desfazer automático nem migração automática de pastas antigas.
- Nomes como Images e PowerPoint são nomes reais das categorias atuais;
  não traduzi-los silenciosamente na interface.
- Não foi solicitada sincronização, publicação ou transferência para nuvem.

## Brand Commitments

O projeto se chama Python File Organizer na documentação existente.
Central é o nome provisório apresentado no esboço, não uma decisão de marca.
A interface de demonstração está em português. Não há compromisso confirmado
com marca final, paleta, tipografia ou tema fixo.

## Evidence on Hand

- [README.md](README.md): uso, regras, compatibilidade e decisões técnicas.
- [data_dict.py](data_dict.py): categorias existentes.
- [tests](tests): testes de configuração, organização, preservação e integração.
- Protótipo original e versão refinada estão na pasta de visualizações desta
  conversa, fora da aplicação. Não representam documentos reais do usuário.

## Product Principles

1. Manter uma central estável enquanto as origens mudam.
2. Mostrar as consequências antes de mover arquivos.
3. Preservar arquivos existentes e comunicar exceções de forma específica.
4. Distinguir o que foi movido do que permaneceu na origem.
5. Preservar o esboço aprovado como referência e distinguir dados de teste de
   operações reais.

## Estado e decisões da implementação

- Interface conectada ao organizador, com estados de carregamento, configuração
  incompleta, pasta indisponível, revisão, resultado e falha parcial.
- Uma prévia identifica os arquivos e destinos revisados; a execução não inclui
  arquivos que chegaram depois e revalida cada arquivo antes de iniciar sua cópia.
- Cópias completas com original preservado são reportadas separadamente e ficam
  excluídas da repetição automática de falhas.
- Testes de movimentação e smoke tests no navegador usam pastas temporárias.
- Aplicativo empacotado com Python, com encerramento da janela vinculado ao serviço
  e bloqueio de fechamento durante operações. A interface aprovada foi preservada.
- A instalação inicial copia as preferências existentes sem alterar o arquivo da
  CLI. As preferências instaladas evoluem separadamente a partir dessa cópia.
- Validação inclui 68 testes e teste do executável em WebView2 com documentos
  descartáveis, passando por revisão, movimentação, resultado e encerramento.
- Próxima ação: uso do aplicativo pelo atalho Central na Área de Trabalho.

## Open Decisions

- Nome definitivo e eventuais compromissos de marca.
- Público além do solicitante.
- Distribuição pública, assinatura digital e atualização automática.
- Eventuais requisitos futuros além do escopo desktop aprovado.

Este registro reúne o contexto confirmado da conversa e da aplicação.
As escolhas deixadas em aberto não foram preenchidas por silêncio.
