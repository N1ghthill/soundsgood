# Testes Manuais

Use este roteiro para validar comportamento que ainda nao e coberto por testes unitarios.

## Preparacao

```bash
meson setup builddir --reconfigure
meson compile -C builddir
./builddir/local-soundsgood
```

O warning `Unknown key gtk-modules` em `~/.config/gtk-4.0/settings.ini` e uma configuracao local do GTK e nao deve bloquear o app.

Antes dos testes manuais, rode a validacao automatica:

```bash
python3 -m py_compile soundsgood/*.py soundsgood/views/*.py soundsgood/widgets/*.py tests/*.py
python3 -m unittest discover -s tests
meson test -C builddir
```

## Biblioteca

- Abrir o app com musicas em `xdg-user-dir MUSIC`.
- Confirmar que Albums, Artists e Songs deixam o estado de escaneamento.
- Confirmar que uma pasta vazia mostra estado vazio sem traceback.
- No estado vazio, clicar em `Choose Music Folder`, escolher uma pasta com musicas e confirmar que o scan inicia.
- Em Preferences, escolher uma pasta inexistente e confirmar toast/estado de erro.
- Em Preferences ou no menu, acionar `Rescan Library`/`Rescan Now` e confirmar que a biblioteca volta ao estado de scan sem duplicatas.
- Adicionar ou remover um arquivo de musica e aguardar o rescan com debounce.
- Confirmar que album/artista/contagens mudam sem duplicatas.
- Fechar e reabrir o app sem alterar a pasta de musicas e confirmar que a biblioteca aparece pelo cache sem espera longa de varredura.

## Navegacao

- Abrir um album pelo grid.
- Confirmar capa, artista, ano quando existir, contagem e faixas ordenadas.
- Confirmar que albums com mais de um disco mostram separadores `Disc N`.
- Abrir um artista e confirmar albums agrupados.
- Buscar por titulo, artista e album.
- Buscar ignorando acentos, por exemplo `musica` para `Música`.
- Iniciar reproducao por faixa, album, artista e resultado de busca.

## Playback

- Definir SoundsGood como app padrao para arquivos `.mp3` e abrir uma faixa pelo gerenciador de arquivos.
- Abrir uma faixa pelo terminal com `soundsgood caminho/para/faixa.mp3` e confirmar que o app inicia a reproducao.
- Abrir playlists `.m3u` e `.pls` e confirmar que as faixas entram como fila temporaria.
- Dar duplo clique em faixas diferentes e confirmar que o audio real muda junto com a UI.
- Testar Play/Pause, Previous, Next e Seek.
- Testar volume e mute.
- Testar repeat none, repeat all, repeat song e shuffle.
- Abrir a fila, selecionar uma faixa, remover item individual e limpar fila.
- Confirmar que a faixa atual fica destacada nas listas.
- Confirmar que uma notificacao aparece quando uma nova faixa comeca, se a preferencia estiver ativa.
- Confirmar que a sessao nao entra em suspensao enquanto ha musica tocando, se a preferencia estiver ativa.
- Alternar as preferencias de notificacao e prevencao de suspensao e confirmar que os comportamentos mudam sem reiniciar o app.

## MPRIS

Com o app aberto, validar propriedades basicas:

```bash
gdbus call --session \
  --dest org.mpris.MediaPlayer2.SoundsGood \
  --object-path /org/mpris/MediaPlayer2 \
  --method org.freedesktop.DBus.Properties.Get \
  org.mpris.MediaPlayer2 Identity

gdbus call --session \
  --dest org.mpris.MediaPlayer2.SoundsGood \
  --object-path /org/mpris/MediaPlayer2 \
  --method org.freedesktop.DBus.Properties.Get \
  org.mpris.MediaPlayer2.Player PlaybackStatus

gdbus call --session \
  --dest org.mpris.MediaPlayer2.SoundsGood \
  --object-path /org/mpris/MediaPlayer2 \
  --method org.freedesktop.DBus.Properties.Get \
  org.mpris.MediaPlayer2.Player Metadata
```

Resultados esperados sem faixa atual:

- `Identity`: `SoundsGood`
- `PlaybackStatus`: `Stopped`
- `Metadata`: `mpris:trackid` apontando para `NoTrack`

Durante reproducao, validar tambem:

- `PlaybackStatus` muda para `Playing`.
- `Metadata` expoe titulo, artista, album, URL e duracao.
- Controles de midia do shell conseguem pausar, retomar, avancar e voltar.
