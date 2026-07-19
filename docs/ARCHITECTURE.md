# Arquitetura

SoundsGood deve ser um app GTK4/libadwaita para biblioteca musical local. A arquitetura deve separar claramente reproducao, biblioteca e interface grafica.

## Principios

- Biblioteca local primeiro.
- Sem radio, podcasts ou streaming.
- UI nao deve conter logica pesada de scan, metadados ou playback.
- Modelos devem ser objetos GObject para integrar bem com GTK.
- Views devem consumir `Gio.ListModel`/`Gio.ListStore` e reagir a sinais.
- Reproducao deve ficar isolada em `Player`.
- O backend de biblioteca deve poder evoluir sem reescrever a UI.

## Componentes

### Application

Responsabilidades:

- Inicializar GTK, libadwaita e GStreamer.
- Criar `Library`, `Player` e `Window`.
- Registrar acoes globais e atalhos.
- Receber arquivos de audio abertos pelo desktop/default app e iniciar uma fila temporaria.
- Receber playlists abertas externamente e expandi-las para uma fila temporaria.
- Expor propriedades compartilhadas por `GObject.Property`.

Nao deve:

- Fazer scan de arquivos diretamente.
- Montar widgets complexos.
- Manipular filas de reproducao internamente.

### Library

Responsabilidades:

- Descobrir arquivos de audio no diretorio configurado.
- Extrair metadados.
- Criar e manter modelos de `Song`, `Album` e `Artist`.
- Emitir sinais de scan e atualizacao.
- Fornecer busca.

`Library` e a fachada GObject consumida pela UI. Funcoes puras e testaveis de
cache, playlists e ranking de busca ficam em `soundsgood/catalog`. I/O de scan e
validacao de cache ocorre em worker; apenas a aplicacao do snapshot aos
`Gio.ListStore` ocorre no thread principal.

Neste contexto, `soundsgood/catalog/playlists.py` apenas interpreta arquivos
externos `.m3u`, `.m3u8` e `.pls`. Nao existe armazenamento de playlists
nomeadas na versao 0.1.8.

Dados esperados por faixa:

- `title`
- `artist`
- `album`
- `album_artist`
- `duration`
- `track_number`
- `disc_number`
- `year`
- `genre`
- `url`
- `thumbnail`

Implementacao inicial aceitavel:

- Scan recursivo no diretorio XDG de musicas ou pasta configurada.
- Extracao local de metadados via GStreamer Discoverer.
- Agrupamento em memoria com `Gio.ListStore`.
- Capas por tags embutidas e por arquivos comuns na pasta do album.
- Cache persistente em `$XDG_CACHE_HOME/soundsgood/library.json`, invalidado por `mtime_ns` e tamanho.
- Reabertura rapida a partir do indice em cache quando arquivos e diretorios indexados continuam inalterados.
- Reindexacao manual para reler metadados quando o usuario solicita.
- Monitoramento com `Gio.FileMonitor` e debounce para rescan quando a pasta de musicas muda.
- Aplicacao de snapshot por diff de URI no modelo de faixas.
- Atualizacao incremental dos agregados de albums/artistas quando uma faixa e adicionada, removida ou substituida.
- Estado observavel via `scan_state` e `status_message` para escaneando, vazio, pronto e erro.

Implementacao futura possivel:

- Backend baseado em Tracker/LocalSearch e Grilo, como no GNOME Music.

### Player

Responsabilidades:

- Controlar GStreamer.
- Manter estado atual: parado, carregando, pausado ou tocando.
- Controlar volume, mute, progresso e duracao.
- Gerenciar fila.
- Implementar anterior/proxima.
- Implementar modos de repeticao e aleatorio.
- Emitir sinais de mudanca de faixa, estado e posicao.
- Reiniciar o `playbin` antes de trocar a URI da faixa atual.

API minima sugerida:

