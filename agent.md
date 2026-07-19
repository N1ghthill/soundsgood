# Orientacao Para Agentes de IA

Este arquivo orienta agentes de IA que forem modificar o SoundsGood. Leia antes de editar codigo.

## Objetivo do Projeto

SoundsGood e um player de musica local para Linux, inspirado no GNOME Music. O foco e reproducao e organizacao de musicas locais por albums, artistas e faixas.

Nao implementar:

- Radio.
- Podcasts.
- Streaming.
- Login em servicos externos.
- Fontes remotas obrigatorias.

## Estado do Projeto

O projeto tem um MVP funcional; a arvore principal esta em desenvolvimento
0.2.1 e a ultima release publica e a 0.2.0. Ele inicia pelo lancador,
Flatpak ou ambiente de desenvolvimento, escaneia o diretorio XDG de musicas,
mostra albums/artistas/faixas, reproduz via GStreamer e pode continuar em
segundo plano quando a janela e fechada.

Antes de assumir que algo existe, verifique os arquivos reais. O MVP atual usa UI programatica em Python. Os templates `.ui` antigos foram removidos.

Pontos importantes:

- `soundsgood/application.py` e a entrada principal da aplicacao.
- `soundsgood/models.py` contem modelos GObject e enums como `RepeatMode`, `PlayState` e `LibraryState`.
- `soundsgood/library.py` coordena o catalogo GObject e o scan; helpers puros de cache, playlists e busca ficam em `soundsgood/catalog`.
- `soundsgood/player.py` contem o `playbin`, fila e controles de reproducao.
- `soundsgood/playlists.py` possui playlists nomeadas, persistencia assincrona,
  disponibilidade de arquivos e importacao/exportacao; nao confundir com a
  fila do player.
- `soundsgood/background.py` separa o ciclo de vida da janela do ciclo de vida
  da aplicacao.
- `soundsgood/statusnotifier.py` implementa o indicador opcional e seu menu
  D-Bus sem adicionar dependencia GTK3/AppIndicator.
- `soundsgood/window.py` compoe a janela principal.
- `soundsgood/views` contem telas de albums, artistas e musicas.
- `soundsgood/widgets` contem toolbar, linhas de musica, busca, detalhes,
  dialogs e o menu contextual dinamico de playlists.
- `data/soundsgood.gresource.xml` foi removido porque estava vazio; a UI segue programatica em Python.
- `docs/MANUAL_TESTS.md` contem o roteiro de validacao manual.

Ultima validacao conhecida, em 19 de julho de 2026 para a arvore de
desenvolvimento 0.2.1:

- 60 testes automatizados passando. O smoke grafico requer uma sessao com
  display; nesta rodada ele foi ignorado de forma explicita no GNOME SDK 50.
- `py_compile` passando para app e testes.
- `meson setup builddir --reconfigure`, `meson compile -C builddir` e `meson test -C builddir` passando.
- CI publica do GNOME 50 passou para o commit da release
  `4c33eec22355d66ae1098d71b78be5568b515d6c`.
- App inicia pelo lancador, `flatpak run io.github.n1ghthill.soundsgood` ou
  `./builddir/local-soundsgood`; pode aparecer o warning local
  `Unknown key gtk-modules` do GTK.
- App tambem aceita arquivos de audio abertos pelo gerenciador de arquivos/default app via `GApplication.open`.
- MPRIS respondeu via `gdbus` para `Identity`, `PlaybackStatus` e `Metadata`, e o usuario validou o app em ambiente real.
- StatusNotifier foi validado em KDE, incluindo a acao `Quit`; em desktops sem
  host de bandeja, lancador e MPRIS continuam funcionando.

Terminologia: o `Player` ainda usa nomes internos como `_playlist`, mas esse
estado e a fila temporaria. Playlists nomeadas pertencem a `PlaylistManager` e
sao armazenadas em `$XDG_DATA_HOME/soundsgood/playlists.json`.

## Prioridades

1. Concluir `/feedback`, video e envio da OpenAI Build Week conforme
   `docs/SUBMISSION.md`.
2. Testar regressao manual em colecoes maiores e em telas estreitas reais.
3. Validar playlists persistentes com colecoes reais e ampliar a regressao.
4. Evoluir diagnosticos para relatar arquivos com metadados incompletos sem
   expor caminhos pessoais por padrao.
