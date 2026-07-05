# Install GSettings schema
schema_file = configure_file(
    input: 'schemas' / 'io.github.irving.soundsgood.gschema.xml',
    output: 'io.github.irving.soundsgood.gschema.xml',
    copy: true,
)

install_data(
    'schemas' / 'io.github.irving.soundsgood.gschema.xml',
    install_dir: join_paths(get_option('datadir'), 'glib-2.0', 'schemas')
)

glib_compile_schemas = find_program('glib-compile-schemas')
custom_target(
    'compile-local-schemas',
    input: schema_file,
    output: 'gschemas.compiled',
    command: [glib_compile_schemas, meson.current_build_dir()],
    build_by_default: true,
)

# Install desktop file
desktop_file = APPLICATION_ID + '.desktop'
configure_file(
    input: 'desktop' / 'io.github.irving.soundsgood.desktop.in',
    output: desktop_file,
    copy: true,
    install: true,
    install_dir: join_paths(get_option('datadir'), 'applications')
)

# Install AppStream metainfo
metainfo_file = APPLICATION_ID + '.metainfo.xml'
configure_file(
    input: 'metainfo' / 'io.github.irving.soundsgood.metainfo.xml.in',
    output: metainfo_file,
    copy: true,
    install: true,
    install_dir: join_paths(get_option('datadir'), 'metainfo')
)

# Install icons
install_data(
    'icons' / 'io.github.irving.soundsgood.svg',
    install_dir: join_paths(get_option('datadir'), 'icons', 'hicolor', 'scalable', 'apps')
)

# Resource bundle
gnome.compile_resources(
    APPLICATION_ID,
    'soundsgood.gresource.xml',
    source_dir: '.',
    gresource_bundle: true,
    install: true,
    install_dir: PKGDATA_DIR
)
