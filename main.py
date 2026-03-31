from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
import json
from pathlib import Path

import pandas as pd

from gerar_dashboard import gerar_html_dashboard, montar_payload_dashboard
from processar_os import (
    normalizar_identificador_pessoa,
    preparar_dataframe,
    ranking_finalizadores,
    resumo_mensal,
)
from sgp_client import SGPClient

STATUS_ABERTAS = [0, 2, 3]
STATUS_ENCERRADAS = [1]
VOTOS_CSV_URL = "https://net4you.com.br/votos_data.csv"
CACHE_DIR_NAME = ".cache"
OS_CACHE_FILENAME = "dashboard_os_cache.json"
VOTOS_CACHE_FILENAME = "dashboard_votos_cache.json"
TECNICOS_CACHE_FILENAME = "dashboard_tecnicos_cache.json"
TECNICOS_HISTORY_FILENAME = "dashboard_tecnicos_history.json"
OS_ESTADO_ATUAL_FILENAME = "dashboard_os_estado_atual.json"
TECNICOS_HISTORY_RETENCAO_DIAS = 366
TECNICOS_HISTORY_HORA_INICIO_PADRAO = 5
TECNICOS_HISTORY_HORA_FIM_PADRAO = 20


MAPA_MES = {
    "Todos": None,
    "Janeiro": ("01-01", "01-31"),
    "Fevereiro": ("02-01", "02-28"),
    "Março": ("03-01", "03-31"),
    "Abril": ("04-01", "04-30"),
    "Maio": ("05-01", "05-31"),
    "Junho": ("06-01", "06-30"),
    "Julho": ("07-01", "07-31"),
    "Agosto": ("08-01", "08-31"),
    "Setembro": ("09-01", "09-30"),
    "Outubro": ("10-01", "10-31"),
    "Novembro": ("11-01", "11-30"),
    "Dezembro": ("12-01", "12-31"),
}


def montar_periodo(ano: int, mes: str) -> tuple[str, str]:
    if mes == "Todos":
        return f"{ano}-01-01", f"{ano}-12-31"

    faixa = MAPA_MES[mes]
    if faixa is None:
        raise ValueError(f"Mês inválido: {mes}")

    return f"{ano}-{faixa[0]}", f"{ano}-{faixa[1]}"


def carregar_votos_df() -> pd.DataFrame:
    try:
        df = pd.read_csv(VOTOS_CSV_URL)
    except Exception:
        return pd.DataFrame()

    if df.empty:
        return df

    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]
    if "data" in df.columns:
        df["data_voto_dashboard"] = pd.to_datetime(df["data"], format="%d/%m/%Y", errors="coerce")
    else:
        df["data_voto_dashboard"] = pd.NaT

    return df


def _agora_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _caminho_cache(base: Path, nome_arquivo: str) -> Path:
    cache_dir = base / CACHE_DIR_NAME
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / nome_arquivo


def _ler_json(caminho: Path) -> dict[str, object] | None:
    if not caminho.exists():
        return None
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except Exception:
        return None


