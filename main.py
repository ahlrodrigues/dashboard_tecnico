from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

from sgp_client import SGPClient
from processar_os import preparar_dataframe, resumo_mensal, ranking_finalizadores
from gerar_dashboard import gerar_html_dashboard

STATUS_COLETA = [0, 1, 2, 3]


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


def main() -> None:
    base = Path(__file__).resolve().parent
    config = json.loads((base / "config.json").read_text(encoding="utf-8"))

    ano = int(config.get("dashboard", {}).get("ano_padrao", 2026))
    mes = config.get("dashboard", {}).get("mes_padrao", "Todos")
    refresh_seconds = int(config.get("dashboard", {}).get("atualizacao_segundos", 300))

    # A coleta continua ampla por criacao para nao perder OS abertas; no dashboard,
    # a data-base principal passa a ser o encerramento, com fallback para criacao.
    data_inicio, data_fim = montar_periodo(ano, "Todos")

    client = SGPClient(config)
    raw_data = client.listar_ordens_servico_statuses(
        statuses=STATUS_COLETA,
        data_criacao_inicio=data_inicio,
        data_criacao_fim=data_fim,
    )

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
        ano=ano,
        mes_selecionado=mes,
        refresh_seconds=refresh_seconds,
        sgp_base_url=config["url_base"],
        output_html=str(dashboard_saida),
    )

    print(f"Dashboard gerado em: {dashboard_saida}")
    print(f"CSV tratado gerado em: {csv_saida}")


if __name__ == "__main__":
    main()
