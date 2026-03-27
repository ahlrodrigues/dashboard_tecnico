from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
import json
from pathlib import Path

import pandas as pd

from gerar_dashboard import gerar_html_dashboard, montar_payload_dashboard
from processar_os import preparar_dataframe, ranking_finalizadores, resumo_mensal
from sgp_client import SGPClient

STATUS_ABERTAS = [0, 2, 3]
STATUS_ENCERRADAS = [1]
VOTOS_CSV_URL = "https://net4you.com.br/votos_data.csv"
CACHE_DIR_NAME = ".cache"
OS_CACHE_FILENAME = "dashboard_os_cache.json"
VOTOS_CACHE_FILENAME = "dashboard_votos_cache.json"


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
    if "votos" not in refresh_targets and "all" not in refresh_targets:
        return _carregar_votos_cache(base)

    if _cache_votos_valido(base, max(cache_segundos, 30)):
        return _carregar_votos_cache(base)

    votos_df = carregar_votos_df()
    _salvar_votos_cache(base, votos_df)
    return votos_df


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
    refresh_targets = refresh_targets or {"all"}
    config = json.loads((base / "config.json").read_text(encoding="utf-8"))

    ano = int(config.get("dashboard", {}).get("ano_padrao", 2026))
    mes = config.get("dashboard", {}).get("mes_padrao", "Todos")
    refresh_seconds = int(config.get("dashboard", {}).get("atualizacao_segundos", 300))
    janela_recente_dias = int(config.get("dashboard", {}).get("janela_recente_dias", 45))
    votos_cache_segundos = int(config.get("dashboard", {}).get("votos_cache_segundos", refresh_seconds))

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
            output_html=str(dashboard_saida),
            embutir_dados=False,
        )

    return {
        "dashboard": dashboard_saida,
        "dashboard_data": dashboard_data_saida,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Geração do dashboard técnico")
    parser.add_argument("--refresh-target", choices=["all", "os", "votos"], default="all")
    parser.add_argument("--rebuild-html", action="store_true", help="Regenera o HTML shell do dashboard.")
    parser.add_argument("--force-full-os", action="store_true", help="Refaz a carga anual completa de O.S.")
    args = parser.parse_args()

    saidas = gerar_arquivos_dashboard(
        refresh_targets={args.refresh_target},
        rebuild_html=args.rebuild_html,
        force_full_os=args.force_full_os,
    )
    dashboard_saida = saidas["dashboard"]
    dashboard_data_saida = saidas["dashboard_data"]
    print(f"Dashboard disponível em: {dashboard_saida}")
    print(f"JSON de dados gerado em: {dashboard_data_saida}")


if __name__ == "__main__":
    main()
