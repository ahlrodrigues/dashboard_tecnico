# Changelog

Registro resumido das mudancas publicadas no dashboard.

## 2.3.3 - 2026-03-27

- Ajustado o botao `Atualizar agora` para recarregar a pagina ao final da atualizacao.

## 2.3.2 - 2026-03-27

- Corrigido o fluxo de rebuild do HTML para atualizar corretamente versao e commit exibidos no dashboard.
- `release_dashboard.sh` passou a reconstruir o HTML em modo offline usando cache local.

## 2.3.1 - 2026-03-27

- Atualizada a documentacao do projeto.
- Acrescentadas informacoes de autoria e contato no `README.md`.

## 2.3.0 - 2026-03-27

- Criados os scripts `release_dashboard.sh` e `atualizar_live.sh`.
- Documentado o fluxo de release automatizado e de atualizacao do ambiente live.
- Corrigido o `bump_version.py` para preservar os helpers de versao em `version.py`.

## 2.1.1 - 2026-03-27

- Centralizada a versao semantica em `version.py`.
- Acrescentada a exibicao do commit curto ao lado da versao no dashboard.

## Versoes anteriores

- `1c9f8b4`: versionamento semantico e exibicao do commit.
- `a3282c6`: painel de detalhamento por POP.
- `35c8521`: sincronizacao de tecnicos e consolidacao de votos por duplas do dia.
- `0a1d0d1`: ajustes de duplicidade de votos e reducao visual do rotulo da versao.
- `5d1d8c1`: refresh incremental do dashboard e cache.
