from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

from sgp_client import SGPClient
from processar_os import preparar_dataframe, resumo_mensal, ranking_finalizadores
from gerar_dashboard import gerar_html_dashboard

STATUS_ABERTAS = [0, 2, 3]
STATUS_ENCERRADAS = [1]
VOTOS_CSV_URL = "https://net4you.com.br/votos_data.csv"


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


def gerar_arquivos_dashboard(base: Path | None = None) -> dict[str, Path]:
    base = base or Path(__file__).resolve().parent
    config = json.loads((base / "config.json").read_text(encoding="utf-8"))

    ano = int(config.get("dashboard", {}).get("ano_padrao", 2026))
    mes = config.get("dashboard", {}).get("mes_padrao", "Todos")
    refresh_seconds = int(config.get("dashboard", {}).get("atualizacao_segundos", 300))

    # Para manter o dashboard coerente com a data-base:
    # - OS encerradas sao coletadas pela data de finalizacao
    # - OS abertas/em execucao/pendentes continuam pela data de criacao
    data_inicio, data_fim = montar_periodo(ano, "Todos")

    client = SGPClient(config)
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

    raw_data = raw_abertas + raw_encerradas

    df = preparar_dataframe(raw_data, config)

    if not df.empty:
        for coluna_unica in ["id", "ordem_servico"]:
            if coluna_unica in df.columns:
                df = df.drop_duplicates(subset=[coluna_unica]).copy()
                break

    if mes != "Todos" and not df.empty:
        df = df[df["mes_nome"] == mes].copy()

    df_finalizadas = df[df["status_dashboard"] == "Encerrada"].copy() if not df.empty else df.copy()

    resumo = resumo_mensal(df_finalizadas)
    ranking = ranking_finalizadores(df_finalizadas)
    votos_df = carregar_votos_df()

    csv_saida = base / "os_finalizadas_tratadas.csv"
    dashboard_saida = base / "dashboard_os_sgp.html"

    if not df.empty:
        df.to_csv(csv_saida, index=False, encoding="utf-8-sig")
    else:
        pd.DataFrame().to_csv(csv_saida, index=False, encoding="utf-8-sig")

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
    )

    return {
        "dashboard": dashboard_saida,
        "csv": csv_saida,
    }


def main() -> None:
    saidas = gerar_arquivos_dashboard()
    dashboard_saida = saidas["dashboard"]
    csv_saida = saidas["csv"]
    print(f"Dashboard gerado em: {dashboard_saida}")
    print(f"CSV tratado gerado em: {csv_saida}")


if __name__ == "__main__":
    main()
