# Flatpak Distribution

O formato de distribuicao atual do SoundsGood e um bundle Flatpak publicado em
GitHub Releases. O app nao depende de listagem no Flathub para ser instalado.

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
flatpak build-bundle ~/.local/share/flatpak/repo SoundsGood-0.1.3-x86_64.flatpak io.github.n1ghthill.soundsgood stable
```

Tambem publique uma copia com nome estavel para permitir o link
`releases/latest/download`:

```bash
cp SoundsGood-0.1.3-x86_64.flatpak SoundsGood-x86_64.flatpak
```

Instalar a ultima release publicada:

```bash
wget https://github.com/N1ghthill/soundsgood/releases/latest/download/SoundsGood-x86_64.flatpak
flatpak install --user ./SoundsGood-x86_64.flatpak
flatpak run io.github.n1ghthill.soundsgood
```

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
    tag: v0.1.3
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

Se o app passar a depender somente de portal/document portal para pastas escolhidas pelo usuario, a permissao `xdg-music:ro` pode ser reavaliada.

## Checklist de Release

- Criar release/tag versionada.
- Buildar e instalar o Flatpak localmente.
- Gerar o bundle versionado.
- Gerar ou copiar o bundle com nome estavel `SoundsGood-x86_64.flatpak`.
- Publicar os dois assets na GitHub Release.
- Confirmar que `releases/latest/download/SoundsGood-x86_64.flatpak` baixa a versao esperada.
- Validar os metadados AppStream.
- Rodar `flatpak-builder-lint`.
