# Flatpak

O formato recomendado para distribuir o SoundsGood e Flatpak, com publicacao final no Flathub.

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
flatpak install flathub org.gnome.Platform//50 org.gnome.Sdk//50
flatpak install flathub org.flatpak.Builder
```

Build e instalacao local:

```bash
flatpak run org.flatpak.Builder --user --install --force-clean --default-branch=stable build-flatpak io.github.n1ghthill.soundsgood.yml
flatpak run io.github.n1ghthill.soundsgood
```

Gerar bundle para GitHub Releases:

```bash
flatpak build-bundle ~/.local/share/flatpak/repo SoundsGood-0.1.0-x86_64.flatpak io.github.n1ghthill.soundsgood stable
```

Instalar o bundle:

```bash
flatpak install --user ./SoundsGood-0.1.0-x86_64.flatpak
flatpak run io.github.n1ghthill.soundsgood
```

O manifest local usa:

```yaml
sources:
  - type: dir
    path: .
```

Para submissao ao Flathub, substitua essa fonte por uma fonte versionada, de preferencia uma tag assinada ou um commit fixo, por exemplo:

```yaml
sources:
  - type: git
    url: https://github.com/N1ghthill/soundsgood.git
    tag: v0.1.0
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

## Antes do Flathub

- Criar release/tag versionada.
- Confirmar que `https://github.com/N1ghthill/soundsgood` continua acessivel antes da validacao final sem `--no-net`.
- Substituir `type: dir` por fonte versionada no manifest.
- Gerar screenshots reais da janela do app para o metainfo.
- Rodar `flatpak-builder-lint`.
- Revisar a politica atual do Flathub sobre submissao e conteudo assistido por IA antes de abrir qualquer PR.
