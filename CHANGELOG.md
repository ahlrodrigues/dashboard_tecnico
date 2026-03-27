# Changelog

Registro resumido das mudanças publicadas no dashboard.

## 2.3.3 - 2026-03-27

- Ajustado o botão `Atualizar agora` para recarregar a página ao final da atualização.

## 2.3.2 - 2026-03-27

- Corrigido o fluxo de rebuild do HTML para atualizar corretamente versão e commit exibidos no dashboard.
- `release_dashboard.sh` passou a reconstruir o HTML em modo offline usando cache local.

## 2.3.1 - 2026-03-27

- Atualizada a documentação do projeto.
- Acrescentadas informações de autoria e contato no `README.md`.

## 2.3.0 - 2026-03-27

- Criados os scripts `release_dashboard.sh` e `atualizar_live.sh`.
- Documentado o fluxo de release automatizado e de atualização do ambiente live.
- Corrigido o `bump_version.py` para preservar os helpers de versão em `version.py`.

## 2.1.1 - 2026-03-27

- Centralizada a versão semântica em `version.py`.
- Acrescentada a exibição do commit curto ao lado da versão no dashboard.

## Versões anteriores

- `1c9f8b4`: versionamento semântico e exibição do commit.
- `a3282c6`: painel de detalhamento por POP.
- `35c8521`: sincronização de técnicos e consolidação de votos por duplas do dia.
- `0a1d0d1`: ajustes de duplicidade de votos e redução visual do rótulo da versão.
- `5d1d8c1`: refresh incremental do dashboard e cache.
