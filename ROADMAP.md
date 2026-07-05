# Roadmap

Este roadmap prioriza um player local estavel antes de recursos avancados. O criterio principal e aproximar a organizacao e a experiencia do GNOME Music, mantendo o escopo sem radio, podcasts ou streaming.

## Fase 0: Base Executavel

Objetivo: fazer o projeto abrir uma janela GTK e tocar um arquivo local.

Status: MVP inicial implementado.

- [x] Criar os modulos ausentes importados por `soundsgood/application.py`.
- [x] Corrigir referencias de recursos ausentes em `data/meson.build` e `data/soundsgood.gresource.xml`.
- [x] Implementar `Window` com stack principal: Albums, Artists, Songs e Search.
- [x] Implementar `Player` com GStreamer `playbin`.
- [x] Conectar acoes globais: play/pause, anterior, proxima, volume, mute, repeat e shuffle.
- [x] Exibir `PlayerToolbar` quando houver musica selecionada.
- [x] Usar diretorio XDG de musicas como padrao.
- [x] Exibir thumbnails de album quando disponiveis.
- [x] Abrir detalhe de album com faixas ordenadas.
- [x] Reproduzir musica por linha, album, artista e resultado de busca.
- [x] Destacar faixa atual nas listas.
- [x] Corrigir troca de faixa no GStreamer reiniciando o `playbin` antes de aplicar nova URI.
- [x] Remover templates `.ui` antigos nao usados pelo runtime.
- [x] Garantir que o app inicialize sem `ImportError`.
- [x] Validar build com Meson e execucao via `local-soundsgood`.

Entregavel: aplicacao abre, lista musicas encontradas e reproduz uma faixa.

## Fase 1: Biblioteca Local Confiavel

Objetivo: organizar musicas usando metadados reais, nao nomes de arquivo.

- [x] Usar leitura de tags com GStreamer Discoverer.
- [x] Manter fallback por nome/pasta quando tags estiverem incompletas.
- [x] Capturar titulo, artista, album artist, album, faixa, disco, ano, genero, duracao e capa quando disponiveis.
- [x] Usar URIs corretas com `Path(...).resolve().as_uri()`.
- [x] Ordenar albums por artista/ano/titulo e faixas por disco/faixa/titulo.
- [x] Usar diretorio XDG de musicas como padrao.
- [x] Usar capas embutidas e arquivos de capa na pasta.
- [x] Persistir cache de biblioteca para evitar redescoberta de metadados em arquivos inalterados.
- [x] Monitorar mudancas na pasta de musicas e agendar rescan com debounce.
- [x] Evitar duplicatas por URI durante aplicacao de snapshots de scan.
- [x] Atualizar contagens de albums e musicas de forma incremental.
- [x] Adicionar sinalizacao de estado: escaneando, vazio, erro e pronto.
- Evitar percurso completo da arvore de arquivos a cada abertura.
- [x] Atualizar faixas por diff de URI sem limpar todo o modelo de musicas.
- [x] Atualizar agregados de albums/artistas sem recalculo completo.

Alternativas futuras:

- Caminho simples: usar GStreamer Discoverer, `mutagen` ou `tinytag`.
- Caminho mais alinhado ao GNOME: usar Tracker/LocalSearch + Grilo.

Decisao atual: o MVP usa GStreamer Discoverer e scan local. Manter a interface `Library` isolada para permitir trocar para Tracker/LocalSearch + Grilo no futuro, se valer a pena.

## Fase 2: Navegacao e Busca

Objetivo: reproduzir a experiencia central de biblioteca do GNOME Music.

- [x] Tela de albums com grid responsivo.
- [x] Tela de artistas com lista lateral e detalhes do artista.
- [x] Tela de faixas com lista densa.
- [x] Tela de album com capa, metadados e faixas ordenadas.
- [x] Busca global por titulo, artista e album.
- [x] Busca com normalizacao simples de acentos e ranking basico de relevancia.
- [x] Separar resultados de busca por tipo: musicas, albums e artistas.
- [x] Acionamento de item: tocar faixa, album ou artista.
- [x] Estado vazio basico.
- [ ] Agrupar faixas por disco visualmente nos detalhes de album/artista.
- [ ] Adicionar selecao de pasta pelo estado vazio.
- [ ] Melhorar responsividade em telas estreitas.

