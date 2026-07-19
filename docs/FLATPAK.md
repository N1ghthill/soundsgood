# Flatpak Distribution

O formato de distribuicao atual do SoundsGood e um repositorio Flatpak proprio,
hospedado via GitHub Pages. O app nao depende de listagem no Flathub para ser
instalado ou atualizado.

Os exemplos de bundle abaixo apontam para a ultima release publica, 0.2.1.

## Instalar pelo repositorio

O usuario adiciona o remote uma vez:

```bash
flatpak remote-add --user --if-not-exists soundsgood https://n1ghthill.github.io/soundsgood/soundsgood.flatpakrepo
```

Depois instala o app:

```bash
flatpak install --user soundsgood io.github.n1ghthill.soundsgood
flatpak run io.github.n1ghthill.soundsgood
```

Atualizacoes passam a vir pelo Flatpak:

```bash
flatpak update --user io.github.n1ghthill.soundsgood
```

Gerenciadores graficos que suportam remotes Flatpak tambem podem oferecer essa
atualizacao ao usuario final; nao e necessario abrir o aplicativo pelo terminal.

Para migrar uma instalacao antiga feita por bundle:

```bash
flatpak install --user --reinstall soundsgood io.github.n1ghthill.soundsgood//stable
```

## App ID

O app ID preparado para publicacao e:

```text
io.github.n1ghthill.soundsgood
```

Esse ID deve permanecer sincronizado entre:

- `meson.build`
- `io.github.n1ghthill.soundsgood.yml`
- `data/metainfo/io.github.n1ghthill.soundsgood.metainfo.xml.in`
- `data/desktop/io.github.n1ghthill.soundsgood.desktop.in`
- `data/schemas/io.github.n1ghthill.soundsgood.gschema.xml`
- `data/icons/io.github.n1ghthill.soundsgood-*.png`
- `data/icons/io.github.n1ghthill.soundsgood.png`
- `data/icons/io.github.n1ghthill.soundsgood.svg`

## Build Local

Dependencias:

```bash
flatpak install org.gnome.Platform//50 org.gnome.Sdk//50
flatpak install org.flatpak.Builder
```

Build e instalacao local:

```bash
flatpak run org.flatpak.Builder --user --install --force-clean --default-branch=stable build-flatpak io.github.n1ghthill.soundsgood.yml
flatpak run io.github.n1ghthill.soundsgood
```

Gerar bundle versionado para GitHub Releases:

```bash
flatpak build-bundle ~/.local/share/flatpak/repo SoundsGood-0.2.1-x86_64.flatpak io.github.n1ghthill.soundsgood stable
```

Tambem publique uma copia com nome estavel para permitir o link
`releases/latest/download`:

```bash
cp SoundsGood-0.2.1-x86_64.flatpak SoundsGood-x86_64.flatpak
```

Instalar a ultima release publicada:

```bash
wget https://github.com/N1ghthill/soundsgood/releases/latest/download/SoundsGood-x86_64.flatpak
flatpak install --user ./SoundsGood-x86_64.flatpak
flatpak run io.github.n1ghthill.soundsgood
```

## Publicar o repositorio Flatpak

O repositorio remoto e assinado com a chave GPG local:

```text
452731C50C39B6D4
```

Para atualizar o repositorio hospedado no GitHub Pages:

```bash
scripts/publish-flatpak-repo.sh
```

O script:

- builda o app com `flatpak-builder`;
- exporta para um repositorio OSTree assinado;
- gera static deltas;
- gera `soundsgood.flatpakrepo` com a chave publica embutida;
- publica a branch `gh-pages`.

O manifest local usa:

```yaml
sources:
  - type: dir
    path: .
```

Para um build reproduzivel fora da arvore local, substitua essa fonte por uma
fonte versionada, de preferencia uma tag assinada ou um commit fixo, por
exemplo:

```yaml
sources:
  - type: git
    url: https://github.com/N1ghthill/soundsgood.git
    tag: v0.2.1
    commit: COMMIT_DA_TAG
```

## Validacao

Validacao automatica do projeto:

```bash
python3 -m py_compile soundsgood/*.py soundsgood/views/*.py soundsgood/widgets/*.py tests/*.py
python3 -m unittest discover -s tests
meson setup builddir --reconfigure
meson compile -C builddir
meson test -C builddir
```

Validacao dos metadados instalados:

```bash
desktop-file-validate builddir/data/io.github.n1ghthill.soundsgood.desktop
appstreamcli validate --no-net --pedantic builddir/data/io.github.n1ghthill.soundsgood.metainfo.xml
glib-compile-schemas --strict builddir/data
```

Validacao do manifest, quando `org.flatpak.Builder` estiver instalado:

```bash
flatpak run --command=flatpak-builder-lint org.flatpak.Builder manifest io.github.n1ghthill.soundsgood.yml
```

## Permissoes

O manifest concede:

- Wayland e fallback X11 para a interface GTK.
- PulseAudio para reproducao.
- `xdg-music:ro` para escanear musicas locais.
- `org.mpris.MediaPlayer2.SoundsGood` para publicar controles MPRIS.
- `org.kde.StatusNotifierWatcher` apenas para registrar o indicador opcional
  em desktops compativeis.
- Notificacoes e inibicao de suspensao usam as APIs de aplicacao/portais do desktop.

Se o app passar a depender somente de portal/document portal para pastas escolhidas pelo usuario, a permissao `xdg-music:ro` pode ser reavaliada.

## Checklist de Release

- Criar release/tag versionada.
- Atualizar screenshots, se a UI mudou.
- Rodar `scripts/generate-assets.sh` se screenshots, marca ou versao mudaram.
- Buildar e instalar o Flatpak localmente.
- Publicar o repositorio Flatpak com `scripts/publish-flatpak-repo.sh`.
- Testar `flatpak update --user io.github.n1ghthill.soundsgood`.
- Gerar o bundle versionado.
- Gerar ou copiar o bundle com nome estavel `SoundsGood-x86_64.flatpak`.
- Publicar os dois assets na GitHub Release.
- Confirmar que `releases/latest/download/SoundsGood-x86_64.flatpak` baixa a versao esperada.
- Validar os metadados AppStream.
- Rodar `flatpak-builder-lint`.

## Estado da Release 0.2.1

- Tag assinada: `v0.2.1`.
- Commit de codigo: `968fc3fa4d7556a3e7dffb9f082d0d56c1fd931b`.
- Commit publicado no repositorio Flatpak:
  `3973dfeca78689cffd36a5dbdf4e8e300085b9cffc7ec43898dd225b76e62252`.
- Menus contextuais de musicas e albums foram validados antes da publicacao.
- Assets versionado e estavel publicados na GitHub Release.
- Build, testes e validacao Flatpak aprovados no
  [CI publico do GNOME 50](https://github.com/N1ghthill/soundsgood/actions/runs/29676931211).
