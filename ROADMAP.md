# Roadmap

Atualizado em 19 de julho de 2026 para a release publica 0.2.3.

O SoundsGood prioriza um player local estavel e integrado ao desktop antes de
recursos avancados. O produto permanece inspirado no GNOME Music e mantem fora
do escopo radio, podcasts, streaming, contas e servicos remotos obrigatorios.

## Estado Atual

A base do MVP, a biblioteca local, a navegacao, o player, o acabamento visual e
o empacotamento Flatpak estao implementados. A versao 0.2.3 tambem oferece
reproducao opcional em segundo plano, indicador de bandeja em desktops
compativeis e listas de detalhe virtualizadas.

O app mantem conceitos separados para **fila de reproducao temporaria** e
**playlists persistentes**. Arquivos `.m3u`, `.m3u8` e `.pls` podem ser abertos
como fila ou importados como colecoes nomeadas na secao Playlists.

## Fase 0: Base Executavel — concluida

Objetivo: abrir uma janela GTK, descobrir arquivos locais e reproduzir audio.

- [x] Implementar a janela principal com Albums, Artists, Songs e Search.
- [x] Implementar o player GStreamer e os controles globais.
- [x] Usar o diretorio XDG de musicas como padrao.
- [x] Exibir capas e detalhes de album.
- [x] Reproduzir por faixa, album, artista e busca.
- [x] Abrir arquivos de audio pelo desktop.
- [x] Abrir `.m3u`, `.m3u8` e `.pls` como fila temporaria.
- [x] Remover templates e recursos GTK obsoletos.

## Fase 1: Biblioteca Local Confiavel — concluida

Objetivo: organizar musicas por metadados reais, com falhas isoladas e
reabertura rapida.

- [x] Ler tags e capas com GStreamer Discoverer, com fallback seguro.
- [x] Capturar titulo, artista, album artist, album, faixa, disco, ano, genero,
  duracao e capa quando disponiveis.
- [x] Persistir indice local invalidado por `mtime_ns` e tamanho.
- [x] Gravar o cache por substituicao atomica.
- [x] Executar validacao e scan fora da thread principal do GTK.
- [x] Isolar arquivos malformados sem interromper o scan.
- [x] Consolidar pedidos concorrentes de scan.
- [x] Monitorar a pasta com debounce.
- [x] Aplicar diffs por URI e atualizar albums/artistas incrementalmente.
- [x] Expor estados vazio, escaneando, pronto e erro.
- [x] Permitir reindexacao manual completa.

Decisao mantida: `Library` continua isolada para permitir avaliar
Tracker/LocalSearch + Grilo no futuro sem reescrever a UI. Essa migracao nao e
um compromisso atual.

## Fase 2: Navegacao e Busca — concluida

Objetivo: entregar a experiencia central de uma biblioteca musical local.

- [x] Grid responsivo de albums.
- [x] Lista de artistas e detalhes agrupados por album/disco.
- [x] Lista densa de faixas.
- [x] Busca global com normalizacao de acentos e ranking basico.
- [x] Resultados separados por artistas, albums e musicas.
- [x] Estados vazios e escolha de pasta.
- [x] Navegacao adaptativa e composicao para telas estreitas.
- [x] Virtualizacao de albums, artistas, musicas e listas de detalhe.

## Fase 3: Fila e Experiencia de Player — implementada, validacao aberta

Objetivo: tornar a reproducao previsivel e confortavel.

- [x] Implementar fila temporaria de reproducao.
- [x] Tocar album, artista e resultado de busca como fila.
- [x] Implementar anterior/proxima e modos `none`, `song`, `all` e `shuffle`.
- [x] Exibir progresso real e permitir seek.
- [x] Persistir volume, mute e repeticao em GSettings.
- [x] Tratar fim de faixa e erros do GStreamer.
- [x] Mostrar, selecionar, remover itens e limpar a fila atual.
- [x] Eliminar caminhos duplicados de ativacao de faixas.
- [ ] Executar regressao de shuffle/repeat com colecoes reais e registrar o
  resultado.

## Fase 4: Integracao e Acabamento — concluida para o MVP

Objetivo: oferecer uma experiencia coerente com aplicativos Linux modernos.

- [x] Preferencias, About, atalhos e CSS semantico.
- [x] Barra de player compacta e adaptativa.
- [x] Acessibilidade basica em controles e acoes de icone.
- [x] MPRIS para controles de midia do sistema.
- [x] Notificacoes opcionais e inibicao de suspensao.
- [x] Execucao opcional em segundo plano separando janela e processo.
- [x] StatusNotifier opcional com abrir, transporte e sair.
- [x] Reabertura pelo lancador sem exigir terminal ou bandeja.
- [x] Teardown explicito de sinais, sources, monitores, D-Bus e GStreamer.

## Fase 5: Qualidade e Distribuicao — concluida para a versao 0.2.2

Objetivo: manter um app empacotavel, atualizavel e diagnosticavel.

- [x] Testes unitarios de modelos, biblioteca, cache, player, MPRIS, segundo
  plano e StatusNotifier.
- [x] Smoke tests graficos e matriz automatizada de larguras.
- [x] Validacao de schemas, desktop file, AppStream e recursos.
- [x] Manifest e build Flatpak no GNOME 50.
- [x] CI publica para build, testes e validacao do Flatpak.
- [x] Repositorio Flatpak proprio, assinado e atualizavel.
- [x] Logs locais limitados e diagnosticos acessiveis pelas preferencias.
- [x] Documentacao e kit de submissao da OpenAI Build Week 2026.

