# Dashboard de OS Finalizadas - SGP

Projeto base para gerar um dashboard HTML com dados de OS finalizadas via API do SGP.

## O que este projeto faz

- Consulta a API `POST /api/ura/ordemservico/list/`
- Busca apenas OS encerradas (`status = 1`)
- Usa paginação automática com `offset` e `limit=1000`
- Permite filtrar:
  - Ano inteiro
  - Um mês específico
- Classifica quem finalizou em:
  - Técnicos
  - Infra
  - Outros

## Arquivos

- `config.example.json`  
  Exemplo versionado da configuração da API e da lista manual de técnicos / infra

- `config.json`  
  Arquivo local com credenciais reais e configurações da sua instância; não deve ser versionado

- `sgp_client.py`  
  Cliente da API do SGP

- `processar_os.py`  
  Tratamento, classificação e agregação

- `gerar_dashboard.py`  
  Geração do HTML final

- `main.py`  
  Execução principal do projeto

## Antes de rodar

Crie o seu `config.json` a partir do `config.example.json` e então edite:

### 1. URL da API
```json
"url_base": "https://SEU-SGP"
```

### 2. Autenticação
Você pode usar:

#### Basic Auth
```json
"auth_mode": "basic",
"basic_auth": {
  "username": "SEU_USUARIO",
  "password": "SUA_SENHA"
}
```

#### App + Token
```json
"auth_mode": "app_token",
"app_token_auth": {
  "app": "SEU_APP",
  "token": "SEU_TOKEN"
}
```

### 3. Classificação manual
```json
"classificacao": {
  "tecnicos": ["joao", "cabral", "eriki"],
  "infra_keywords": ["infra", "infraestrutura"]
}
```

Tudo que aparecer em `finalizado por` e não estiver nas listas acima será classificado como `Outros`.

### 4. Filtro inicial do dashboard
```json
"dashboard": {
  "ano_padrao": 2026,
  "mes_padrao": "Todos",
  "atualizacao_segundos": 300
}
```

Valores possíveis para `mes_padrao`:
- `Todos`
- `Janeiro`
- `Fevereiro`
- `Março`
- `Abril`
- `Maio`
- `Junho`
- `Julho`
- `Agosto`
- `Setembro`
- `Outubro`
- `Novembro`
- `Dezembro`

`atualizacao_segundos` controla:
- o contador regressivo mostrado no topo do dashboard
- o intervalo usado pela automação local via `cron`

## Instalação

```bash
pip install requests pandas
```

## Execução

```bash
python main.py
```

## Automação da atualização

Para atualizar o dashboard automaticamente no servidor ou máquina onde esse projeto roda:

```bash
chmod +x atualizar_dashboard.sh instalar_cron_dashboard.sh
./instalar_cron_dashboard.sh
```

Isso cria uma entrada no `cron` para executar `main.py` no intervalo configurado em `dashboard.atualizacao_segundos`.

## Saídas geradas

- `dashboard_os_sgp.html`
- `os_finalizadas_tratadas.csv`

## Atenção importante

A API do SGP pode devolver nomes de campos diferentes conforme a instalação.  
No arquivo `processar_os.py`, revise principalmente as candidatas para:

- campo de finalização
- campo de usuário que finalizou

As candidatas atuais são:

```python
col_finalizado = detectar_coluna(df, [
    "finalizado por",
    "finalizado_por",
    "usuario_finalizacao",
    "usuario_finalizado",
    "user_finish",
])

col_data_finalizacao = detectar_coluna(df, [
    "data_finalizacao",
    "finalizacao",
    "encerrada",
    "data encerramento",
    "data_encerramento",
    "encerramento",
])
```

Se o JSON da sua API vier com outros nomes, basta ajustar aqui.

## Próximo refinamento recomendado

Quando você tiver um exemplo real do JSON retornado pela API, vale ajustar:
- nomes exatos das colunas
- colunas detalhadas que devem aparecer na tabela final
- filtros extras como POP e motivo