```python
class Player(GObject.GObject):
    current_song = GObject.Property(type=object, default=None)
    play_state = GObject.Property(type=int, default=0)
    repeat_mode = GObject.Property(type=int, default=0)
    volume = GObject.Property(type=float, default=1.0)
    mute = GObject.Property(type=bool, default=False)
    position = GObject.Property(type=int, default=0)
    duration = GObject.Property(type=int, default=0)

    def play_song(self, song, playlist=None): ...
    def play_pause(self): ...
    def pause(self): ...
    def stop(self): ...
    def next(self): ...
    def previous(self): ...
    def seek(self, position): ...
```

### Models

Os modelos atuais estao em `soundsgood/models.py` e devem continuar simples.

Regras:

- `Song.url` e a identidade primaria de uma faixa.
- `Album` deve agrupar por `album` + `album_artist`.
- `Artist` deve representar artista de faixa ou album artist conforme a view.
- `LibraryState` representa o estado observavel da biblioteca: vazio, escaneando, pronto ou erro.
- Duracoes devem ser em segundos.
- Numeros de faixa e disco devem ser inteiros.

### Integracao com o desktop

- `MprisService` publica estado e transporte para os controles de midia.
- `BackgroundController` decide se fechar a janela oculta ou encerra o app,
  possui o `GApplication.hold()` e solicita permissao de segundo plano quando
  o portal esta disponivel.
- `StatusNotifierService` registra item e menu D-Bus somente quando existe um
  watcher compativel. Ele nao e requisito de execucao nem substitui MPRIS,
  notificacoes ou o lancador.
- A acao explicita `Quit`, vinda da aplicacao, MPRIS ou bandeja, deve liberar o
  hold e executar todo o teardown.

### Window e Views

Estrutura sugerida:

- `Window`: janela principal, navegacao e composicao das views.
- `AlbumsView`: grid de albums e detalhe de album.
- `ArtistsView`: lista de artistas e painel de detalhes com albums agrupados.
- `SongsView`: lista de faixas.
- `SearchView`: busca global com secoes de artistas, albums e musicas.
- `PlayerToolbar`: controles de reproducao.
- `PlayerToolbar` tambem contem o popover da fila atual, com selecao, remocao por item e limpeza.
- `MprisService`: interface DBus MPRIS para controles do sistema.

Views devem:

- Receber `application`, `library` ou `player` por injecao.
- Conectar sinais/propriedades.
- Criar factories GTK para listas/grids.
- Chamar metodos publicos do `Player` para iniciar reproducao.
- Usar `Gtk.ListView`/`Gtk.GridView` e factories para colecoes potencialmente grandes.
- Desconectar sinais no `unbind`/`teardown` da factory ou no `unroot` do widget.
- Adaptar composicao por breakpoints, incluindo navegacao sequencial de artistas em telas estreitas.

### Sistema visual

O estilo da aplicacao fica centralizado em `soundsgood/style.css`. Widgets
adicionam classes semanticas em vez de repetir CSS ou tamanhos locais:

- `compact-icon`: acao secundaria de icone, com alvo visual de 28 px.
- `row-play`: reproducao contextual dentro de listas.
- `primary-play`: controle principal circular do player.
- `compact-pill`: acao textual curta, como Play, Select ou Rescan.
- `album-tile`, `song-item` e `detail-header`: densidade e superficies de
  conteudo.

Controles devem manter tooltip e nome acessivel mesmo quando forem apenas
icones. Botoes em `Gtk.Box` horizontal devem usar alinhamento vertical central
para nao crescer com capas ou cabecalhos vizinhos. Novos tamanhos fixos so sao
aceitaveis para arte ou limites de popover; layout e navegacao continuam
responsivos.

Views nao devem:

- Ler arquivos do disco.
- Controlar GStreamer diretamente.
- Recalcular modelos globais de biblioteca.

## Playlists Persistentes Planejadas

A fila do `Player` e transitoria e representa apenas a sequencia em execucao.
Uma playlist salva deve ser um conceito separado, pertencente ao catalogo.

Direcao aprovada para a Fase 6 do roadmap:

- `Playlist` possui identificador estavel, nome e entradas ordenadas.
- Entradas referenciam a URI canonica da faixa e preservam informacao suficiente
  para diagnosticar arquivos ausentes.