## Fase 6: Playlists Persistentes — concluida na 0.2.0, refinada na 0.2.1

Objetivo: permitir que o usuario mantenha colecoes nomeadas sem confundir
playlist salva com a fila temporaria do player.

- [x] Definir `Playlist` e `PlaylistEntry` com identidade estavel e ordem
  explicita.
- [x] Persistir playlists em `$XDG_DATA_HOME/soundsgood` com escrita atomica e
  formato versionado; como este e o formato inicial, versoes desconhecidas sao
  rejeitadas com seguranca ate existir uma migracao real.
- [x] Criar, renomear e excluir playlists com confirmacao para operacoes
  destrutivas.
- [x] Adicionar faixas, albums, artistas e resultados de busca a uma playlist.
- [x] Remover e reordenar faixas sem alterar a fila que estiver tocando.
- [x] Adicionar uma secao adaptativa de Playlists, com estados vazio e de
  arquivo ausente.
- [x] Expor menus contextuais nativos em musicas e albums, com submenu dinamico
  de playlists e acesso a criacao de uma nova colecao.
- [x] Corrigir a regressao 0.2.1 que impedia factories de detalhe de renderizar
  thumbnails de albums e faixas na tela de artistas.
- [x] Tocar uma playlist inteira, criando a fila apenas quando solicitado.
- [x] Importar `.m3u`, `.m3u8` e `.pls` como playlists salvas sem quebrar o
  comportamento atual de abertura temporaria.
- [x] Exportar playlists em `.m3u8`, tratando caminhos relativos e caracteres
  Unicode.
- [x] Cobrir persistencia, versao de formato, importacao, exportacao, ordenacao,
  arquivos ausentes e falhas com testes unitarios e graficos.
- [x] Documentar claramente recuperacao quando uma faixa for movida ou
  removida da biblioteca.

Restricoes arquiteturais: a persistencia pertence a uma camada de catalogo,
nao aos widgets; a fila continua pertencendo ao `Player`; I/O nao deve bloquear
a thread GTK; arquivos corrompidos devem gerar diagnostico recuperavel.

## Fase 6.1: Confiabilidade diaria de playlists — implementada na 0.2.3

Objetivo: corrigir as lacunas observadas no uso real sem voltar a misturar
playlists salvas com a fila temporaria.

- [x] Adicionar um seletor pesquisavel e multi-selecao para incluir musicas da
  biblioteca diretamente no editor da playlist.
- [x] Ocultar no seletor as musicas que ja pertencem a playlist e explicar
  claramente resultados vazios ou duplicados.
- [x] Virtualizar tambem a escolha da playlist de destino.
- [x] Tornar a exclusao visivel, confirmada e previsivel, selecionando a
  colecao vizinha quando existir.
- [x] Atualizar nome, contagem e entradas no lugar, preservando rolagem e foco
  em vez de reconstruir todo o detalhe durante cada mutacao.
- [x] Consolidar rajadas de alteracoes antes de criar o snapshot persistente,
  mantendo escrita atomica fora da thread GTK.
- [x] Recusar limites de playlists e entradas antes de qualquer mutacao
  parcial que nao possa ser salva.
- [x] Cobrir 50 playlists e 5.000 entradas, tres ciclos de reabertura,
  reordenacao, disco cheio simulado e recuperacao da gravacao.
- [ ] Validar manualmente o fluxo completo com a biblioteca principal do
  mantenedor antes de promover estas mudancas a uma release.

## Fase 7: Beta e Acessibilidade — planejada

Objetivo: validar o uso diario em ambientes e bibliotecas mais diversos.

- [ ] Executar regressao manual com colecoes pequenas, grandes e com metadados
  incompletos.
- [ ] Auditar navegacao completa por teclado, foco e leitor de tela.
- [ ] Evoluir diagnosticos para listar arquivos problemáticos sem expor
  caminhos pessoais por padrao.
- [ ] Medir tempo de abertura, scan, memoria e rolagem com bibliotecas grandes.
- [ ] Testar comportamento em GNOME, KDE e ambientes sem StatusNotifier.
- [ ] Definir criterio objetivo para promover o projeto de MVP para beta.

## Prioridade Imediata

1. Concluir os itens ainda abertos da submissao Build Week em
   `docs/SUBMISSION.md`, especialmente `/feedback`, video e envio no Devpost.
2. Executar e registrar a regressao manual final em colecoes e larguras reais.
3. Validar playlists com colecoes reais e ampliar a cobertura de regressao.
4. Prosseguir para a auditoria de acessibilidade e os criterios de beta.

## Fora de Escopo

- Radio e podcasts.
- Streaming ou download automatico de musicas.
- Login, conta, sincronizacao ou dependencia obrigatoria de nuvem.
- Edicao completa de tags.

## Como Retomar

1. Leia `AGENTS.md`, `agent.md`, este roadmap e `docs/ARCHITECTURE.md`.
2. Rode a validacao definida em `AGENTS.md` antes de mudar comportamento.
3. Escolha o primeiro item aberto da prioridade imediata.
4. Para UI ou playback, siga `docs/MANUAL_TESTS.md`.
5. Ao concluir uma etapa, atualize roadmap, README, arquitetura, testes manuais
   e AppStream no mesmo conjunto de mudancas.
