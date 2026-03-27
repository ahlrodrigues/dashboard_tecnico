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

## Publicação paralela sem sobrescrever a versão antiga

Para publicar esta versão em paralelo com a antiga, use:

- outro diretório
- outra porta
- outro nome de serviço `systemd`
- outro arquivo de log

Exemplo seguro:

- versão antiga: `/var/www/html/dashboard_tecnico-main` na porta `8765`
- nova versão live: `/var/www/html/dashboard_tecnico-live` na porta `8775`

### 1. Envie os arquivos para um novo diretório no servidor

No servidor, crie um diretório separado:

```bash
mkdir -p /var/www/html/dashboard_tecnico-live
```

Depois envie os arquivos desta branch para esse novo diretório.
Se você estiver usando `git` no servidor:

```bash
cd /var/www/html
git clone git@github.com:ahlrodrigues/dashboard_tecnico.git dashboard_tecnico-live
cd dashboard_tecnico-live
git checkout feature/dashboard-live-api
```

Se preferir copiar a partir da máquina local, envie pelo método que você já usa hoje, sempre para o novo diretório:

```bash
rsync -av --exclude '.git' --exclude '.venv' /CAMINHO/LOCAL/dashboard_técnico/ usuario@SERVIDOR:/var/www/html/dashboard_tecnico-live/
```

### 2. Crie o ambiente virtual da nova versão

```bash
cd /var/www/html/dashboard_tecnico-live
python3 -m venv .venv
./.venv/bin/pip install -U pip
./.venv/bin/pip install requests pandas
```

Se o seu projeto já tiver outros pacotes no servidor:

```bash
./.venv/bin/pip install -r requirements.txt
```

### 3. Crie o `config.json` da nova versão

Copie o arquivo de configuração e ajuste se necessário:

```bash
cp config.example.json config.json
```

Depois edite:

- URL do SGP
- credenciais
- classificação
- `dashboard.atualizacao_segundos`

### 4. Gere os arquivos da nova versão antes de subir o servidor

```bash
cd /var/www/html/dashboard_tecnico-live
./.venv/bin/python main.py
```

Isso deve gerar:

- `dashboard_os_sgp.html`
- `dashboard_data.json`

### 5. Teste manualmente a nova versão em outra porta

```bash
cd /var/www/html/dashboard_tecnico-live
./.venv/bin/python dashboard_server.py --host 0.0.0.0 --port 8775
```

Depois teste:

- `http://SEU_IP:8775/`
- `http://SEU_IP:8775/api/dashboard-data`
- `http://SEU_IP:8775/api/refresh-status`

### 6. Instale um segundo serviço `systemd`, sem tocar no antigo

O script agora aceita nome de serviço parametrizado. Para instalar a nova versão em paralelo:

```bash
cd /var/www/html/dashboard_tecnico-live
sudo env \
  DASHBOARD_SERVICE_NAME=dashboard-tecnico-live.service \
  DASHBOARD_SERVICE_DESCRIPTION="Dashboard Tecnico Live" \
  DASHBOARD_BASE_DIR=/var/www/html/dashboard_tecnico-live \
  DASHBOARD_SERVER_PORT=8775 \
  DASHBOARD_LOG_FILE=/var/www/html/dashboard_tecnico-live/dashboard_server.log \
  DASHBOARD_SERVICE_USER=root \
  ./instalar_systemd_dashboard.sh
```

Isso cria um segundo serviço, sem substituir `dashboard-tecnico.service`.

### 7. Garanta que o processo auxiliar use o diretório novo

Se você usar `garantir_dashboard_server.sh`, rode com as mesmas variáveis:

```bash
cd /var/www/html/dashboard_tecnico-live
env \
  DASHBOARD_BASE_DIR=/var/www/html/dashboard_tecnico-live \
  DASHBOARD_SERVER_PORT=8775 \
  DASHBOARD_LOG_FILE=/var/www/html/dashboard_tecnico-live/dashboard_server.log \
  ./garantir_dashboard_server.sh
```

### 8. Valide os dois serviços em paralelo

Versão antiga:

```bash
systemctl status dashboard-tecnico.service
```

Nova versão live:

```bash
systemctl status dashboard-tecnico-live.service
```

Checagens HTTP:

```bash
curl -s http://127.0.0.1:8765/api/refresh-status
curl -s http://127.0.0.1:8775/api/refresh-status
curl -s http://127.0.0.1:8775/api/dashboard-data | head
```

### 9. Só depois troque acesso externo, se quiser

Enquanto estiver validando:

- mantenha a antiga em `8765`
- mantenha a nova em `8775`

Depois, se quiser promover a nova versão, você pode:

- trocar o proxy reverso para apontar para `8775`
- ou desligar a antiga e reaproveitar a porta `8765`

Fazendo assim, a publicação é paralela e reversível.

## Saídas geradas

- `dashboard_os_sgp.html`
- `dashboard_data.json`

O HTML continua sendo gerado como snapshot para abertura direta e fallback local.
Quando o servidor local `dashboard_server.py` está em execução, a página também pode buscar
os dados atualizados em `/api/dashboard-data`, reduzindo a dependência do snapshot embutido.

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