5. Ampliar acessibilidade com auditoria de navegacao por teclado e leitor de
   tela.

Consulte `ROADMAP.md` antes de escolher a proxima tarefa.

## Retomada Rapida

1. Leia `ROADMAP.md`, `docs/ARCHITECTURE.md` e este arquivo.
2. Rode `python3 -m unittest discover -s tests`.
3. Escolha a primeira prioridade ainda aberta no roadmap.
4. Mantenha o escopo local-first e sem radio/streaming.
5. Depois de alterar codigo, rode unitarios, `py_compile`, Meson e, se houver UI/playback, o roteiro manual relevante.

Confirme o estado do Git antes de editar e preserve mudancas existentes do
usuario.

## Regras de Arquitetura

- Mantenha GTK/libadwaita como base da interface.
- Mantenha GStreamer como base de reproducao.
- Separe biblioteca, player e views.
- Nao coloque scan de arquivos ou logica de metadados em widgets.
- Nao controle GStreamer diretamente a partir das views.
- Prefira `Gio.ListStore`/`Gio.ListModel` para dados exibidos em GTK.
- Use sinais e propriedades GObject para comunicar mudancas.
- Colecoes sem limite devem usar `Gtk.ListView`/`Gtk.GridView` com factories, nunca uma arvore permanente de widgets por item.
- Todo sinal, source GLib, monitor ou bus watch deve ter teardown explicito.
- Preserve o escopo local-first.
- Mantenha playlists persistentes fora de `Player`: o player possui a fila; o
  catalogo possui colecoes salvas.
- Mantenha a troca de faixa no `Player` reiniciando o `playbin` antes de aplicar nova URI.

## Biblioteca e Metadados

Nao trate nomes de arquivo como fonte final de verdade.

O scanner usa GStreamer Discoverer e pode usar fallback por nome/pasta quando tags estiverem ausentes. A direcao correta continua sendo extrair tags reais sempre que possivel:

- titulo
- artista
- album
- album artist
- numero da faixa
- numero do disco
- duracao
- ano
- genero
- capa

Para URI de arquivo, use API segura, por exemplo:

```python
Path(filepath).resolve().as_uri()
```

Nao monte URI manualmente com `file://{path}`.

Use `xdg-user-dir MUSIC` como fonte do diretorio padrao de musicas, com fallback para `~/Music`.

Capas:

- Primeiro tente capa embutida via tags do GStreamer.
- Depois procure arquivos comuns na pasta do album, como `cover.jpg`, `folder.png`, `front.jpg`, `album.png` e variantes.
- Capas extraidas podem ficar em `$XDG_CACHE_HOME/soundsgood/covers`.

Cache:

- Metadados da biblioteca ficam em `$XDG_CACHE_HOME/soundsgood/library.json`.
- O cache deve ser invalidado por `mtime_ns` e tamanho do arquivo.
- Ao alterar campos de `Song`, atualize `_record_from_song()` e `_song_from_record()`.
- O monitoramento usa `Gio.FileMonitor` com limite explicito e agenda rescan com debounce.
- Scans concorrentes sao consolidados e executados depois do scan ativo.
- O cache e gravado por substituicao atomica.
- A abertura normal usa o indice em cache quando a versao do cache, os arquivos conhecidos e os diretorios indexados continuam validos.
- A acao manual de reindexacao usa scan forcado e reler metadados, mesmo quando arquivos parecem inalterados.
- O rescan aplica diff por URI no modelo de faixas.
- Albums e artistas sao atualizados incrementalmente no diff de faixas. Ao mexer nisso, cubra remocao, troca de album e troca de artista.
- A biblioteca expoe `scan_state` e `status_message`; use isso para UI de escaneando, vazio, erro e pronto.

Estados de biblioteca:

- `LibraryState.EMPTY`: scan terminou sem musicas.
- `LibraryState.SCANNING`: scan em andamento.
- `LibraryState.READY`: ha musicas carregadas.
- `LibraryState.ERROR`: erro recuperavel, como pasta configurada inexistente.

## GTK e Recursos

Estado atual: a UI principal e criada em Python. Nao adicione templates `.ui` novos sem uma decisao explicita de migrar a UI para `Gtk.Template`.

Se uma classe Python baseada em template GTK for reintroduzida:

