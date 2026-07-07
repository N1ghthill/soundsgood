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

Views nao devem:

- Ler arquivos do disco.
- Controlar GStreamer diretamente.
- Recalcular modelos globais de biblioteca.

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
- Notificacoes e inibicao de suspensao ficam em `Application`, reagindo ao estado publico do `Player`.