def _escrever_json(caminho: Path, payload: dict[str, object]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _obter_chave_registro_os(registro: dict[str, object]) -> str:
    for campo in ("id", "ordem_servico"):
        valor = str(registro.get(campo, "")).strip()
        if valor:
            return f"{campo}:{valor}"
    return ""


def _parse_data_texto(valor: object) -> date | None:
    texto = str(valor or "").strip()
    if not texto:
        return None
    try:
        return date.fromisoformat(texto[:10])
    except ValueError:
        return None


def _registro_toca_janela_recente(registro: dict[str, object], data_inicio: date) -> bool:
    for campo in ("data_base_dashboard", "data_finalizacao_dashboard", "data_criacao_dashboard"):
        data_registro = _parse_data_texto(registro.get(campo, ""))
        if data_registro and data_registro >= data_inicio:
            return True
    return False


def _deduplicar_df_os(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    for coluna_unica in ("id", "ordem_servico"):
        if coluna_unica in df.columns:
            return df.drop_duplicates(subset=[coluna_unica]).copy()
    return df.copy()


def _normalizar_df_cache_os(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    for coluna_data in ("data_base_dashboard", "data_finalizacao_dashboard", "data_criacao_dashboard"):
        if coluna_data in df.columns:
            df[coluna_data] = pd.to_datetime(df[coluna_data], errors="coerce")
    return df


def _payload_os_cache(df: pd.DataFrame, ano: int, mes: str, url_base: str) -> list[dict[str, object]]:
    finalizadas_df = (
        df[df["status_dashboard"] == "Encerrada"].copy()
        if not df.empty and "status_dashboard" in df.columns
        else pd.DataFrame()
    )
    payload = montar_payload_dashboard(
        resumo_df=resumo_mensal(finalizadas_df),
        ranking_df=ranking_finalizadores(finalizadas_df),
        detalhes_df=df,
        finalizadas_df=finalizadas_df,
        votos_df=pd.DataFrame(),
        ano=ano,
        mes_selecionado=mes,
        refresh_seconds=30,
        sgp_base_url=url_base,
    )
    return payload["detalhes_data"]


def _carregar_os_cache(base: Path, ano: int) -> list[dict[str, object]]:
    payload = _ler_json(_caminho_cache(base, OS_CACHE_FILENAME))
    if not payload:
        return []
    if int(payload.get("ano", 0) or 0) != ano:
        return []
    registros = payload.get("detalhes_data", [])
    return registros if isinstance(registros, list) else []


def _salvar_os_cache(base: Path, ano: int, detalhes_data: list[dict[str, object]]) -> None:
    _escrever_json(
        _caminho_cache(base, OS_CACHE_FILENAME),
        {
            "schema_version": 1,
            "ano": ano,
            "updated_at": _agora_iso(),
            "detalhes_data": detalhes_data,
        },
    )


def _cache_votos_valido(base: Path, max_age_seconds: int) -> bool:
    payload = _ler_json(_caminho_cache(base, VOTOS_CACHE_FILENAME))
    if not payload:
        return False
    updated_at = str(payload.get("updated_at", "")).strip()
    if not updated_at:
        return False
    try:
        atualizado_em = datetime.fromisoformat(updated_at)
    except ValueError:
        return False
    return (datetime.now() - atualizado_em).total_seconds() <= max_age_seconds


def _carregar_votos_cache(base: Path) -> pd.DataFrame:
    payload = _ler_json(_caminho_cache(base, VOTOS_CACHE_FILENAME))
    if not payload:
        return pd.DataFrame()
    registros = payload.get("votos_data", [])
    if not isinstance(registros, list):
        return pd.DataFrame()
    df = pd.DataFrame(registros)
    if "data_voto_dashboard" in df.columns:
        df["data_voto_dashboard"] = pd.to_datetime(df["data_voto_dashboard"], errors="coerce")
    return df


def _salvar_votos_cache(base: Path, votos_df: pd.DataFrame) -> None:
    registros: list[dict[str, object]] = []
    if not votos_df.empty:
        view = votos_df.copy()
        colunas = [col for col in view.columns.tolist() if col != "data_voto_dashboard"]
        if "data_voto_dashboard" in view.columns:
            view["data_voto_dashboard"] = view["data_voto_dashboard"].dt.strftime("%Y-%m-%d")
            colunas.append("data_voto_dashboard")
        registros = view[colunas].fillna("").to_dict(orient="records")

    _escrever_json(
        _caminho_cache(base, VOTOS_CACHE_FILENAME),
        {
            "schema_version": 1,
            "updated_at": _agora_iso(),
            "votos_data": registros,
        },
    )


def _carregar_ou_atualizar_votos_df(base: Path, refresh_targets: set[str], cache_segundos: int) -> pd.DataFrame:
    if not refresh_targets:
        return _carregar_votos_cache(base)

    if "votos" not in refresh_targets and "all" not in refresh_targets:
        return _carregar_votos_cache(base)

    if _cache_votos_valido(base, max(cache_segundos, 30)):
        return _carregar_votos_cache(base)

    votos_df = carregar_votos_df()
    _salvar_votos_cache(base, votos_df)
    return votos_df


def _identificadores_tecnico(registro: object) -> list[str]:
    if not isinstance(registro, dict):
        return []

    identificadores: list[str] = []
    for campo in ("username", "nome", "name", "login"):
        valor = str(registro.get(campo, "")).strip()
        if valor:
            identificadores.append(valor)
    return identificadores


def _carregar_tecnicos_cache(base: Path) -> list[dict[str, object]]:
    payload = _ler_json(_caminho_cache(base, TECNICOS_CACHE_FILENAME))
    if not payload:
        return []
    registros = payload.get("tecnicos", [])
    return registros if isinstance(registros, list) else []


def _cache_tecnicos_valido(base: Path, max_age_seconds: int) -> bool:
    payload = _ler_json(_caminho_cache(base, TECNICOS_CACHE_FILENAME))
    if not payload:
        return False
    updated_at = str(payload.get("updated_at", "")).strip()
    if not updated_at:
        return False
    try:
        atualizado_em = datetime.fromisoformat(updated_at)
    except ValueError:
        return False
    return (datetime.now() - atualizado_em).total_seconds() <= max_age_seconds


def _salvar_tecnicos_cache(base: Path, tecnicos: list[dict[str, object]]) -> None:
    _escrever_json(
        _caminho_cache(base, TECNICOS_CACHE_FILENAME),
        {
            "schema_version": 1,
            "updated_at": _agora_iso(),
            "tecnicos": tecnicos,
        },
    )


def _texto_limpo(valor: object) -> str:
    return str(valor or "").strip()


def _normalizar_nome_exibicao_tecnico(valor: object, fallback: str = "") -> str:
    texto = _texto_limpo(valor)
    return texto or fallback


def _resolver_dono_os(registro: dict[str, object]) -> tuple[str, str]:
    responsavel = _texto_limpo(registro.get("responsavel", ""))
    responsavel_key = normalizar_identificador_pessoa(responsavel)
    if responsavel_key:
        return responsavel_key, responsavel

    return "", ""


def _resolver_finalizador_os(registro: dict[str, object]) -> tuple[str, str]:
    finalizador = _texto_limpo(registro.get("finalizado_por_dashboard", ""))
    finalizador_key = normalizar_identificador_pessoa(finalizador)
    return finalizador_key, finalizador


def _carregar_tecnicos_history(base: Path) -> list[dict[str, object]]:
    payload = _ler_json(_caminho_cache(base, TECNICOS_HISTORY_FILENAME))
    if not payload:
        return []
    registros = payload.get("records", [])
    return registros if isinstance(registros, list) else []


def _salvar_tecnicos_history(base: Path, records: list[dict[str, object]]) -> None:
    _escrever_json(
        _caminho_cache(base, TECNICOS_HISTORY_FILENAME),
        {
            "schema_version": 1,
            "updated_at": _agora_iso(),
            "records": records,
        },
    )


def _carregar_estado_os_atual(base: Path) -> dict[str, dict[str, object]]:
    payload = _ler_json(_caminho_cache(base, OS_ESTADO_ATUAL_FILENAME))
    if not payload:
        return {}
    registros = payload.get("records", [])
    if not isinstance(registros, list):
        return {}

    estado: dict[str, dict[str, object]] = {}
    for registro in registros:
        if not isinstance(registro, dict):
            continue
        os_id = _texto_limpo(registro.get("os_id", ""))
        if not os_id:
            continue
        estado[os_id] = registro
    return estado


def _salvar_estado_os_atual(base: Path, records: dict[str, dict[str, object]]) -> None:
    _escrever_json(
        _caminho_cache(base, OS_ESTADO_ATUAL_FILENAME),
        {
            "schema_version": 1,
            "updated_at": _agora_iso(),
            "records": list(records.values()),
        },
    )


def _prunar_tecnicos_history(records: list[dict[str, object]], retention_days: int) -> list[dict[str, object]]:
    if retention_days <= 0:
        return records

    limite = datetime.now() - timedelta(days=retention_days)
    filtrados: list[dict[str, object]] = []
    for registro in records:
        captured_at = _texto_limpo(registro.get("capturado_em", ""))
        try:
            capturado_em = datetime.fromisoformat(captured_at)
        except ValueError:
            continue
        if capturado_em >= limite:
            filtrados.append(registro)
    return filtrados


def _historico_tecnicos_em_janela_coleta(
    hora_inicio: int,
    hora_fim: int,
    agora: datetime | None = None,
) -> bool:
    referencia = agora or datetime.now()
    return hora_inicio <= referencia.hour <= hora_fim


def _normalizar_snapshot_tecnicos(records: list[dict[str, object]]) -> list[dict[str, object]]:
    campos_snapshot = (
        "tecnico",
        "tecnico_nome",
        "total_carteira",
        "abertas",
        "pendentes",
        "em_execucao",
        "encerradas_no_periodo",
        "recebidas_no_periodo",
    )
    snapshot_normalizado: list[dict[str, object]] = []
    for registro in records:
        item = {campo: registro.get(campo) for campo in campos_snapshot}
        snapshot_normalizado.append(item)
    snapshot_normalizado.sort(key=lambda item: (_texto_limpo(item.get("tecnico", "")), _texto_limpo(item.get("tecnico_nome", ""))))
    return snapshot_normalizado


def _extrair_ultima_coleta_tecnicos(records: list[dict[str, object]]) -> list[dict[str, object]]:
    ultimo_capturado_em = ""
    ultima_coleta: list[dict[str, object]] = []
    for registro in records:
        capturado_em = _texto_limpo(registro.get("capturado_em", ""))
        if not capturado_em:
            continue
        if capturado_em > ultimo_capturado_em:
            ultimo_capturado_em = capturado_em
            ultima_coleta = [registro]
        elif capturado_em == ultimo_capturado_em:
            ultima_coleta.append(registro)
    return ultima_coleta


def _atualizar_historico_tecnicos(
    base: Path,
    df: pd.DataFrame,
    refresh_targets: set[str],
    hora_inicio: int,
    hora_fim: int,
) -> list[dict[str, object]]:
    history_records = _carregar_tecnicos_history(base)
    precisa_capturar = "os" in refresh_targets or "all" in refresh_targets or not history_records
    if not precisa_capturar:
        return _prunar_tecnicos_history(history_records, TECNICOS_HISTORY_RETENCAO_DIAS)
    if not _historico_tecnicos_em_janela_coleta(hora_inicio, hora_fim):
        return _prunar_tecnicos_history(history_records, TECNICOS_HISTORY_RETENCAO_DIAS)

    captured_at = _agora_iso()
    previous_state = _carregar_estado_os_atual(base)
    had_previous_state = bool(previous_state)
    current_state: dict[str, dict[str, object]] = {}
    summary_map: dict[str, dict[str, object]] = {}

    def ensure_summary(tecnico_key: str, tecnico_nome: str) -> dict[str, object] | None:
        if not tecnico_key:
            return None
        if tecnico_key not in summary_map:
            summary_map[tecnico_key] = {
                "capturado_em": captured_at,
                "data_snapshot": captured_at[:10],
                "tecnico": tecnico_key,
                "tecnico_nome": _normalizar_nome_exibicao_tecnico(tecnico_nome, tecnico_key.upper()),
                "total_carteira": 0,
                "abertas": 0,
                "pendentes": 0,
                "em_execucao": 0,
                "encerradas_no_periodo": 0,
                "recebidas_no_periodo": 0,
            }
        else:
            summary_map[tecnico_key]["tecnico_nome"] = _normalizar_nome_exibicao_tecnico(
                tecnico_nome,
                str(summary_map[tecnico_key]["tecnico_nome"]),
            )
        return summary_map[tecnico_key]

    if not df.empty:
        for registro in df.fillna("").to_dict(orient="records"):
            os_id = _obter_chave_registro_os(registro)
            if not os_id:
                continue

            status = _texto_limpo(registro.get("status_dashboard", registro.get("status", "")))
            dono_key, dono_nome = _resolver_dono_os(registro)
            finalizador_key, finalizador_nome = _resolver_finalizador_os(registro)

            current_state[os_id] = {
                "os_id": os_id,
                "capturado_em": captured_at,
                "status": status,
                "tecnico": dono_key,
                "tecnico_nome": _normalizar_nome_exibicao_tecnico(dono_nome, finalizador_nome),
                "finalizador": finalizador_key,
                "finalizador_nome": _normalizar_nome_exibicao_tecnico(finalizador_nome),
            }

            if status != "Encerrada":
                summary = ensure_summary(dono_key, dono_nome)
                if summary is not None:
                    summary["total_carteira"] += 1
                    if status == "Aberta":
                        summary["abertas"] += 1
                    elif status == "Pendente":
                        summary["pendentes"] += 1
                    elif status == "Em execução":
                        summary["em_execucao"] += 1

            if not had_previous_state:
                continue

            anterior = previous_state.get(os_id)
            if status == "Encerrada":
                if anterior and _texto_limpo(anterior.get("status", "")) != "Encerrada":
                    encerramento_key = finalizador_key
                    encerramento_nome = finalizador_nome
                    summary = ensure_summary(encerramento_key, encerramento_nome)
                    if summary is not None:
                        summary["encerradas_no_periodo"] += 1
                continue

            if anterior is None:
                continue

            tecnico_anterior = _texto_limpo(anterior.get("tecnico", ""))
            if dono_key and tecnico_anterior != dono_key:
                summary = ensure_summary(dono_key, dono_nome)
                if summary is not None:
                    summary["recebidas_no_periodo"] += 1

    if summary_map:
        coleta_atual = [summary_map[chave] for chave in sorted(summary_map)]
        ultima_coleta = _extrair_ultima_coleta_tecnicos(history_records)
        if _normalizar_snapshot_tecnicos(coleta_atual) != _normalizar_snapshot_tecnicos(ultima_coleta):
            history_records.extend(coleta_atual)

    history_records = _prunar_tecnicos_history(history_records, TECNICOS_HISTORY_RETENCAO_DIAS)
    _salvar_tecnicos_history(base, history_records)
    _salvar_estado_os_atual(base, current_state)
    return history_records


def _resolver_tecnicos_classificacao(base: Path, config: dict[str, object]) -> dict[str, object]:
    classificacao = dict(config.get("classificacao", {}) or {})
    tecnicos_manuais = classificacao.get("tecnicos", [])
    tecnicos_resolvidos = [str(item).strip() for item in tecnicos_manuais if str(item).strip()]

    usar_api = bool(classificacao.get("usar_api_tecnicos", False))
    cache_segundos = int(classificacao.get("tecnicos_cache_segundos", 21600))
    client = SGPClient(config)

    if usar_api:
        tecnicos_api: list[dict[str, object]] = []
        try:
            if _cache_tecnicos_valido(base, max(cache_segundos, 60)):
                tecnicos_api = _carregar_tecnicos_cache(base)
            else:
                tecnicos_api = client.listar_tecnicos()
                _salvar_tecnicos_cache(base, tecnicos_api)
        except Exception:
            tecnicos_api = _carregar_tecnicos_cache(base)

        for tecnico in tecnicos_api:
            tecnicos_resolvidos.extend(_identificadores_tecnico(tecnico))

    classificacao["tecnicos"] = list(dict.fromkeys(tecnicos_resolvidos))
    config["classificacao"] = classificacao
    return config


def _buscar_os_periodo(client: SGPClient, data_inicio: str, data_fim: str) -> list[dict[str, object]]:
    raw_abertas = client.listar_ordens_servico_statuses(
        statuses=STATUS_ABERTAS,
        data_criacao_inicio=data_inicio,
        data_criacao_fim=data_fim,
    )
    raw_encerradas = client.listar_ordens_servico_statuses(
        statuses=STATUS_ENCERRADAS,
        data_finalizacao_inicio=data_inicio,
        data_finalizacao_fim=data_fim,
    )
    return raw_abertas + raw_encerradas


def _atualizar_os_cache_incremental(
    base: Path,
    config: dict[str, object],
    ano: int,
    mes: str,
    refresh_targets: set[str],
    janela_recente_dias: int,
    force_full_os: bool,
) -> pd.DataFrame:
    cache_atual = _carregar_os_cache(base, ano)
    if "os" not in refresh_targets and "all" not in refresh_targets:
        return _normalizar_df_cache_os(pd.DataFrame(cache_atual))

    client = SGPClient(config)
    inicio_ano, fim_ano = montar_periodo(ano, "Todos")
    ano_atual = date.today().year
    fazer_carga_completa = force_full_os or not cache_atual or ano != ano_atual
    df_cache = _normalizar_df_cache_os(pd.DataFrame(cache_atual))

    try:
        if fazer_carga_completa:
            raw_data = _buscar_os_periodo(client, inicio_ano, fim_ano)
            df = _deduplicar_df_os(preparar_dataframe(raw_data, config))
        else:
            data_inicio_recente = max(date(ano, 1, 1), date.today() - timedelta(days=max(janela_recente_dias - 1, 0)))
            raw_data = _buscar_os_periodo(client, data_inicio_recente.isoformat(), fim_ano)
            df_recente = _deduplicar_df_os(preparar_dataframe(raw_data, config))
            registros_recentes = _payload_os_cache(df_recente, ano, mes, str(config["url_base"]))
            chaves_recentes = {_obter_chave_registro_os(registro) for registro in registros_recentes if _obter_chave_registro_os(registro)}
            cache_filtrado = [
                registro
                for registro in cache_atual
                if not _registro_toca_janela_recente(registro, data_inicio_recente)
                and _obter_chave_registro_os(registro) not in chaves_recentes
            ]
            df = pd.DataFrame(cache_filtrado + registros_recentes)
            df = _normalizar_df_cache_os(df)
            df = _deduplicar_df_os(df)
    except Exception as exc:
        if not df_cache.empty:
            print(f"Aviso: falha ao atualizar O.S. no SGP ({exc}). Usando cache local.")
            df = df_cache.copy()
        else:
            raise

    if mes != "Todos" and not df.empty:
        df = df[df["mes_nome"] == mes].copy()

    df = _deduplicar_df_os(df)
    _salvar_os_cache(base, ano, _payload_os_cache(df, ano, mes, str(config["url_base"])))
    return df


def gerar_arquivos_dashboard(
    base: Path | None = None,
    refresh_targets: set[str] | None = None,
    rebuild_html: bool = False,
    force_full_os: bool = False,
) -> dict[str, Path]:
    base = base or Path(__file__).resolve().parent
    if refresh_targets is None:
        refresh_targets = {"all"}
    config = json.loads((base / "config.json").read_text(encoding="utf-8"))
    config = _resolver_tecnicos_classificacao(base, config)

    ano = int(config.get("dashboard", {}).get("ano_padrao", 2026))
    mes = config.get("dashboard", {}).get("mes_padrao", "Todos")
    refresh_seconds = int(config.get("dashboard", {}).get("atualizacao_segundos", 300))
    janela_recente_dias = int(config.get("dashboard", {}).get("janela_recente_dias", 45))
    votos_cache_segundos = int(config.get("dashboard", {}).get("votos_cache_segundos", refresh_seconds))
    historico_hora_inicio = int(config.get("dashboard", {}).get("tecnicos_history_hora_inicio", TECNICOS_HISTORY_HORA_INICIO_PADRAO))
    historico_hora_fim = int(config.get("dashboard", {}).get("tecnicos_history_hora_fim", TECNICOS_HISTORY_HORA_FIM_PADRAO))
    historico_hora_inicio = max(0, min(23, historico_hora_inicio))
    historico_hora_fim = max(0, min(23, historico_hora_fim))
    if historico_hora_inicio > historico_hora_fim:
        historico_hora_inicio = TECNICOS_HISTORY_HORA_INICIO_PADRAO
        historico_hora_fim = TECNICOS_HISTORY_HORA_FIM_PADRAO

    df = _atualizar_os_cache_incremental(
        base=base,
        config=config,
        ano=ano,
        mes=mes,
        refresh_targets=refresh_targets,
        janela_recente_dias=janela_recente_dias,
        force_full_os=force_full_os,
    )

    df_finalizadas = (
        df[df["status_dashboard"] == "Encerrada"].copy()
        if not df.empty and "status_dashboard" in df.columns
        else df.copy()
    )
    resumo = resumo_mensal(df_finalizadas)
    ranking = ranking_finalizadores(df_finalizadas)
    votos_df = _carregar_ou_atualizar_votos_df(base, refresh_targets, votos_cache_segundos)
    historico_tecnicos = _atualizar_historico_tecnicos(
        base,
        df,
        refresh_targets,
        historico_hora_inicio,
        historico_hora_fim,
    )

    dashboard_saida = base / "dashboard_os_sgp.html"
    dashboard_data_saida = base / "dashboard_data.json"

    payload = montar_payload_dashboard(
        resumo_df=resumo,
        ranking_df=ranking,
        detalhes_df=df,
        finalizadas_df=df_finalizadas,
        votos_df=votos_df,
        ano=ano,
        mes_selecionado=mes,
        refresh_seconds=refresh_seconds,
        sgp_base_url=config["url_base"],
        tecnico_history_records=historico_tecnicos,
    )
    dashboard_data_saida.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if rebuild_html or not dashboard_saida.exists():
        gerar_html_dashboard(
            resumo_df=resumo,
            ranking_df=ranking,
            detalhes_df=df,
            finalizadas_df=df_finalizadas,
            votos_df=votos_df,
            ano=ano,
            mes_selecionado=mes,
            refresh_seconds=refresh_seconds,
            sgp_base_url=config["url_base"],
            tecnico_history_records=historico_tecnicos,
            output_html=str(dashboard_saida),
            embutir_dados=False,
        )

    return {
        "dashboard": dashboard_saida,
        "dashboard_data": dashboard_data_saida,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Geração do dashboard técnico")
    parser.add_argument("--refresh-target", choices=["all", "os", "votos", "none"], default="all")
    parser.add_argument("--rebuild-html", action="store_true", help="Regenera o HTML shell do dashboard.")
    parser.add_argument("--force-full-os", action="store_true", help="Refaz a carga anual completa de O.S.")
    args = parser.parse_args()

    saidas = gerar_arquivos_dashboard(
        refresh_targets=set() if args.refresh_target == "none" else {args.refresh_target},
        rebuild_html=args.rebuild_html,
        force_full_os=args.force_full_os,
    )
    dashboard_saida = saidas["dashboard"]
    dashboard_data_saida = saidas["dashboard_data"]
    print(f"Dashboard disponível em: {dashboard_saida}")
    print(f"JSON de dados gerado em: {dashboard_data_saida}")


if __name__ == "__main__":
    main()