- Defina `__gtype_name__`.
- Use `Gtk.Template(resource_path=...)`.
- Recrie `data/soundsgood.gresource.xml` e garanta que o caminho exista nele.
- Garanta que o arquivo esteja listado em `data/meson.build`.
- Garanta que o `class` no `.ui` corresponda ao `__gtype_name__`.

Ao remover um template:

- Remova o arquivo.
- Remova de `data/meson.build`.
- Remova de `data/soundsgood.gresource.xml`, se esse bundle existir.
- Remova imports e referencias Python.

Nao reintroduza um bundle `.gresource` vazio; ele so deve voltar se houver recursos reais para instalar.

## Player

O `Player` deve concentrar:

- GStreamer pipeline/playbin.
- fila de reproducao.
- faixa atual.
- estado de reproducao.
- progresso e seek.
- volume e mute.
- repeat e shuffle.
- tratamento de fim de faixa e erro.

A fila atual e transitoria. Nao reutilize diretamente sua lista mutavel como
armazenamento de playlists persistentes.

Playlists persistentes:

- usam `PlaylistManager`, `Playlist` e `PlaylistEntry`;
- sao gravadas de forma atomica fora do loop GTK;
- preservam snapshots para diagnosticar faixas ausentes;
- so alteram a fila quando o usuario pede para reproduzi-las;
- devem manter IDs e ordem durante renomeacao, exportacao e reabertura.

Views devem chamar metodos publicos como `play_song`, `play_pause`, `next`, `previous` e `seek`.

Regras importantes:

- `play_song()` deve substituir a fila quando receber `playlist`.
- Antes de tocar uma nova faixa, pare o `playbin` com `Gst.State.NULL`, aguarde a troca de estado, aplique a nova URI e entao use `Gst.State.PLAYING`.
- Atualize `current_song` so depois de a nova faixa ser carregada com sucesso.
- Em erro de GStreamer, emita o sinal `error` para a janela exibir feedback.
- Views nao devem mudar `current_song` diretamente.

## Estilo de Codigo

- Siga o estilo existente do repositorio.
- Use Python 3.10+.
- Prefira type hints quando ajudarem.
- Escreva comentarios apenas quando a logica nao for obvia.
- Evite refatoracoes amplas enquanto o MVP nao estiver executavel.
- Nao introduza frameworks novos sem justificar no README, roadmap ou arquitetura.

## Validacao

Sempre que possivel, rode:

```bash
python3 -m py_compile soundsgood/*.py soundsgood/catalog/*.py soundsgood/views/*.py soundsgood/widgets/*.py tests/*.py
python3 -m unittest discover -s tests
meson setup builddir --reconfigure
meson compile -C builddir
./builddir/local-soundsgood
meson test -C builddir
```

Se `meson` ou dependencias do sistema nao estiverem instalados, informe isso claramente.

Nao leia arquivos pessoais fora do repositorio para obter senhas ou credenciais. Se uma dependencia do sistema estiver ausente, prefira relatar o pacote necessario ou pedir autorizacao explicita antes de qualquer instalacao.

Para execucao rapida durante desenvolvimento:

```bash
python3 -m soundsgood.application
```

Para mudancas em UI:

- Verifique se o app inicia.
- Verifique se os widgets aparecem.
- Verifique se nao ha recursos `.ui` ausentes.
- Verifique se textos e botoes nao se sobrepoem.
- Verifique se a faixa atual fica destacada e se trocar de faixa altera o audio real, nao apenas a UI.
- Use `docs/MANUAL_TESTS.md` como roteiro para validacao manual de biblioteca, UI, playback e MPRIS.

## Como Responder ao Usuario

- Seja direto.
- Diga o que foi alterado.
- Diga o que foi validado.
- Diga o que nao foi possivel validar.
- Se encontrar inconsistencias existentes, registre sem apagar trabalho do usuario.

## Nao Fazer

- Nao adicionar radio.
- Nao adicionar streaming.
- Nao substituir GTK por outro toolkit.
- Nao misturar UI e backend de biblioteca.
- Nao atualizar UI de reproducao diretamente sem passar pelo `Player`.
- Nao remover arquivos grandes ou mudancas do usuario sem pedido explicito.
- Nao mascarar imports ausentes com stubs vazios que nao entregam comportamento util.