Entregavel: usuario consegue navegar, procurar e iniciar reproducao pela biblioteca.

## Fase 3: Fila e Experiencia de Player

Objetivo: tornar a reproducao previsivel e confortavel.

- [x] Implementar fila de reproducao.
- [x] Suportar play de album inteiro, artista inteiro e resultado de busca.
- [x] Implementar proxima/anterior com modos `none`, `song`, `all` e `shuffle`.
- [x] Exibir progresso real e permitir seek.
- [x] Persistir volume, mute e modo de repeticao em GSettings quando schema estiver disponivel.
- [x] Atualizar icones e labels conforme estado do player.
- [x] Tratar fim da faixa e erros de GStreamer.
- [x] Mostrar fila atual em um popover.
- [x] Suportar limpar fila.
- [x] Suportar remover itens individuais da fila.
- [ ] Testar comportamento de shuffle/repeat com colecoes reais.

Entregavel: player usavel no dia a dia para biblioteca local.

## Fase 4: Acabamento GNOME

Objetivo: melhorar integracao com desktop e polimento visual.

- [x] Dialogo de preferencias para pasta de musica.
- [x] About dialog funcional.
- [x] CSS minimo e coerente com libadwaita.
- [x] Atalhos de teclado basicos.
- [x] Capa de album com cache local para capas embutidas.
- [x] MPRIS para controles do sistema.
- [x] Refinar capacidades MPRIS e validar `PlaybackStatus`, `Metadata`, `Pause` e `Play` durante reproducao via `gdbus`.
- [ ] Inibir suspensao durante reproducao.
- [ ] Notificacoes opcionais para faixa atual.
- [ ] Refinar layout mobile/estreito.
- [ ] Melhorar acessibilidade: labels, tooltips e navegacao por teclado.

Entregavel: experiencia consistente com apps GNOME modernos.

## Fase 5: Qualidade e Distribuicao

Objetivo: estabilizar o projeto para uso e empacotamento.

- [x] Testes unitarios para modelos, biblioteca e fila.
- [x] Testes unitarios basicos para biblioteca, busca e player.
- [x] Testes unitarios para cache persistente e logica MPRIS.
- [x] Testes manuais documentados para UI, playback e MPRIS.
- [x] Validacao de schemas, desktop file, metainfo e recursos.
- [x] Flatpak manifest inicial.
- CI para lint, build e testes.
- [x] Documentacao inicial de empacotamento Flatpak.
- Revisar se `data/soundsgood.gresource.xml` ainda e necessario sem templates `.ui`.

Entregavel: app empacotavel e sustentavel.

## Fora de Escopo

- Radio.
- Podcasts.
- Streaming.
- Login em servicos externos.
- Sincronizacao com nuvem.
- Download automatico de musicas.
- Edicao completa de tags.

## Prioridade Atual

1. Melhorar responsividade e acessibilidade das views.
2. Implementar notificacoes e inibicao de suspensao durante reproducao.
3. Validar controles de midia do shell em uma sessao GNOME real com a UI aberta.
4. Avaliar indice persistente para evitar percorrer toda a arvore de musicas a cada abertura.
5. Agrupar faixas por disco visualmente nos detalhes de album/artista.
6. Preparar CI para lint, build e testes.

## Como Retomar

- Comece lendo `agent.md`, este roadmap e `docs/ARCHITECTURE.md`.
- Rode `python3 -m unittest discover -s tests` antes de mexer em comportamento existente.
- Para mudancas de UI/playback, use `docs/MANUAL_TESTS.md`.
- O proximo trabalho recomendado e responsividade/acessibilidade das views. Para MPRIS, ainda vale validar controles de midia do shell em uma sessao GNOME real com a UI aberta.
