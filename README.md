# SoundsGood

SoundsGood e um player de musica local para Linux, inspirado na experiencia do GNOME Music. O foco do projeto e tocar e organizar musicas locais por album, artista e faixas, com uma interface GTK moderna.

O projeto nao deve incluir radio, podcasts, streaming ou fontes remotas como requisito de produto. Qualquer dependencia ou arquitetura importada do GNOME Music deve ser avaliada pelo valor que traz para biblioteca local, metadados, busca ou reproducao.

## Objetivos

- Interface grafica em GTK4/libadwaita.
- Biblioteca local com musicas agrupadas por albums, artistas e faixas.
- Busca por titulo, artista e album.
- Reproducao via GStreamer.
- Controles de player: play/pause, anterior, proxima, progresso, volume, repeticao e aleatorio.
- Leitura confiavel de metadados reais dos arquivos.
- Sem radio, podcasts ou streaming.

## Estado Atual

O repositorio tem um MVP funcional em Python/GTK4/libadwaita. A aplicacao abre uma janela, escaneia a pasta de musicas configurada pelo XDG, organiza faixas por albums e artistas, oferece busca basica e reproduz audio via GStreamer.

Recursos ja implementados:

- Diretorio padrao de musicas via `xdg-user-dir MUSIC`, incluindo ambientes pt-BR como `~/Musicas` ou `~/Músicas`.
- Tela de albums com grid, detalhe de album, capa, metadados, botao Play e faixas ordenadas.
- Tela de artistas com lista lateral, cabecalho do artista, albums agrupados e faixas por album.
- Tela de musicas com lista global.
- Busca por titulo, artista, album, album artist, genero e ano, com normalizacao simples de acentos.
- Resultados de busca separados por artistas, albums e musicas.
- Reproducao com fila, anterior/proxima, play/pause, seek, volume, repeat e shuffle.
- Popover de fila atual na toolbar, com selecao de faixa, remocao individual e limpeza da fila.
- MPRIS em `org.mpris.MediaPlayer2.SoundsGood` com metadata, estado de playback, capacidades de transporte e controles basicos via DBus.
- Destaque visual da faixa atual nas listas.
- Troca de faixa corrigida com reinicio seguro do `playbin`.
- Capas embutidas via GStreamer quando disponiveis e fallback por arquivos como `cover.jpg`, `folder.png`, `front.jpg`, `album.png` e similares.
- Cache persistente da biblioteca em `$XDG_CACHE_HOME/soundsgood/library.json`.
- Monitoramento simples da pasta de musicas com debounce para reescanear quando arquivos mudam.
- Scan aplica diferencas por URI para adicionar, substituir e remover faixas sem limpar todo o modelo de musicas.
- Agregados de albums/artistas sao atualizados incrementalmente quando faixas entram, saem ou mudam de metadados.
- Estados explicitos de biblioteca: escaneando, vazio, pronto e erro, com feedback quando a pasta configurada nao existe.
- UI principal programatica em Python; templates `.ui` antigos foram removidos.
- Testes unitarios para biblioteca, cache persistente, busca, player e logica MPRIS registrados no Meson.
- App ID preparado para Flathub: `io.github.n1ghthill.soundsgood`.
- Manifest Flatpak inicial em `io.github.n1ghthill.soundsgood.yml`.

Pontos conhecidos:

- A biblioteca ja tenta ler metadados e capas embutidas com GStreamer Discoverer, mas ainda precisa de mais testes com colecoes reais.
- Capas por arquivo de pasta como `cover.jpg`, `folder.png` e similares ja sao usadas.
- O cache evita redescobrir metadados de arquivos inalterados, mas o app ainda percorre a arvore de arquivos a cada abertura.
- O monitoramento atual agenda um novo scan; faixas e agregados sao aplicados por diff, mas o app ainda nao usa um indice persistente para evitar listar a arvore.
- Notificacoes e inibicao de suspensao ainda nao foram implementados.
- O build Meson/Ninja local foi validado com `./builddir/local-soundsgood`.

Ultima validacao conhecida:

- `python3 -m unittest discover -s tests`: 27 testes OK.
- `python3 -m py_compile soundsgood/*.py soundsgood/views/*.py soundsgood/widgets/*.py tests/*.py`: OK.
- `meson setup builddir --reconfigure`: OK.
- `meson compile -C builddir`: OK.
- `meson test -C builddir`: OK.
- MPRIS via `gdbus`: `Identity=SoundsGood`, `PlaybackStatus=Stopped`, `Metadata=NoTrack` sem faixa atual.
- MPRIS durante reproducao com WAV sintetico: `PlaybackStatus=Playing`, metadata preenchida, `CanPlay`, `CanPause` e `CanSeek` verdadeiros, `Pause` e `Play` funcionando via DBus.

## Arquitetura Pretendida

Camadas principais:

- `Application`: inicializa GTK/libadwaita, configuracoes, biblioteca e player.
- `Library`: descobre musicas locais, extrai metadados e mantem modelos de faixas, albums e artistas.
- `Player`: controla GStreamer, fila, estado de reproducao, progresso, volume e modos de repeticao.
- `Models`: objetos GObject para `Song`, `Album`, `Artist` e enums de player.
- `Views`: telas de albums, artistas, faixas, busca e detalhes de album/artista.
- `Widgets`: componentes reutilizaveis como toolbar do player, linhas de musica, busca e dialogs.

Veja detalhes em [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

O roteiro de validacao manual fica em [docs/MANUAL_TESTS.md](docs/MANUAL_TESTS.md).

## Desenvolvimento

Dependencias esperadas:

- Python 3.10+
- GTK4
- libadwaita
- PyGObject
- GStreamer
- Meson
- Ninja

Comandos pretendidos:

```bash
meson setup builddir
meson compile -C builddir
./builddir/local-soundsgood
```

Validacao rapida:

```bash
python3 -m py_compile soundsgood/*.py soundsgood/views/*.py soundsgood/widgets/*.py tests/*.py
python3 -m unittest discover -s tests
meson test -C builddir
```

Para validar instalacao sem tocar no sistema:

```bash
DESTDIR="$(mktemp -d)" meson install -C builddir --destdir "$DESTDIR"
```

Durante desenvolvimento, tambem e possivel iniciar diretamente com:

```bash
python3 -m soundsgood.application
```

No ambiente atual, valide primeiro se `meson` esta instalado. Se nao estiver, instale as dependencias do sistema antes de tentar executar o app.

## Distribuicao

O formato recomendado para distribuicao e Flatpak/Flathub.

Enquanto o app ainda nao estiver no Flathub, use o bundle publicado em GitHub Releases:

```bash
flatpak install --user ./SoundsGood-0.1.0-x86_64.flatpak
flatpak run io.github.n1ghthill.soundsgood
```

Arquivos relevantes:

- `io.github.n1ghthill.soundsgood.yml`: manifest Flatpak local inicial.
- `data/metainfo/io.github.n1ghthill.soundsgood.metainfo.xml.in`: metainfo AppStream.
- `data/desktop/io.github.n1ghthill.soundsgood.desktop.in`: desktop entry.
- `data/icons/io.github.n1ghthill.soundsgood.svg`: icone da aplicacao.
- `COPYING`: licenca GPL-2.0.

Veja o roteiro em [docs/FLATPAK.md](docs/FLATPAK.md).

## Roadmap

O plano de desenvolvimento esta em [ROADMAP.md](ROADMAP.md).

## Orientacao Para IA

Agentes de IA devem ler [agent.md](agent.md) antes de modificar o projeto.