- Persistencia fica em `$XDG_DATA_HOME/soundsgood`, com formato versionado,
  migracao testada e substituicao atomica.
- Importacao e exportacao ficam em helpers puros do catalogo; widgets nao fazem
  I/O direto.
- Carregar uma playlist cria ou altera a fila somente por metodos publicos do
  `Player`.
- Remover ou reordenar uma playlist salva nao muda silenciosamente a fila que
  ja estiver tocando.
- Falhas parciais e arquivos ausentes sao estados recuperaveis e aparecem nos
  diagnosticos.

## Dados e Ordenacao

Ordenacao recomendada:

- Albums: `album_artist`, `year`, `album`.
- Artistas: nome normalizado.
- Faixas de album: `disc_number`, `track_number`, `title`.
- Faixas globais: `album_artist`, `album`, `disc_number`, `track_number`, `title`.

Busca:

- Normalizar caixa e acentos quando possivel.
- Procurar em titulo, artista, album e album artist.
- Ordenar resultados por relevancia simples: correspondencia exata, prefixo e depois substring.
- Retornar resultados como `Gio.ListStore` ou modelo filtrado.

## Recursos GTK

Estado atual: o MVP usa UI programatica em Python. Os templates `.ui` antigos foram removidos para evitar divergencia entre runtime e recursos instalados. O bundle `data/soundsgood.gresource.xml` tambem foi removido porque estava vazio.

Se templates `.ui` forem reintroduzidos:

- Atualizar `data/meson.build`.
- Recriar/atualizar `data/soundsgood.gresource.xml`.
- Garantir que o nome do template corresponda ao `__gtype_name__` da classe Python.

## GSettings

Configuracoes atuais:

- `repeat`
- `volume`
- `mute`
- `window-width`
- `window-height`
- `window-maximized`
- `music-dir`
- `color-scheme`
- `enable-notifications`
- `inhibit-suspend`
- `run-in-background`

Use GSettings para preferencias persistentes. Nao use arquivos ad hoc de configuracao enquanto GSettings resolver o caso.

## Dependencias

Dependencias centrais:

- Python 3.10+
- PyGObject
- GTK4
- libadwaita
- GStreamer
- Meson/Ninja

Dependencias a avaliar:

- `mutagen` ou `tinytag` para tags de audio.
- Tracker/LocalSearch + Grilo para backend mais parecido com GNOME Music.

## Decisoes Atuais

- O app sera local-first.
- Radio esta fora de escopo.
- O MVP pode usar scan manual de diretorio, mas nao deve depender de nomes de arquivo como fonte final de metadados.
- A UI deve seguir padroes GNOME/libadwaita.
- Antes de adicionar features novas, a aplicacao precisa inicializar, listar musicas e tocar uma faixa.
- MPRIS usa ID de faixa deterministico derivado da URI por SHA-256.
- O app reabre pelo indice em cache quando os arquivos conhecidos e diretorios indexados nao mudaram; quando ha mudanca detectada, troca de pasta ou cache antigo, faz rescan completo.
- A acao manual de reindexacao força rescan e releitura de metadados.
- Playlists `.m3u`, `.m3u8` e `.pls` sao aceitas no fluxo externo de abertura, mas nao sao indexadas como parte da biblioteca.
- Criacao e persistencia de playlists pertencem a uma fase futura; ate la,
  documentacao e UI devem chamar o estado atual de fila de reproducao.
- Notificacoes e inibicao de suspensao ficam em `Application`, reagindo ao estado publico do `Player`.
- `BackgroundController` possui o `GApplication.hold()` usado ao ocultar a
  janela e separa fechar/ocultar da acao explicita de sair.
- O StatusNotifier e complementar: registra-se somente quando ha um watcher
  compativel e nunca substitui lancador, MPRIS ou notificacoes.
- Detalhes de album e artista usam `Gio.ListStore` e factories; nenhuma colecao
  de faixas potencialmente grande deve ser materializada como `Gtk.ListBox`.
