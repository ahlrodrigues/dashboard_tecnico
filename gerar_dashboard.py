from __future__ import annotations

import json
from datetime import date
from html import escape
from pathlib import Path
import pandas as pd

from version import VERSION, get_dashboard_version_label

VERSAO_DASHBOARD = get_dashboard_version_label()


def _serializar_registros(df: pd.DataFrame, detalhe_cols: list[str]) -> list[dict[str, str | int | float | None]]:
    if df.empty:
        return []

    view = df.copy()

    if "data_finalizacao_dashboard" in view.columns:
        view["data_finalizacao_dashboard"] = view["data_finalizacao_dashboard"].dt.strftime("%Y-%m-%d")
    if "data_criacao_dashboard" in view.columns:
        view["data_criacao_dashboard"] = view["data_criacao_dashboard"].dt.strftime("%Y-%m-%d")
    if "data_base_dashboard" in view.columns:
        view["data_base_dashboard"] = view["data_base_dashboard"].dt.strftime("%Y-%m-%d")

    base_cols = list(detalhe_cols)
    for extra_col in [
        "mes_nome",
        "mes_num",
        "grupo_dashboard",
        "grupo_encerramento_dashboard",
        "total_os_encerramento_dashboard",
        "contrato_status_dashboard",
        "finalizado_por_dashboard",
        "tecnicos_auxiliares",
        "data_base_dashboard",
        "data_finalizacao_dashboard",
        "data_criacao_dashboard",
        "mes_criacao_num",
        "mes_criacao_nome",
        "responsavel",
        "status_dashboard",
    ]:
        if extra_col in view.columns and extra_col not in base_cols:
            base_cols.append(extra_col)

    registros = (
        view[base_cols]
        .fillna("")
        .to_dict(orient="records")
    )
    return registros


def _serializar_votos(df: pd.DataFrame, votos_cols: list[str]) -> list[dict[str, str | int | float | None]]:
    if df.empty or not votos_cols:
        return []

    view = df.copy()
    if "data_voto_dashboard" in view.columns:
        view["data_voto_dashboard"] = view["data_voto_dashboard"].dt.strftime("%Y-%m-%d")

    base_cols = list(votos_cols)
    if "data_voto_dashboard" in view.columns and "data_voto_dashboard" not in base_cols:
        base_cols.append("data_voto_dashboard")

    return view[base_cols].fillna("").to_dict(orient="records")


def montar_payload_dashboard(
    resumo_df: pd.DataFrame,
    ranking_df: pd.DataFrame,
    detalhes_df: pd.DataFrame,
    finalizadas_df: pd.DataFrame,
    votos_df: pd.DataFrame,
    ano: int,
    mes_selecionado: str,
    refresh_seconds: int,
    sgp_base_url: str,
) -> dict[str, object]:
    detalhe_cols: list[str] = []
    for cand in ["id", "ordem_servico", "cliente", "contrato", "pop", "motivo", "status"]:
        if cand in detalhes_df.columns:
            detalhe_cols.append(cand)

    extra_cols = [
        "data_finalizacao_dashboard",
        "finalizado_por_dashboard",
        "grupo_dashboard",
    ]
    detalhe_cols += [c for c in extra_cols if c in detalhes_df.columns and c not in detalhe_cols]
    detalhe_labels = {
        "data_finalizacao_dashboard": "Data finalizacao",
        "data_base_dashboard": "Data base do recorte",
        "data_criacao_dashboard": "Criada em",
        "finalizado_por_dashboard": "Finalizado por",
        "grupo_dashboard": "Grupo",
        "status_dashboard": "Status",
    }

    cards = {
        "aberta": int((detalhes_df["status_dashboard"] == "Aberta").sum()) if not detalhes_df.empty else 0,
        "encerrada": int(len(finalizadas_df)) if not finalizadas_df.empty else 0,
        "encerrada_tecnicos": int((finalizadas_df["grupo_encerramento_dashboard"] == "Técnicos").sum())
        if "grupo_encerramento_dashboard" in finalizadas_df.columns and not finalizadas_df.empty else 0,
        "pendente": int((detalhes_df["status_dashboard"] == "Pendente").sum()) if not detalhes_df.empty else 0,
        "em_execucao": int((detalhes_df["status_dashboard"] == "Em execução").sum()) if not detalhes_df.empty else 0,
        "inviabilidade": int((detalhes_df["contrato_status_dashboard"].fillna("").astype(str).str.strip() == "Inviabilidade Técnica").sum())
        if "contrato_status_dashboard" in detalhes_df.columns and not detalhes_df.empty else 0,
        "instalacoes": int((detalhes_df["motivo"].fillna("").astype(str).str.strip() == "Instalação de KIT").sum()) if "motivo" in detalhes_df.columns else 0,
        "remocoes": int((detalhes_df["motivo"].fillna("").astype(str).str.strip() == "Remoção de KIT").sum()) if "motivo" in detalhes_df.columns else 0,
        "por_outros": int(len(finalizadas_df) - (finalizadas_df["grupo_encerramento_dashboard"] == "Técnicos").sum())
        if "grupo_encerramento_dashboard" in finalizadas_df.columns and not finalizadas_df.empty else 0,
    }

    detalhes_data = _serializar_registros(detalhes_df, detalhe_cols) if detalhe_cols else []
    votos_cols = [col for col in votos_df.columns.tolist() if col != "data_voto_dashboard"] if not votos_df.empty else []
    votos_data = _serializar_votos(votos_df, votos_cols)
    meses_ordem = resumo_df["mes_nome"].tolist()
    refresh_seconds = max(int(refresh_seconds), 30)

    if "data_base_dashboard" in detalhes_df.columns and not detalhes_df["data_base_dashboard"].dropna().empty:
        data_inicial_padrao = detalhes_df["data_base_dashboard"].dropna().min().strftime("%Y-%m-%d")
        data_final_padrao = detalhes_df["data_base_dashboard"].dropna().max().strftime("%Y-%m-%d")
    else:
        data_inicial_padrao = ""
        data_final_padrao = ""
    data_snapshot_atual = data_final_padrao or date.today().strftime("%Y-%m-%d")

    return {
        "ano": ano,
        "mes_selecionado": mes_selecionado,
        "refresh_seconds": refresh_seconds,
        "sgp_base_url": sgp_base_url.rstrip("/"),
        "titulo_periodo": "Encerramentos por data de encerramento; Status Operacional pelo backlog atual no dia filtrado",
        "detalhe_cols": detalhe_cols,
        "detalhe_labels": detalhe_labels,
        "cards": cards,
        "detalhes_data": detalhes_data,
        "votos_cols": votos_cols,
        "votos_data": votos_data,
        "meses_ordem": meses_ordem,
        "data_inicial_padrao": data_inicial_padrao,
        "data_final_padrao": data_final_padrao,
        "data_snapshot_atual": data_snapshot_atual,
        "ranking_cols": ranking_df.columns.tolist() if not ranking_df.empty else [],
    }


def gerar_html_dashboard(
    resumo_df: pd.DataFrame,
    ranking_df: pd.DataFrame,
    detalhes_df: pd.DataFrame,
    finalizadas_df: pd.DataFrame,
    votos_df: pd.DataFrame,
    ano: int,
    mes_selecionado: str,
    refresh_seconds: int,
    sgp_base_url: str,
    output_html: str,
    embutir_dados: bool = True,
) -> None:
    payload = montar_payload_dashboard(
        resumo_df=resumo_df,
        ranking_df=ranking_df,
        detalhes_df=detalhes_df,
        finalizadas_df=finalizadas_df,
        votos_df=votos_df,
        ano=ano,
        mes_selecionado=mes_selecionado,
        refresh_seconds=refresh_seconds,
        sgp_base_url=sgp_base_url,
    )
    detalhe_cols = payload["detalhe_cols"]
    detalhe_labels = payload["detalhe_labels"]
    cards = payload["cards"]
    detalhes_data = payload["detalhes_data"]
    votos_cols = payload["votos_cols"]
    votos_data = payload["votos_data"]
    meses_ordem = payload["meses_ordem"]
    refresh_seconds = payload["refresh_seconds"]
    data_inicial_padrao = payload["data_inicial_padrao"]
    data_final_padrao = payload["data_final_padrao"]
    data_snapshot_atual = payload["data_snapshot_atual"]
    titulo_periodo = payload["titulo_periodo"]
    titulo_dashboard = f"Dashboard de OS SGP - {VERSAO_DASHBOARD}"
    titulo_dashboard_base = "Dashboard de OS SGP"
    dados_embutidos = detalhes_data if embutir_dados else []
    votos_embutidos = votos_data if embutir_dados else []
    header_cols = "".join(
        f'<th aria-sort="none"><button type="button" class="sort-header" data-col="{escape(col)}" data-label="{escape(detalhe_labels.get(col, col))}"><span class="sort-header-label">{escape(detalhe_labels.get(col, col))}</span><span class="sort-indicator" aria-hidden="true">△</span></button></th>'
        for col in detalhe_cols
    )
    votos_display_labels = {
        **{col: col for col in votos_cols},
        "auxiliares_dupla_dashboard": "auxiliares_no_dia",
        "papel_dupla_dashboard": "papel_no_dia",
        "responsavel_dupla_dashboard": "consolidado_para",
    }
    votos_display_cols = votos_cols + ["auxiliares_dupla_dashboard", "papel_dupla_dashboard", "responsavel_dupla_dashboard"]
    votos_header_cols = "".join(
        f'<th aria-sort="none"><button type="button" class="sort-header" data-col="{escape(col)}"><span class="sort-header-label">{escape(votos_display_labels.get(col, col))}</span><span class="sort-indicator" aria-hidden="true">△</span></button></th>'
        for col in votos_display_cols
    )

    html = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{escape(titulo_dashboard)}</title>
  <style>
    :root {{
      --bg: #eef3f1;
      --panel: #fcfdf8;
      --panel-strong: #ffffff;
      --text: #173229;
      --muted: #587166;
      --line: #d8e3dc;
      --accent: #17624c;
      --accent-soft: #dcefe7;
      --shadow: 0 18px 40px rgba(23, 50, 41, 0.10);
    }}
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(113, 170, 143, 0.22), transparent 28%),
        linear-gradient(180deg, #f7fbf8 0%, var(--bg) 100%);
      font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
    }}
    .wrap {{
      max-width: 1320px;
      margin: 28px auto;
      padding: 0 18px 40px;
    }}
    .hero {{
      background: linear-gradient(135deg, rgba(23, 98, 76, 0.96), rgba(38, 125, 98, 0.88));
      color: #f7fffb;
      border-radius: 24px;
      padding: 28px;
      box-shadow: var(--shadow);
      margin-bottom: 20px;
    }}
    .hero-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }}
    .hero-titles {{
      min-width: 0;
    }}
    .hero h1 {{
      margin: 0 0 8px;
      font-size: clamp(28px, 4vw, 42px);
      line-height: 1.05;
    }}
    .hero-version {{
      font-size: 0.36em;
      font-weight: 700;
      letter-spacing: 0.12em;
      opacity: 0.82;
      vertical-align: super;
      margin-left: 10px;
      white-space: nowrap;
    }}
    .hero p {{
      margin: 0;
      color: rgba(247, 255, 251, 0.78);
      font-size: 15px;
    }}
    .refresh-badge {{
      flex: 0 1 240px;
      min-width: 180px;
      min-height: 92px;
      padding: 14px 16px;
      border-radius: 18px;
      background: rgba(247, 255, 251, 0.12);
      border: 1px solid rgba(247, 255, 251, 0.18);
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      text-align: center;
      gap: 10px;
    }}
    .refresh-badge strong {{
      display: block;
      font-size: 12px;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      color: rgba(247, 255, 251, 0.78);
    }}
    .refresh-badge span {{
      display: block;
      margin-top: 4px;
      font-size: 26px;
      font-weight: 800;
      letter-spacing: -0.03em;
    }}
    .refresh-badge button {{
      border: 0;
      border-radius: 999px;
      padding: 10px 16px;
      font-size: 13px;
      font-weight: 700;
      color: var(--accent);
      background: #f7fffb;
      cursor: pointer;
      transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
      box-shadow: 0 10px 24px rgba(23, 50, 41, 0.12);
    }}
    .refresh-badge button:hover {{
      transform: translateY(-1px);
      background: #ffffff;
    }}
    .refresh-badge button:active {{
      transform: translateY(0);
    }}
    .refresh-badge button[disabled] {{
      opacity: 0.72;
      cursor: progress;
      box-shadow: none;
    }}
    .update-overlay {{
      position: fixed;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
      background: rgba(12, 38, 30, 0.46);
      backdrop-filter: blur(8px);
      opacity: 0;
      visibility: hidden;
      pointer-events: none;
      transition: opacity 0.24s ease, visibility 0.24s ease;
      z-index: 40;
    }}
    .update-overlay.active {{
      opacity: 1;
      visibility: visible;
      pointer-events: auto;
    }}
    .update-dialog {{
      width: min(460px, 100%);
      padding: 28px 26px;
      border-radius: 24px;
      background: rgba(252, 253, 248, 0.98);
      border: 1px solid rgba(23, 98, 76, 0.12);
      box-shadow: 0 24px 64px rgba(23, 50, 41, 0.18);
      text-align: center;
    }}
    .update-dialog h3 {{
      margin: 0 0 10px;
      font-size: 22px;
      color: var(--text);
    }}
    .update-dialog p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.5;
      font-size: 14px;
    }}
    .update-pulse {{
      width: 88px;
      height: 88px;
      margin: 0 auto 18px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      position: relative;
      background:
        radial-gradient(circle at center, rgba(23, 98, 76, 0.20), rgba(23, 98, 76, 0.06));
    }}
    .update-pulse::before,
    .update-pulse::after {{
      content: "";
      position: absolute;
      inset: 0;
      border-radius: 50%;
      border: 2px solid rgba(23, 98, 76, 0.18);
      animation: refresh-wave 1.8s ease-out infinite;
    }}
    .update-pulse::after {{
      animation-delay: 0.9s;
    }}
    .update-spinner {{
      width: 38px;
      height: 38px;
      border-radius: 50%;
      border: 4px solid rgba(23, 98, 76, 0.14);
      border-top-color: var(--accent);
      animation: refresh-spin 0.9s linear infinite;
    }}
    .update-status {{
      margin-top: 14px;
      min-height: 21px;
      font-size: 13px;
      font-weight: 700;
      color: var(--accent);
    }}
    .update-overlay.error .update-status {{
      color: #a13a2a;
    }}
    @keyframes refresh-spin {{
      to {{
        transform: rotate(360deg);
      }}
    }}
    @keyframes refresh-wave {{
      0% {{
        transform: scale(0.82);
        opacity: 0.72;
      }}
      100% {{
        transform: scale(1.34);
        opacity: 0;
      }}
    }}
    .toolbar {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 14px;
      margin: 20px 0;
    }}
    .filter-card,
    .card,
    .panel {{
      background: var(--panel-strong);
      border: 1px solid var(--line);
      border-radius: 20px;
      box-shadow: var(--shadow);
    }}
    .filter-card {{
      padding: 16px;
    }}
    .filter-card label {{
      display: block;
      margin-bottom: 8px;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--muted);
    }}
    .filter-card select,
    .filter-card input {{
      width: 100%;
      border-radius: 14px;
      border: 1px solid var(--line);
      padding: 12px 14px;
      font-size: 14px;
      background: #f8fbf9;
      color: var(--text);
    }}
    .quick-range {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin: -6px 0 20px;
    }}
    .quick-range button {{
      border: 1px solid var(--line);
      background: var(--panel-strong);
      color: var(--text);
      border-radius: 999px;
      padding: 10px 14px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      box-shadow: var(--shadow);
      transition: transform 0.18s ease, background 0.18s ease, border-color 0.18s ease;
    }}
    .quick-range button:hover {{
      transform: translateY(-1px);
      background: #ffffff;
      border-color: rgba(23, 98, 76, 0.22);
    }}
    .cards-stack {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
      margin-bottom: 18px;
      align-items: stretch;
    }}
    .summary-card {{
      min-height: 0;
      height: 100%;
      padding: 22px 20px;
      display: grid;
      grid-template-columns: minmax(220px, 300px) minmax(0, 1fr);
      gap: 18px;
      align-items: start;
      background:
        linear-gradient(180deg, rgba(220, 239, 231, 0.55), rgba(255, 255, 255, 0.96));
      position: relative;
      overflow: hidden;
    }}
    .summary-card::after {{
      content: "";
      position: absolute;
      inset: auto -22px -22px auto;
      width: 86px;
      height: 86px;
      border-radius: 50%;
      background: rgba(23, 98, 76, 0.08);
    }}
    .summary-card.primary {{
      background: linear-gradient(135deg, rgba(23, 98, 76, 0.16), rgba(255, 255, 255, 0.98));
      grid-template-columns: 1fr;
      grid-template-rows: minmax(74px, auto) 1fr;
    }}
    .summary-card.secondary {{
      grid-template-columns: 1fr;
      grid-template-rows: minmax(74px, auto) 1fr;
    }}
    .summary-card.tertiary {{
      background: linear-gradient(135deg, rgba(220, 239, 231, 0.92), rgba(255, 255, 255, 0.98));
      grid-column: 1 / -1;
      grid-template-columns: 1fr;
    }}
    .summary-card.quaternary {{
      background: linear-gradient(135deg, rgba(228, 243, 237, 0.92), rgba(255, 255, 255, 0.98));
      grid-column: 1 / -1;
      grid-template-columns: 1fr;
    }}
    .summary-card.primary .summary-card-head,
    .summary-card.secondary .summary-card-head,
    .summary-card.tertiary .summary-card-head,
    .summary-card.quaternary .summary-card-head {{
      padding-right: 0;
      margin-bottom: 2px;
    }}
    .summary-card.primary .summary-card-head,
    .summary-card.secondary .summary-card-head {{
      min-height: 74px;
    }}
    .summary-card h3 {{
      margin: 0 0 6px;
      font-size: 18px;
      line-height: 1.2;
      color: var(--text);
      position: relative;
      z-index: 1;
    }}
    .summary-card .caption {{
      margin: 0;
      font-size: 13px;
      color: var(--muted);
      position: relative;
      z-index: 1;
    }}
    .summary-card-head {{
      position: relative;
      z-index: 1;
      padding-right: 8px;
      align-self: start;
      justify-self: start;
      text-align: left;
    }}
    .metric-grid {{
      width: 100%;
      display: flex;
      flex-wrap: wrap;
      flex-direction: row;
      gap: 12px;
      position: relative;
      z-index: 1;
      align-self: start;
      justify-content: flex-start;
      align-content: flex-start;
      align-items: stretch;
    }}
    .metric-grid.scrollable {{
      max-height: none;
      overflow: visible;
      padding-right: 0;
    }}
    .metric-grid.flow {{
      justify-content: flex-start;
      width: 100%;
    }}
    .metric-grid.flow .metric-item {{
      flex: 0 1 calc((100% - 60px) / 6);
      min-width: 150px;
    }}
    .summary-card.primary .metric-grid,
    .summary-card.secondary .metric-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      width: 100%;
      justify-content: stretch;
      align-content: start;
      align-items: stretch;
      align-self: end;
    }}
    .metric-item {{
      width: auto;
      min-width: 180px;
      max-width: 100%;
      padding: 12px 16px 10px;
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.72);
      border: 1px solid rgba(23, 98, 76, 0.10);
      min-height: 84px;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      text-align: center;
      flex: 1 1 180px;
    }}
    .summary-card.primary .metric-item,
    .summary-card.secondary .metric-item {{
      min-width: 0;
      padding: 12px 10px 10px;
      display: grid;
      grid-template-rows: minmax(34px, auto) 1fr;
      align-content: start;
    }}
    .metric-item.compact {{
      min-height: 84px;
      padding: 12px 12px 10px;
    }}
    .metric-label {{
      display: block;
      margin-bottom: 8px;
      font-size: 12px;
      line-height: 1.2;
      color: var(--muted);
      white-space: nowrap;
    }}
    .summary-card.primary .metric-label,
    .summary-card.secondary .metric-label {{
      white-space: normal;
      overflow-wrap: anywhere;
      font-size: 11px;
      min-height: 34px;
      margin-bottom: 4px;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .metric-value {{
      display: block;
      font-size: 32px;
      font-weight: 800;
      letter-spacing: -0.03em;
    }}
    .summary-card.primary .metric-value,
    .summary-card.secondary .metric-value {{
      font-size: 28px;
    }}
    .variation {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-weight: 700;
      white-space: nowrap;
    }}
    .variation.up {{
      color: #17624c;
    }}
    .variation.down {{
      color: #b24040;
    }}
    .variation.flat {{
      color: #587166;
    }}
    .grid-panels {{
      display: grid;
      grid-template-columns: 1.05fr 0.95fr;
      gap: 18px;
    }}
    .panel {{
      padding: 18px;
      overflow: hidden;
    }}
    .panel-stack {{
      display: grid;
      gap: 18px;
      align-content: start;
    }}
    .section-title {{
      margin: 0 0 14px;
      font-size: 18px;
    }}
    .panel-meta {{
      margin: -6px 0 14px;
      color: var(--muted);
      font-size: 13px;
    }}
    tbody tr.row-link {{
      cursor: pointer;
    }}
    tbody tr.row-link:hover {{
      background: rgba(184, 216, 200, 0.55);
    }}
    .full {{
      margin-top: 18px;
    }}
    .table-wrap {{
      max-height: 460px;
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 16px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--panel);
    }}
    th, td {{
      padding: 11px 12px;
      border-bottom: 1px solid var(--line);
      font-size: 13px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      position: sticky;
      top: 0;
      z-index: 1;
      background: #edf5f0;
    }}
    th .sort-header {{
      display: flex;
      align-items: center;
      justify-content: flex-start;
      gap: 3px;
      width: 100%;
      border: 0;
      background: transparent;
      padding: 0;
      font: inherit;
      font-weight: 700;
      color: inherit;
      text-align: left;
      cursor: pointer;
    }}
    th .sort-header-label {{
      flex: 0 1 auto;
      min-width: 0;
    }}
    th .sort-indicator {{
      flex: none;
      color: var(--muted);
      font-size: 11px;
      line-height: 1;
    }}
    th[aria-sort="ascending"] .sort-indicator,
    th[aria-sort="descending"] .sort-indicator {{
      color: var(--accent);
    }}
    tbody tr:nth-child(even) {{
      background: rgba(220, 239, 231, 0.23);
    }}
    tbody tr:hover {{
      background: rgba(220, 239, 231, 0.40);
    }}
    tbody tr.duplicate-vote-row:nth-child(even),
    tbody tr.duplicate-vote-row {{
      background: rgba(208, 74, 74, 0.10);
    }}
    tbody tr.duplicate-vote-row:hover {{
      background: rgba(208, 74, 74, 0.16);
    }}
    td.duplicate-vote-cell {{
      color: #a12b2b;
      font-weight: 800;
    }}
    .empty {{
      padding: 24px;
      text-align: center;
      color: var(--muted);
    }}
    .chip {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 10px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 12px;
      font-weight: 700;
    }}
    canvas {{
      width: 100% !important;
      height: 360px !important;
    }}
    @media (max-width: 1100px) {{
      .toolbar,
	      .cards-stack {{
	        grid-template-columns: 1fr;
	      }}
	      .summary-card.primary .metric-grid,
	      .summary-card.secondary .metric-grid {{
	        grid-template-columns: repeat(2, minmax(0, 1fr));
	      }}
	      .grid-panels {{
	        grid-template-columns: 1fr;
	      }}
	    }}
	    @media (max-width: 720px) {{
	      .toolbar {{
	        grid-template-columns: 1fr;
	      }}
	      .metric-grid {{
	        justify-content: flex-start;
	      }}
	      .summary-card.primary .metric-grid,
	      .summary-card.secondary .metric-grid {{
	        grid-template-columns: 1fr;
	      }}
	      .metric-grid.flow .metric-item {{
	        flex-basis: 180px;
	      }}
	      .summary-card {{
	        grid-template-columns: 1fr;
	        gap: 14px;
	      }}
	      .summary-card {{
	        min-height: 0;
	      }}
	      .wrap {{
	        padding: 0 14px 28px;
      }}
      .hero {{
        padding: 22px;
      }}
      .hero-head {{
        flex-direction: column;
      }}
      .refresh-badge {{
        width: 100%;
      }}
    }}
  </style>
</head>
<body>
  <div class="update-overlay" id="updateOverlay" aria-live="polite" aria-hidden="true">
    <div class="update-dialog">
      <div class="update-pulse" aria-hidden="true">
        <div class="update-spinner"></div>
      </div>
      <h3>Atualizando arquivos</h3>
      <p id="updateOverlayMessage">Atualizando o HTML e os dados do dashboard. Isso pode levar alguns segundos.</p>
      <div class="update-status" id="updateOverlayStatus">Conectando ao serviço de atualização...</div>
    </div>
  </div>
  <div class="wrap">
    <section class="hero">
      <div class="hero-head">
        <div class="hero-titles">
          <h1>{escape(titulo_dashboard_base)}<span class="hero-version">{escape(VERSAO_DASHBOARD)}</span></h1>
          <p>{escape(titulo_periodo)}</p>
        </div>
        <div class="refresh-badge">
          <strong>Atualiza em</strong>
          <span id="refreshCountdown"></span>
          <button id="refreshNowButton" type="button">Atualizar agora</button>
        </div>
      </div>
    </section>

    <section class="toolbar">
      <div class="filter-card">
        <label for="filtroDataInicial">Data inicial</label>
        <input id="filtroDataInicial" type="date"/>
      </div>
      <div class="filter-card">
        <label for="filtroDataFinal">Data final</label>
        <input id="filtroDataFinal" type="date"/>
      </div>
      <div class="filter-card">
        <label for="filtroUsuario">Usuário</label>
        <select id="filtroUsuario"></select>
      </div>
      <div class="filter-card">
        <label for="filtroGrupo">Grupo</label>
        <select id="filtroGrupo"></select>
      </div>
      <div class="filter-card">
        <label for="filtroPop">POP</label>
        <select id="filtroPop"></select>
      </div>
    </section>

    <section class="quick-range">
      <button type="button" data-range="hoje">Hoje</button>
      <button type="button" data-range="ontem">Ontem</button>
      <button type="button" data-range="7dias">Últimos 7 dias</button>
      <button type="button" data-range="30dias">Últimos 30 dias</button>
      <button type="button" data-range="mes-atual">Mês atual</button>
    </section>

    <section class="toolbar">
      <div class="filter-card" style="grid-column: span 5;">
        <label for="filtroBusca">Busca no detalhamento</label>
        <input id="filtroBusca" type="text" placeholder="Digite cliente, contrato, POP, motivo ou usuário"/>
      </div>
    </section>

	    <div class="cards-stack">
	      <div class="summary-card secondary">
	        <div class="summary-card-head">
	          <h3 id="tituloStatusOperacional">Status Operacional</h3>
	          <p class="caption">Backlog atual das ordens abertas, pendentes e em execucao no dia filtrado, para acompanhamento simultaneo da operacao.</p>
	        </div>
	        <div class="metric-grid cols-2">
	          <div class="metric-item"><span class="metric-label">Total de O.S. do recorte</span><span class="metric-value" id="cardTotalStatus">{len(detalhes_data)}</span></div>
	          <div class="metric-item"><span class="metric-label">Em aberto</span><span class="metric-value" id="cardAberta">{cards['aberta']}</span></div>
	          <div class="metric-item"><span class="metric-label">Pendentes</span><span class="metric-value" id="cardPendente">{cards['pendente']}</span></div>
	          <div class="metric-item"><span class="metric-label">Em execução</span><span class="metric-value" id="cardEmExecucao">{cards['em_execucao']}</span></div>
	        </div>
	      </div>
	      <div class="summary-card primary">
	        <div class="summary-card-head">
	          <h3 id="tituloEncerramentos">Encerramentos</h3>
	          <p class="caption">Visão consolidada das O.S. encerradas no recorte, com cortes por grupo técnico e por quem realizou o encerramento.</p>
	        </div>
	        <div class="metric-grid cols-2">
	          <div class="metric-item"><span class="metric-label">Total de O.S. encerradas</span><span class="metric-value" id="cardEncerrada">{cards['encerrada']}</span></div>
	          <div class="metric-item"><span class="metric-label">Encerradas pelo técnico</span><span class="metric-value" id="cardEncerradaTecnicos">{cards['encerrada_tecnicos']}</span></div>
	          <div class="metric-item"><span class="metric-label">Encerradas por outros</span><span class="metric-value" id="cardPorOutros">{cards['por_outros']}</span></div>
	        </div>
	      </div>
	      <div class="summary-card tertiary">
	        <div class="summary-card-head">
	          <h3 id="tituloMovimentacoes">Movimentações</h3>
	          <p class="caption">Distribuição completa dos atendimentos por motivo no recorte filtrado.</p>
	        </div>
	        <div class="metric-grid flow scrollable" id="movimentacoesGrid">
	          <div class="metric-item compact"><span class="metric-label">Inviabilidades</span><span class="metric-value" id="cardInviabilidade">{cards['inviabilidade']}</span></div>
	          <div class="metric-item compact"><span class="metric-label">Instalação de KIT</span><span class="metric-value" id="cardInstalacoes">{cards['instalacoes']}</span></div>
	          <div class="metric-item compact"><span class="metric-label">Remoção de KIT</span><span class="metric-value" id="cardRemocoes">{cards['remocoes']}</span></div>
	        </div>
	      </div>
	      <div class="summary-card quaternary">
	        <div class="summary-card-head">
	          <h3 id="tituloPops">POPs</h3>
	          <p class="caption">Distribuição das O.S. por POP no recorte filtrado.</p>
	        </div>
	        <div class="metric-grid flow scrollable" id="popsGrid">
	          <div class="metric-item compact"><span class="metric-label">Sem POPs no recorte</span><span class="metric-value">0</span></div>
	        </div>
	      </div>
	    </div>

	    <div class="panel full">
	      <h2 class="section-title" id="tituloDetalhamentoPops">Detalhamento por POP</h2>
	      <div class="panel-meta" id="detalhamentoPopsMeta">Mostrando as O.S. do recorte filtradas por POP.</div>
      <div class="table-wrap">
        <table id="tabelaDetalhamentoPops">
          <thead>
            <tr><th>Data</th><th>POP</th><th>OS</th><th>Cliente</th><th>Contrato</th><th>Status</th><th>Motivo</th><th>Responsável</th><th>Auxiliares</th></tr>
          </thead>
          <tbody id="detalhamentoPopsBody"></tbody>
        </table>
      </div>
    </div>

	    <div class="grid-panels">
	      <div class="panel">
	        <h2 class="section-title" id="tituloTempoBacklog">Tempo médio e backlog</h2>
	        <div class="panel-meta" id="painelTempoMeta">Tempo médio e backlog no recorte atual.</div>
	        <div class="table-wrap">
	          <table>
	            <thead>
	              <tr>
	                <th>Indicador</th>
	                <th>Valor</th>
	              </tr>
	            </thead>
	            <tbody id="tempoBacklogBody"></tbody>
	          </table>
	        </div>
	      </div>

      <div class="panel-stack">
        <div class="panel">
          <h2 class="section-title" id="tituloRanking">Ranking por finalizador</h2>
          <div class="panel-meta" id="rankingMeta">Ranking atualizado pelos filtros da página.</div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Finalizado Por</th>
                  <th>Grupo</th>
                  <th>Total</th>
                  <th>Var. mes anterior</th>
                </tr>
              </thead>
              <tbody id="rankingBody"></tbody>
            </table>
          </div>
        </div>

        <div class="panel">
          <h2 class="section-title" id="tituloRankingVotosResumo">Ranking de votação</h2>
          <div class="panel-meta" id="rankingVotosResumoMeta">Total de votos únicos por IP e data no recorte atual.</div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Técnico</th>
                  <th>Total</th>
                </tr>
              </thead>
              <tbody id="rankingVotosResumoBody"></tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

	    <div class="panel full">
	      <h2 class="section-title" id="tituloGraficoMensal">Gráfico mensal</h2>
	      <canvas id="graficoMensal"></canvas>
	    </div>

	    <div class="panel full">
	      <h2 class="section-title" id="tituloGraficoDiario">Evolução diária dos grupos</h2>
	      <div class="panel-meta" id="graficoDiarioMeta">Mostrando a evolução diária por grupo no mês selecionado.</div>
	      <canvas id="graficoDiario"></canvas>
	    </div>

	    <div class="panel full">
	      <h2 class="section-title" id="tituloDetalhamento">Detalhamento</h2>
	      <div class="panel-meta" id="detalheMeta">Mostrando os registros filtrados.</div>
      <div class="table-wrap">
        <table id="tabelaDetalhes">
          <thead id="detalhesHead">
            <tr>{header_cols}</tr>
          </thead>
          <tbody id="detalhesBody"></tbody>
        </table>
      </div>
    </div>

	    <div class="panel full">
	      <h2 class="section-title" id="tituloRankingVotos">Detalhamento dos votos</h2>
	      <div class="panel-meta" id="rankingVotosMeta">Tabela de votos atualizada pelo recorte de data da página.</div>
      <div class="table-wrap">
        <table id="tabelaRankingVotos">
          <thead id="rankingVotosHead">
            <tr>{votos_header_cols}</tr>
          </thead>
          <tbody id="rankingVotosBody"></tbody>
        </table>
      </div>
    </div>

	    <div class="panel full">
	      <h2 class="section-title" id="tituloReincidencia">Reincidência por cliente/contrato</h2>
	      <div class="panel-meta" id="reincidenciaMeta">Mostrando as O.S. dos clientes/contratos com reincidência em janela móvel de 30 dias.</div>
      <div class="table-wrap">
        <table id="tabelaReincidencias">
          <thead id="reincidenciasHead">
            <tr>{header_cols}</tr>
          </thead>
          <tbody id="reincidenciasBody"></tbody>
        </table>
      </div>
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <script>
    const detalheCols = {json.dumps(detalhe_cols, ensure_ascii=False)};
    const votosCols = {json.dumps(votos_cols, ensure_ascii=False)};
    const votosDisplayCols = {json.dumps(votos_display_cols, ensure_ascii=False)};
    const votosDisplayLabels = {json.dumps(votos_display_labels, ensure_ascii=False)};
    const mesesOrdem = {json.dumps(meses_ordem, ensure_ascii=False)};
    let detalhes = {json.dumps(dados_embutidos, ensure_ascii=False)};
    let votosData = {json.dumps(votos_embutidos, ensure_ascii=False)};
    let dataInicialPadrao = "{data_inicial_padrao}";
    let dataFinalPadrao = "{data_final_padrao}";
    let dataSnapshotAtual = "{data_snapshot_atual}";
    let datasDisponiveisOrdenadas = [];
    let dataMinDisponivel = "";
    let dataMaxDisponivel = "";
    let refreshSeconds = {refresh_seconds};
    let sgpBaseUrl = {json.dumps(sgp_base_url.rstrip("/"), ensure_ascii=False)};
    const filtroDataInicial = document.getElementById("filtroDataInicial");
    const filtroDataFinal = document.getElementById("filtroDataFinal");
    const filtroUsuario = document.getElementById("filtroUsuario");
    const filtroGrupo = document.getElementById("filtroGrupo");
    const filtroPop = document.getElementById("filtroPop");
    const filtroBusca = document.getElementById("filtroBusca");
    const quickRangeButtons = Array.from(document.querySelectorAll("[data-range]"));
    const refreshCountdown = document.getElementById("refreshCountdown");
    const refreshNowButton = document.getElementById("refreshNowButton");
    const updateOverlay = document.getElementById("updateOverlay");
    const updateOverlayMessage = document.getElementById("updateOverlayMessage");
    const updateOverlayStatus = document.getElementById("updateOverlayStatus");
    const backendBaseUrl = (() => {{
      if (window.location.protocol === "file:") {{
        return "http://127.0.0.1:8765";
      }}

      return window.location.origin || "";
    }})();
    const refreshApiUrl = `${{backendBaseUrl}}/api/refresh`;
    const refreshStatusUrl = `${{backendBaseUrl}}/api/refresh-status`;
    const dashboardDataUrl = `${{backendBaseUrl}}/api/dashboard-data`;
		    const tempoBacklogBody = document.getElementById("tempoBacklogBody");
		    const rankingBody = document.getElementById("rankingBody");
    const rankingVotosResumoBody = document.getElementById("rankingVotosResumoBody");
    const rankingVotosBody = document.getElementById("rankingVotosBody");
    const detalhamentoPopsBody = document.getElementById("detalhamentoPopsBody");
		    const detalhesBody = document.getElementById("detalhesBody");
    const reincidenciasBody = document.getElementById("reincidenciasBody");
		    const painelTempoMeta = document.getElementById("painelTempoMeta");
		    const rankingMeta = document.getElementById("rankingMeta");
    const detalhamentoPopsMeta = document.getElementById("detalhamentoPopsMeta");
    const rankingVotosResumoMeta = document.getElementById("rankingVotosResumoMeta");
    const rankingVotosMeta = document.getElementById("rankingVotosMeta");
	    const graficoDiarioMeta = document.getElementById("graficoDiarioMeta");
    const detalheMeta = document.getElementById("detalheMeta");
    const reincidenciaMeta = document.getElementById("reincidenciaMeta");
    const tituloEncerramentos = document.getElementById("tituloEncerramentos");
    const tituloStatusOperacional = document.getElementById("tituloStatusOperacional");
    const tituloMovimentacoes = document.getElementById("tituloMovimentacoes");
    const tituloPops = document.getElementById("tituloPops");
    const tituloDetalhamentoPops = document.getElementById("tituloDetalhamentoPops");
    const tituloTempoBacklog = document.getElementById("tituloTempoBacklog");
    const tituloRanking = document.getElementById("tituloRanking");
    const tituloRankingVotosResumo = document.getElementById("tituloRankingVotosResumo");
    const tituloRankingVotos = document.getElementById("tituloRankingVotos");
    const tituloGraficoMensal = document.getElementById("tituloGraficoMensal");
    const tituloGraficoDiario = document.getElementById("tituloGraficoDiario");
    const tituloDetalhamento = document.getElementById("tituloDetalhamento");
    const tituloReincidencia = document.getElementById("tituloReincidencia");
    const detalhesHead = document.getElementById("detalhesHead");
    const rankingVotosHead = document.getElementById("rankingVotosHead");
    const reincidenciasHead = document.getElementById("reincidenciasHead");
	    const movimentacoesGrid = document.getElementById("movimentacoesGrid");
	    const popsGrid = document.getElementById("popsGrid");
    const storageKey = "dashboard_tecnico_filtros";
    const aliasesUsuarios = {{
      joaopaulo: "joaopaulo",
      joaojaulo: "joaopaulo",
      jpaulo: "joaopaulo",
      luizcarlos: "luizcarlos",
      lcarlos: "luizcarlos",
    }};
    const rotulosCanonicosUsuarios = {{
      joaopaulo: "JOAO PAULO",
      luizcarlos: "LUIZ CARLOS",
      luizhenrique: "LUIZ HENRIQUE",
      ivison: "IVISON",
      allan: "Allan",
      charles: "Charles",
      everaldo: "Everaldo",
      valdeir: "Valdeir",
      franklin: "Franklin",
      robson: "Robson",
      micael: "MICAEL",
      francivaldo: "FRANCIVALDO",
      wilton: "WILTON",
      talis: "TALIS",
      eriki: "ERIKI",
      cabral: "CABRAL",
    }};
    let atualizandoArquivos = false;
    let pollingAtualizacaoId = null;
    let restanteRefresh = refreshSeconds;
    let intervaloRefreshId = null;
    let ordenacaoDetalhes = {{ col: "data_finalizacao_dashboard", dir: "desc" }};
    let ordenacaoRankingVotos = {{ col: votosCols[0] || "data", dir: "asc" }};
    let ordenacaoReincidencias = {{ col: "cliente", dir: "asc" }};

    function normalizarTexto(valor) {{
      return String(valor || "").trim();
    }}

    function recalcularMetadadosBase() {{
      datasDisponiveisOrdenadas = detalhes.map((registro) => obterDataFiltroTexto(registro)).filter(Boolean).sort();
      dataMinDisponivel = datasDisponiveisOrdenadas[0] || dataInicialPadrao || "";
      dataMaxDisponivel = datasDisponiveisOrdenadas[datasDisponiveisOrdenadas.length - 1] || dataFinalPadrao || dataMinDisponivel || "";
      restanteRefresh = refreshSeconds;
    }}

    function aplicarPayloadDashboard(payload) {{
      if (!payload || typeof payload !== "object") return;
      detalhes = Array.isArray(payload.detalhes_data) ? payload.detalhes_data : [];
      votosData = Array.isArray(payload.votos_data) ? payload.votos_data : [];
      dataInicialPadrao = normalizarTexto(payload.data_inicial_padrao);
      dataFinalPadrao = normalizarTexto(payload.data_final_padrao);
      dataSnapshotAtual = normalizarTexto(payload.data_snapshot_atual) || dataSnapshotAtual;
      refreshSeconds = Math.max(Number.parseInt(payload.refresh_seconds || refreshSeconds, 10) || refreshSeconds, 30);
      sgpBaseUrl = normalizarTexto(payload.sgp_base_url) || sgpBaseUrl;
      recalcularMetadadosBase();
    }}

    async function carregarDadosDashboardRemotos() {{
      if (window.location.protocol !== "http:" && window.location.protocol !== "https:") {{
        return false;
      }}

      try {{
        const resposta = await window.fetch(dashboardDataUrl, {{
          method: "GET",
          mode: "cors",
          headers: {{
            "Accept": "application/json",
          }},
        }});
        if (!resposta.ok) return false;
        const payload = await resposta.json().catch(() => null);
        if (!payload || payload.ok === false) return false;
        aplicarPayloadDashboard(payload);
        return true;
      }} catch (_erro) {{
        return false;
      }}
    }}

    function normalizarChaveUsuario(valor) {{
      const base = normalizarTexto(valor)
        .normalize("NFD")
        .replace(/[̀-ͯ]/g, "")
        .toLowerCase()
        .replace(/[^a-z0-9]/g, "");
      return aliasesUsuarios[base] || base;
    }}

    function usuariosSaoEquivalentes(a, b) {{
      const chaveA = normalizarChaveUsuario(a);
      const chaveB = normalizarChaveUsuario(b);
      return Boolean(chaveA) && chaveA === chaveB;
    }}

    function formatarNomeUsuarioExibicao(valor) {{
      const texto = normalizarTexto(valor);
      const chave = normalizarChaveUsuario(texto);
      if (!texto) return "";
      if (chave && rotulosCanonicosUsuarios[chave]) {{
        return rotulosCanonicosUsuarios[chave];
      }}
      if (texto === texto.toLowerCase()) {{
        return texto
          .split(" ")
          .filter(Boolean)
          .map((parte) => parte.charAt(0).toUpperCase() + parte.slice(1))
          .join(" ");
      }}
      return texto;
    }}

    function obterAno(registro) {{
      const data = normalizarTexto(registro.data_base_dashboard || registro.data_finalizacao_dashboard || registro.data_criacao_dashboard);
      if (!data) return "";
      return data.slice(0, 4);
    }}

    function obterMes(registro) {{
      return normalizarTexto(registro.mes_nome);
    }}

    function obterUsuario(registro) {{
      return normalizarTexto(registro.finalizado_por_dashboard);
    }}

    function obterPop(registro) {{
      return normalizarTexto(registro.pop);
    }}

	    function obterGrupo(registro) {{
	      const statusContrato = normalizarTexto(registro.contrato_status_dashboard);
	      if (statusContrato.localeCompare("Inviabilidade Técnica", "pt-BR", {{ sensitivity: "accent" }}) === 0) {{
	        return "Inviabilidade";
	      }}
	      return normalizarTexto(registro.grupo_dashboard);
	    }}

	    function obterGrupoEncerramento(registro) {{
	      return normalizarTexto(registro.grupo_encerramento_dashboard);
	    }}

	    function obterGrupoFiltro(registro) {{
	      const grupoStatusContrato = obterGrupo(registro);
	      if (grupoStatusContrato === "Inviabilidade") {{
	        return "Inviabilidade";
	      }}

	      if (ehStatusEncerrada(registro)) {{
	        const grupoEncerramento = obterGrupoEncerramento(registro);
	        if (grupoEncerramento) return grupoEncerramento;
	      }}

	      const responsavel = normalizarTexto(registro.responsavel).toLowerCase();
	      const auxiliares = obterTecnicosAuxiliares(registro).map((valor) => valor.toLowerCase());
	      if (responsavel.includes("infra") || auxiliares.some((valor) => valor.includes("infra"))) {{
	        return "Infra";
	      }}
	      if (responsavel || auxiliares.length) {{
	        return "Técnicos";
	      }}

	      return grupoStatusContrato;
	    }}

    function obterStatus(registro) {{
      return normalizarTexto(registro.status_dashboard || registro.status);
    }}

    function obterMotivo(registro) {{
      return normalizarTexto(registro.motivo);
    }}

    function motivoDeveSerExibido(motivo) {{
      return Boolean(motivo) && !/^\\d/.test(motivo);
    }}

	    function obterTecnicosAuxiliares(registro) {{
	      const bruto = normalizarTexto(registro.tecnicos_auxiliares);
	      if (!bruto || bruto === "[]") return [];

	      const matches = [...bruto.matchAll(/'([^']+)'|"([^"]+)"/g)];
	      if (matches.length) {{
	        return matches
	          .map((match) => normalizarTexto(match[1] || match[2] || ""))
	          .filter(Boolean);
	      }}

	      return [bruto]
	        .map((valor) => valor.replace(/^\\[|\\]$/g, ""))
	        .map((valor) => normalizarTexto(valor))
	        .filter(Boolean);
	    }}

	    function usuarioNaEquipeResponsavel(registro, usuario) {{
	      const usuarioNorm = normalizarTexto(usuario);
	      if (!usuarioNorm) return false;

	      const responsavel = normalizarTexto(registro.responsavel);
	      if (usuariosSaoEquivalentes(responsavel, usuarioNorm)) {{
	        return true;
	      }}

	      return obterTecnicosAuxiliares(registro).some((auxiliar) =>
	        usuariosSaoEquivalentes(auxiliar, usuarioNorm)
	      );
	    }}

	    function obterMesNumero(registro) {{
	      return Number(registro.mes_num || 0);
	    }}

	    function obterDiaNumero(registro) {{
	      const data = normalizarTexto(registro.data_base_dashboard || registro.data_finalizacao_dashboard || registro.data_criacao_dashboard);
	      if (!data || data.length < 10) return 0;
	      return Number(data.slice(8, 10));
	    }}

	    function obterDataBase(registro) {{
	      const valor = normalizarTexto(registro.data_base_dashboard || registro.data_finalizacao_dashboard || registro.data_criacao_dashboard);
	      if (!valor) return null;
	      const data = new Date(`${{valor}}T00:00:00`);
	      return Number.isNaN(data.getTime()) ? null : data;
	    }}

    function obterDataBaseTexto(registro) {{
      return normalizarTexto(registro.data_base_dashboard || registro.data_finalizacao_dashboard || registro.data_criacao_dashboard);
    }}

    function obterDataFiltroTexto(registro) {{
      if (ehStatusEncerrada(registro)) {{
        return obterDataBaseTexto(registro);
      }}
      return dataSnapshotAtual;
    }}

    function obterDataVotoTexto(registro) {{
      return normalizarTexto(registro.data_voto_dashboard || "");
    }}

    function obterUsuarioVoto(registro) {{
      return normalizarTexto(registro.tecnico);
    }}

    function obterUsuarioVotoConsolidado(registro) {{
      return normalizarTexto(registro.responsavel_dupla_dashboard || registro.tecnico);
    }}

    function obterHoraVotoTexto(registro) {{
      return normalizarTexto(registro.hora);
    }}

	    function obterDataCriacao(registro) {{
	      const valor = normalizarTexto(registro.data_criacao_dashboard);
	      if (!valor) return null;
	      const data = new Date(`${{valor}}T00:00:00`);
	      return Number.isNaN(data.getTime()) ? null : data;
	    }}

	    function obterDataFinalizacao(registro) {{
	      const valor = normalizarTexto(registro.data_finalizacao_dashboard);
	      if (!valor) return null;
	      const data = new Date(`${{valor}}T00:00:00`);
	      return Number.isNaN(data.getTime()) ? null : data;
	    }}

    function obterTextoBusca(registro) {{
      return detalheCols
        .map((coluna) => normalizarTexto(registro[coluna]).toLowerCase())
        .join(" ");
    }}

    function obterTextoBuscaVoto(registro) {{
      return [
        ...votosCols.map((coluna) => normalizarTexto(registro[coluna]).toLowerCase()),
        normalizarTexto(registro.papel_dupla_dashboard).toLowerCase(),
        normalizarTexto(registro.responsavel_dupla_dashboard).toLowerCase(),
      ]
        .filter(Boolean)
        .join(" ");
    }}

    function obterChaveDuplicidadeVoto(registro) {{
      const ip = normalizarTexto(registro.ip);
      const data = obterDataVotoTexto(registro);
      if (!ip || !data) return "";
      return `${{ip}}|||${{data}}`;
    }}

    function analisarDuplicidadeVotos(registros) {{
      const linhasOrdenadas = [...registros].sort((a, b) => {{
        const comparacaoData = obterDataVotoTexto(a).localeCompare(obterDataVotoTexto(b), "pt-BR", {{ sensitivity: "base" }});
        if (comparacaoData !== 0) return comparacaoData;
        const comparacaoHora = obterHoraVotoTexto(a).localeCompare(obterHoraVotoTexto(b), "pt-BR", {{ sensitivity: "base" }});
        if (comparacaoHora !== 0) return comparacaoHora;
        return obterUsuarioVoto(a).localeCompare(obterUsuarioVoto(b), "pt-BR", {{ sensitivity: "base" }});
      }});

      const contagemPorChave = new Map();
      linhasOrdenadas.forEach((registro) => {{
        const chave = obterChaveDuplicidadeVoto(registro);
        if (!chave) return;
        contagemPorChave.set(chave, (contagemPorChave.get(chave) || 0) + 1);
      }});

      const chavesVistas = new Set();
      const validos = linhasOrdenadas.filter((registro) => {{
        const chave = obterChaveDuplicidadeVoto(registro);
        if (!chave) return true;
        if (chavesVistas.has(chave)) return false;
        chavesVistas.add(chave);
        return true;
      }});

      const chavesDuplicadas = new Set(
        [...contagemPorChave.entries()]
          .filter(([, total]) => total > 1)
          .map(([chave]) => chave)
      );

      return {{
        validos,
        registrosValidos: new Set(validos),
        chavesDuplicadas,
      }};
    }}

    function deduplicarVotosPorIpEData(registros) {{
      return analisarDuplicidadeVotos(registros).validos;
    }}

    function formatarDataTitulo(data) {{
      if (!data || data.length < 10) return data;
      return `${{data.slice(8, 10)}}/${{data.slice(5, 7)}}/${{data.slice(0, 4)}}`;
    }}

    function obterLinkSgp(registro) {{
      const id = normalizarTexto(registro.id || registro.ordem_servico);
      if (!id) return "";
      return `${{sgpBaseUrl}}/admin/atendimento/ocorrencia/os/${{encodeURIComponent(id)}}/edit/`;
    }}

    function preencherSelect(select, valores, rotuloTodos) {{
      const valorAtual = select.value;
      select.innerHTML = "";

      const optTodos = document.createElement("option");
      optTodos.value = "";
      optTodos.textContent = rotuloTodos;
      select.appendChild(optTodos);

      valores.forEach((valor) => {{
        const opt = document.createElement("option");
        opt.value = valor;
        opt.textContent = valor;
        select.appendChild(opt);
      }});

      if (valores.includes(valorAtual)) {{
        select.value = valorAtual;
      }}
    }}

    function salvarFiltros() {{
      const estado = {{
        dataInicial: filtroDataInicial.value,
        dataFinal: filtroDataFinal.value,
        usuario: filtroUsuario.value,
        grupo: filtroGrupo.value,
        pop: filtroPop.value,
        busca: filtroBusca.value,
      }};
      window.localStorage.setItem(storageKey, JSON.stringify(estado));
    }}

    function restaurarFiltros() {{
      try {{
        const bruto = window.localStorage.getItem(storageKey);
        if (!bruto) return;
        const estado = JSON.parse(bruto);
        filtroDataInicial.value = estado.dataInicial || "";
        filtroDataFinal.value = estado.dataFinal || "";
        filtroUsuario.value = estado.usuario || "";
        filtroGrupo.value = estado.grupo || "";
        filtroPop.value = estado.pop || "";
        filtroBusca.value = estado.busca || "";
        normalizarPeriodoSelecionado();
      }} catch (_erro) {{
        window.localStorage.removeItem(storageKey);
      }}
    }}

    function limitarDataAoIntervalo(valor, fallback = "") {{
      const data = normalizarTexto(valor);
      if (!data) return fallback;
      if (dataMinDisponivel && data < dataMinDisponivel) return dataMinDisponivel;
      if (dataMaxDisponivel && data > dataMaxDisponivel) return dataMaxDisponivel;
      return data;
    }}

    function normalizarPeriodoSelecionado() {{
      const fallbackInicial = dataInicialPadrao || dataMinDisponivel || "";
      const fallbackFinal = dataFinalPadrao || dataMaxDisponivel || fallbackInicial;
      filtroDataInicial.value = limitarDataAoIntervalo(filtroDataInicial.value, fallbackInicial);
      filtroDataFinal.value = limitarDataAoIntervalo(filtroDataFinal.value, fallbackFinal);

      if (filtroDataInicial.value && filtroDataFinal.value && filtroDataInicial.value > filtroDataFinal.value) {{
        filtroDataFinal.value = filtroDataInicial.value;
      }}
    }}

    function popularFiltros() {{
      const usuarios = [...new Set(detalhes.map(obterUsuario).filter(Boolean))].sort((a, b) =>
        a.localeCompare(b, "pt-BR", {{ sensitivity: "base" }})
      );
      const grupos = [...new Set(detalhes.map(obterGrupoFiltro).filter(Boolean))].sort((a, b) =>
        a.localeCompare(b, "pt-BR", {{ sensitivity: "base" }})
      );
      const pops = [...new Set(detalhes.map(obterPop).filter(Boolean))].sort((a, b) =>
        a.localeCompare(b, "pt-BR", {{ sensitivity: "base" }})
      );

      preencherSelect(filtroUsuario, usuarios, "Todos os usuários");
      preencherSelect(filtroGrupo, grupos, "Todos os grupos");
      preencherSelect(filtroPop, pops, "Todos os POPs");
      if (dataMinDisponivel) {{
        filtroDataInicial.min = dataMinDisponivel;
        filtroDataFinal.min = dataMinDisponivel;
      }}
      if (dataMaxDisponivel) {{
        filtroDataInicial.max = dataMaxDisponivel;
        filtroDataFinal.max = dataMaxDisponivel;
      }}

      if (!filtroDataInicial.value) {{
        filtroDataInicial.value = dataInicialPadrao || dataMinDisponivel || "";
      }}
      if (!filtroDataFinal.value) {{
        filtroDataFinal.value = dataFinalPadrao || dataMaxDisponivel || "";
      }}

      normalizarPeriodoSelecionado();
    }}

    function dataDentroDoIntervalo(registro) {{
      const data = obterDataFiltroTexto(registro);
      if (!data) return false;
      if (filtroDataInicial.value && data < filtroDataInicial.value) return false;
      if (filtroDataFinal.value && data > filtroDataFinal.value) return false;
      return true;
    }}

    function usuarioCorrespondeAoFiltro(registro, usuarioFiltro) {{
      const usuario = normalizarTexto(usuarioFiltro);
      if (!usuario) return true;
      if (ehStatusEncerrada(registro)) {{
        return usuariosSaoEquivalentes(obterUsuario(registro), usuario);
      }}
      return usuarioNaEquipeResponsavel(registro, usuario);
    }}

    function filtrarDetalhes() {{
      const busca = normalizarTexto(filtroBusca.value).toLowerCase();

      return detalhes.filter((registro) => {{
        if (!dataDentroDoIntervalo(registro)) return false;
        if (!usuarioCorrespondeAoFiltro(registro, filtroUsuario.value)) return false;
        if (filtroGrupo.value && obterGrupoFiltro(registro) !== filtroGrupo.value) return false;
        if (filtroPop.value && obterPop(registro) !== filtroPop.value) return false;
        if (busca && !obterTextoBusca(registro).includes(busca)) return false;
        return true;
      }});
    }}

    function filtrarBaseRanking() {{
      const busca = normalizarTexto(filtroBusca.value).toLowerCase();

      return detalhes.filter((registro) => {{
        if (!dataDentroDoIntervalo(registro)) return false;
        if (!usuarioCorrespondeAoFiltro(registro, filtroUsuario.value)) return false;
        if (filtroGrupo.value && obterGrupoFiltro(registro) !== filtroGrupo.value) return false;
        if (filtroPop.value && obterPop(registro) !== filtroPop.value) return false;
        if (busca && !obterTextoBusca(registro).includes(busca)) return false;
        return true;
      }});
    }}

    function filtrarBaseRankingComparativo() {{
      const busca = normalizarTexto(filtroBusca.value).toLowerCase();

      return detalhes.filter((registro) => {{
        if (!usuarioCorrespondeAoFiltro(registro, filtroUsuario.value)) return false;
        if (filtroGrupo.value && obterGrupoFiltro(registro) !== filtroGrupo.value) return false;
        if (filtroPop.value && obterPop(registro) !== filtroPop.value) return false;
        if (busca && !obterTextoBusca(registro).includes(busca)) return false;
        return true;
      }});
    }}

    function obterUsuariosPermitidosParaVotos() {{
      const busca = normalizarTexto(filtroBusca.value).toLowerCase();
      const usuarios = new Set();

      detalhes.forEach((registro) => {{
        if (!dataDentroDoIntervalo(registro)) return;
        if (!usuarioCorrespondeAoFiltro(registro, filtroUsuario.value)) return false;
        if (filtroGrupo.value && obterGrupoFiltro(registro) !== filtroGrupo.value) return;
        if (filtroPop.value && obterPop(registro) !== filtroPop.value) return;
        if (busca && !obterTextoBusca(registro).includes(busca)) return;

        const usuario = obterUsuario(registro);
        const responsavel = normalizarTexto(registro.responsavel);
        if (usuario) usuarios.add(normalizarChaveUsuario(usuario));
        if (responsavel) usuarios.add(normalizarChaveUsuario(responsavel));
        obterTecnicosAuxiliares(registro).forEach((auxiliar) => {{
          usuarios.add(normalizarChaveUsuario(auxiliar));
        }});
      }});

      return usuarios;
    }}

    function construirMapaRotulosUsuarios(registros) {{
      const contagem = new Map();

      function registrar(nome) {{
        const rotulo = normalizarTexto(nome);
        const chave = normalizarChaveUsuario(rotulo);
        if (!rotulo || !chave) return;
        if (!contagem.has(chave)) {{
          contagem.set(chave, new Map());
        }}
        const mapaRotulos = contagem.get(chave);
        mapaRotulos.set(rotulo, (mapaRotulos.get(rotulo) || 0) + 1);
      }}

      registros.forEach((registro) => {{
        registrar(registro.responsavel);
        registrar(registro.finalizado_por_dashboard);
        obterTecnicosAuxiliares(registro).forEach(registrar);
      }});

      const rotulos = new Map();
      contagem.forEach((mapaRotulos, chave) => {{
        const escolhido = [...mapaRotulos.entries()]
          .sort((a, b) => b[1] - a[1] || b[0].length - a[0].length || a[0].localeCompare(b[0], "pt-BR", {{ sensitivity: "base" }}))[0];
        if (escolhido) {{
          rotulos.set(chave, escolhido[0]);
        }}
      }});
      return rotulos;
    }}

    function normalizarRotuloUsuario(valor, mapaRotulos) {{
      const texto = normalizarTexto(valor);
      const chave = normalizarChaveUsuario(texto);
      if (!chave) return texto;
      return formatarNomeUsuarioExibicao(mapaRotulos?.get(chave) || texto);
    }}

    function construirMapaDuplasPorDia() {{
      const mapaAuxiliar = new Map();
      const mapaResponsavel = new Map();
      const mapaAuxiliaresPorResponsavel = new Map();
      const registros = filtrarDetalhes();
      const mapaRotulos = construirMapaRotulosUsuarios(registros);

      registros.forEach((registro) => {{
        const data = obterDataBaseTexto(registro);
        const responsavel = normalizarRotuloUsuario(registro.responsavel, mapaRotulos);
        if (!data || !responsavel) return;

        mapaResponsavel.set(`${{data}}|||${{normalizarChaveUsuario(responsavel)}}`, responsavel);
        const chaveResponsavelDia = `${{data}}|||${{normalizarChaveUsuario(responsavel)}}`;
        if (!mapaAuxiliaresPorResponsavel.has(chaveResponsavelDia)) {{
          mapaAuxiliaresPorResponsavel.set(chaveResponsavelDia, new Set());
        }}
        obterTecnicosAuxiliares(registro).forEach((auxiliar) => {{
          const auxiliarNormalizado = normalizarRotuloUsuario(auxiliar, mapaRotulos);
          const chave = `${{data}}|||${{normalizarChaveUsuario(auxiliarNormalizado)}}`;
          mapaAuxiliaresPorResponsavel.get(chaveResponsavelDia).add(auxiliarNormalizado);
          const atual = mapaAuxiliar.get(chave);
          if (atual) {{
            atual.total += 1;
            return;
          }}
          mapaAuxiliar.set(chave, {{
            auxiliar: auxiliarNormalizado,
            responsavel,
            total: 1,
          }});
        }});
      }});

      return {{
        mapaAuxiliar,
        mapaResponsavel,
        mapaAuxiliaresPorResponsavel,
        mapaRotulos,
      }};
    }}

    function enriquecerVotoComDupla(registro, mapaDuplas) {{
      const voto = {{ ...registro }};
      const data = obterDataVotoTexto(voto);
      const tecnico = normalizarRotuloUsuario(obterUsuarioVoto(voto), mapaDuplas.mapaRotulos);
      const chaveTecnico = normalizarChaveUsuario(tecnico);
      const mapeamentoAuxiliar = mapaDuplas.mapaAuxiliar.get(`${{data}}|||${{chaveTecnico}}`);
      const responsavelNoDia = mapaDuplas.mapaResponsavel.get(`${{data}}|||${{chaveTecnico}}`);

      voto.tecnico = tecnico;
      voto.auxiliares_dupla_dashboard = "";
      voto.papel_dupla_dashboard = "";
      voto.responsavel_dupla_dashboard = tecnico;

      if (mapeamentoAuxiliar && mapeamentoAuxiliar.responsavel) {{
        voto.papel_dupla_dashboard = "Auxiliar";
        voto.responsavel_dupla_dashboard = mapeamentoAuxiliar.responsavel;
      }} else if (responsavelNoDia) {{
        voto.papel_dupla_dashboard = "Responsável";
        voto.responsavel_dupla_dashboard = responsavelNoDia;
      }}

      const chaveResponsavelDia = `${{data}}|||${{normalizarChaveUsuario(voto.responsavel_dupla_dashboard)}}`;
      const auxiliares = [...(mapaDuplas.mapaAuxiliaresPorResponsavel.get(chaveResponsavelDia) || [])]
        .sort((a, b) => a.localeCompare(b, "pt-BR", {{ sensitivity: "base" }}));
      voto.auxiliares_dupla_dashboard = auxiliares.join(", ");

      return voto;
    }}

    function filtrarVotosPorData() {{
      const busca = normalizarTexto(filtroBusca.value).toLowerCase();
      const usuarioFiltro = normalizarTexto(filtroUsuario.value);
      const usuariosPermitidos = obterUsuariosPermitidosParaVotos();
      const restringirPorDetalhes = Boolean(filtroUsuario.value || filtroGrupo.value || filtroPop.value || busca);
      const mapaDuplas = construirMapaDuplasPorDia();

      return votosData.flatMap((registro) => {{
        const data = obterDataVotoTexto(registro);
        if (!data) return [];
        if (filtroDataInicial.value && data < filtroDataInicial.value) return [];
        if (filtroDataFinal.value && data > filtroDataFinal.value) return [];

        const voto = enriquecerVotoComDupla(registro, mapaDuplas);
        const tecnico = obterUsuarioVoto(voto);
        const tecnicoConsolidado = obterUsuarioVotoConsolidado(voto);
        if (usuarioFiltro && !usuariosSaoEquivalentes(tecnico, usuarioFiltro) && !usuariosSaoEquivalentes(tecnicoConsolidado, usuarioFiltro)) return [];
        if (busca && !obterTextoBuscaVoto(voto).includes(busca)) return [];
        if (restringirPorDetalhes) {{
          if (!tecnico) return [];
          if (!usuariosPermitidos.has(normalizarChaveUsuario(tecnico)) && !usuariosPermitidos.has(normalizarChaveUsuario(tecnicoConsolidado))) return [];
        }}

        return [voto];
      }});
    }}

    function filtrarBaseReincidencias() {{
      const busca = normalizarTexto(filtroBusca.value).toLowerCase();

      return detalhes.filter((registro) => {{
        if (!usuarioCorrespondeAoFiltro(registro, filtroUsuario.value)) return false;
        if (filtroGrupo.value && obterGrupoFiltro(registro) !== filtroGrupo.value) return false;
        if (filtroPop.value && obterPop(registro) !== filtroPop.value) return false;
        if (busca && !obterTextoBusca(registro).includes(busca)) return false;
        return true;
      }});
    }}

    function filtrarDetalhamentoPops(registros) {{
      return registros;
    }}

	    function filtrarBaseEncerramentos() {{
	      const busca = normalizarTexto(filtroBusca.value).toLowerCase();

	      return detalhes.filter((registro) => {{
	        if (!dataDentroDoIntervalo(registro)) return false;
	        if (!usuarioCorrespondeAoFiltro(registro, filtroUsuario.value)) return false;
	        if (filtroGrupo.value && obterGrupoFiltro(registro) !== filtroGrupo.value) return false;
	        if (filtroPop.value && obterPop(registro) !== filtroPop.value) return false;
	        if (busca && !obterTextoBusca(registro).includes(busca)) return false;
	        return true;
	      }});
	    }}

    function ehStatusEncerrada(registro) {{
      return obterStatus(registro) === "Encerrada";
    }}

	    function calcularCardsEncerramentos(registros) {{
	      let totalOs = 0;
	      let peloTecnico = 0;
	      let porOutros = 0;

	      registros.forEach((registro) => {{
	        totalOs += 1;

	        if (obterGrupoEncerramento(registro) === "Técnicos") {{
	          peloTecnico += 1;
	        }} else {{
	          porOutros += 1;
	        }}
	      }});

      return {{
        totalOs,
        peloTecnico,
        porOutros,
      }};
    }}

    function renderStatusCards(registros) {{
      let aberta = 0;
      let pendente = 0;
      let emExecucao = 0;

      registros.forEach((registro) => {{
        const status = obterStatus(registro);
        if (status === "Aberta") aberta += 1;
        else if (status === "Pendente") pendente += 1;
        else if (status === "Em execução") emExecucao += 1;
      }});

      document.getElementById("cardTotalStatus").textContent = registros.length;
      document.getElementById("cardAberta").textContent = aberta;
      document.getElementById("cardPendente").textContent = pendente;
      document.getElementById("cardEmExecucao").textContent = emExecucao;
    }}

	    function renderMotivoCards(registros) {{
	      const contagem = new Map();
	      let inviabilidade = 0;

	      registros.forEach((registro) => {{
	        if (obterGrupo(registro) === "Inviabilidade") {{
	          inviabilidade += 1;
	          return;
	        }}
	        const motivo = obterMotivo(registro);
	        if (!motivoDeveSerExibido(motivo)) return;
	        contagem.set(motivo, (contagem.get(motivo) || 0) + 1);
	      }});

	      const itens = [...contagem.entries()]
	        .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "pt-BR", {{ sensitivity: "base" }}));

	      movimentacoesGrid.innerHTML = "";
	      if (inviabilidade > 0) {{
	        const cardInviabilidade = document.createElement("div");
	        cardInviabilidade.className = "metric-item compact";
	        cardInviabilidade.innerHTML = `<span class="metric-label">Inviabilidades</span><span class="metric-value">${{inviabilidade}}</span>`;
	        movimentacoesGrid.appendChild(cardInviabilidade);
	      }}

	      if (!itens.length && inviabilidade === 0) {{
	        movimentacoesGrid.innerHTML = '<div class="metric-item compact"><span class="metric-label">Sem motivos no recorte</span><span class="metric-value">0</span></div>';
	        return;
	      }}

	      itens.forEach(([motivo, total]) => {{
	        const item = document.createElement("div");
	        item.className = "metric-item compact";

	        const label = document.createElement("span");
	        label.className = "metric-label";
	        label.textContent = motivo;

	        const valor = document.createElement("span");
	        valor.className = "metric-value";
	        valor.textContent = String(total);

	        item.appendChild(label);
	        item.appendChild(valor);
	        movimentacoesGrid.appendChild(item);
	      }});
	    }}

	    function renderPopCards(registros) {{
	      const contagem = new Map();

	      registros.forEach((registro) => {{
	        const pop = obterPop(registro);
	        if (!pop) return;
	        contagem.set(pop, (contagem.get(pop) || 0) + 1);
	      }});

	      const itens = [...contagem.entries()]
	        .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "pt-BR", {{ sensitivity: "base" }}));

	      popsGrid.innerHTML = "";

	      if (!itens.length) {{
	        popsGrid.innerHTML = '<div class="metric-item compact"><span class="metric-label">Sem POPs no recorte</span><span class="metric-value">0</span></div>';
	        return;
	      }}

	      itens.forEach(([pop, total]) => {{
	        const item = document.createElement("div");
	        item.className = "metric-item compact";

	        const label = document.createElement("span");
	        label.className = "metric-label";
	        label.textContent = pop;

	        const valor = document.createElement("span");
	        valor.className = "metric-value";
	        valor.textContent = String(total);

	        item.appendChild(label);
	        item.appendChild(valor);
	        popsGrid.appendChild(item);
	      }});
	    }}

    function renderDetalhamentoPops(registros) {{
      detalhamentoPopsBody.innerHTML = "";

      if (!registros.length) {{
        detalhamentoPopsBody.innerHTML = '<tr><td colspan="9" class="empty">Nenhuma O.S. encontrada para os filtros atuais.</td></tr>';
        return;
      }}

      const linhas = [...registros].sort((a, b) => {{
        const dataA = obterDataBaseTexto(a);
        const dataB = obterDataBaseTexto(b);
        const comparacaoData = dataB.localeCompare(dataA, "pt-BR", {{ sensitivity: "base" }});
        if (comparacaoData !== 0) return comparacaoData;
        return obterPop(a).localeCompare(obterPop(b), "pt-BR", {{ sensitivity: "base" }});
      }});

      linhas.forEach((registro) => {{
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${{normalizarTexto(obterDataBaseTexto(registro))}}</td>
          <td>${{obterPop(registro)}}</td>
          <td>${{normalizarTexto(registro.id || registro.ordem_servico)}}</td>
          <td>${{normalizarTexto(registro.cliente)}}</td>
          <td>${{normalizarTexto(registro.contrato)}}</td>
          <td>${{obterStatus(registro)}}</td>
          <td>${{obterMotivo(registro)}}</td>
          <td>${{normalizarTexto(registro.responsavel)}}</td>
          <td>${{obterTecnicosAuxiliares(registro).join(", ")}}</td>
        `;
        detalhamentoPopsBody.appendChild(tr);
      }});
    }}

    function renderCardsEncerramentos(registros) {{
      const cards = calcularCardsEncerramentos(registros);
      document.getElementById("cardEncerrada").textContent = cards.totalOs;
      document.getElementById("cardEncerradaTecnicos").textContent = cards.peloTecnico;
      document.getElementById("cardPorOutros").textContent = cards.porOutros;
    }}

    function agruparResumo(registros) {{
      return mesesOrdem.map((mes) => {{
        const itens = registros.filter((registro) => obterMes(registro) === mes);
        return {{
          mes_nome: mes,
          finalizadas: itens.length,
          tecnicos: itens.filter((registro) => obterGrupoEncerramento(registro) === "Técnicos").length,
          infra: itens.filter((registro) => obterGrupoEncerramento(registro) === "Infra").length,
          inviabilidade: itens.filter((registro) => obterGrupo(registro) === "Inviabilidade").length,
          outros: itens.filter((registro) => obterGrupoEncerramento(registro) === "Outros").length,
        }};
      }});
    }}

	    function formatarDuracaoDias(mediaDias) {{
	      if (mediaDias === null || Number.isNaN(mediaDias)) return "-";
	      return `${{mediaDias.toFixed(1)}} dia(s)`;
	    }}

	    function renderTempoBacklog(registros, registrosFinalizados) {{
	      tempoBacklogBody.innerHTML = "";

	      const backlogAberta = registros.filter((registro) => obterStatus(registro) === "Aberta").length;
	      const backlogPendente = registros.filter((registro) => obterStatus(registro) === "Pendente").length;
	      const backlogExecucao = registros.filter((registro) => obterStatus(registro) === "Em execução").length;
	      const backlogTotal = backlogAberta + backlogPendente + backlogExecucao;

	      const duracoes = registrosFinalizados
	        .map((registro) => {{
	          const criacao = obterDataCriacao(registro);
	          const finalizacao = obterDataFinalizacao(registro);
	          if (!criacao || !finalizacao) return null;
	          return (finalizacao.getTime() - criacao.getTime()) / 86400000;
	        }})
	        .filter((valor) => valor !== null && valor >= 0);

	      const mediaTotal = duracoes.length
	        ? duracoes.reduce((acc, valor) => acc + valor, 0) / duracoes.length
	        : null;

	      const mediaPorGrupo = (grupo) => {{
	        const valores = registrosFinalizados
	          .filter((registro) => obterGrupoEncerramento(registro) === grupo)
	          .map((registro) => {{
	            const criacao = obterDataCriacao(registro);
	            const finalizacao = obterDataFinalizacao(registro);
	            if (!criacao || !finalizacao) return null;
	            return (finalizacao.getTime() - criacao.getTime()) / 86400000;
	          }})
	          .filter((valor) => valor !== null && valor >= 0);

	        return valores.length
	          ? valores.reduce((acc, valor) => acc + valor, 0) / valores.length
	          : null;
	      }};

	      const linhas = [
	        ["Backlog total", String(backlogTotal)],
	        ["Em aberto", String(backlogAberta)],
	        ["Pendentes", String(backlogPendente)],
	        ["Em execução", String(backlogExecucao)],
	        ["Tempo médio até encerramento", formatarDuracaoDias(mediaTotal)],
	        ["Tempo médio dos técnicos", formatarDuracaoDias(mediaPorGrupo("Técnicos"))],
	        ["Tempo médio da infra", formatarDuracaoDias(mediaPorGrupo("Infra"))],
	        ["Tempo médio de outros", formatarDuracaoDias(mediaPorGrupo("Outros"))],
	      ];

	      linhas.forEach(([indicador, valor]) => {{
	        const tr = document.createElement("tr");
	        tr.innerHTML = `
	          <td><b>${{indicador}}</b></td>
	          <td>${{valor}}</td>
	        `;
	        tempoBacklogBody.appendChild(tr);
	      }});

	    }}

    function agruparRanking(registros) {{
      const mapa = new Map();

      registros.forEach((registro) => {{
        const usuario = obterUsuario(registro) || "Sem usuário";
        const grupo = obterGrupoFiltro(registro) || "Outros";
        const chave = `${{usuario}}|||${{grupo}}`;
        mapa.set(chave, (mapa.get(chave) || 0) + 1);
      }});

      return [...mapa.entries()]
        .map(([chave, total]) => {{
          const [usuario, grupo] = chave.split("|||");
          return {{
            usuario,
            grupo,
            total,
          }};
        }})
        .sort((a, b) => b.total - a.total || a.usuario.localeCompare(b.usuario, "pt-BR", {{ sensitivity: "base" }}));
    }}

    function deslocarMes(dataTexto, quantidadeMeses) {{
      if (!dataTexto) return "";
      const [ano, mes, dia] = dataTexto.split("-").map(Number);
      const destino = new Date(ano, mes - 1 + quantidadeMeses, 1);
      const ultimoDia = new Date(destino.getFullYear(), destino.getMonth() + 1, 0).getDate();
      const diaAjustado = Math.min(dia, ultimoDia);
      return `${{destino.getFullYear()}}-${{String(destino.getMonth() + 1).padStart(2, "0")}}-${{String(diaAjustado).padStart(2, "0")}}`;
    }}

    function obterIntervaloComparativoAnterior() {{
      const intervaloAtual = obterIntervaloSelecionado();
      if (!intervaloAtual) return null;
      return {{
        inicio: deslocarMes(intervaloAtual.inicio, -1),
        fim: deslocarMes(intervaloAtual.fim, -1),
      }};
    }}

    function dataDentroDoIntervaloPersonalizado(registro, intervalo) {{
      if (!intervalo) return false;
      const data = obterDataBaseTexto(registro);
      if (!data) return false;
      if (intervalo.inicio && data < intervalo.inicio) return false;
      if (intervalo.fim && data > intervalo.fim) return false;
      return true;
    }}

    function calcularVariacaoRanking(registrosAtuais, registrosBase, usuario, grupo) {{
      const intervaloAnterior = obterIntervaloComparativoAnterior();
      if (!intervaloAnterior) {{
        return {{ texto: "-", classe: "flat" }};
      }}

      const atual = registrosBase.filter((registro) =>
        obterUsuario(registro) === usuario &&
        obterGrupoFiltro(registro) === grupo &&
        dataDentroDoIntervalo(registro)
      ).length;

      const anterior = registrosBase.filter((registro) =>
        obterUsuario(registro) === usuario &&
        obterGrupoFiltro(registro) === grupo &&
        dataDentroDoIntervaloPersonalizado(registro, intervaloAnterior)
      ).length;

      if (anterior === 0 && atual === 0) {{
        return {{ texto: "-", classe: "flat" }};
      }}

      if (anterior === 0) {{
        return {{ texto: "↑ novo", classe: "up" }};
      }}

      const percentual = ((atual - anterior) / anterior) * 100;
      if (percentual > 0.01) {{
        return {{ texto: `↑ ${{percentual.toFixed(1)}}%`, classe: "up" }};
      }}
      if (percentual < -0.01) {{
        return {{ texto: `↓ ${{Math.abs(percentual).toFixed(1)}}%`, classe: "down" }};
      }}
      return {{ texto: "→ 0.0%", classe: "flat" }};
    }}

    function renderRanking(registros, registrosBaseRanking) {{
      const linhas = agruparRanking(registros);
      rankingBody.innerHTML = "";

      if (!linhas.length) {{
        rankingBody.innerHTML = '<tr><td colspan="4" class="empty">Nenhum usuário encontrado.</td></tr>';
        return;
      }}

      linhas.forEach((linha) => {{
        const variacao = calcularVariacaoRanking(registros, registrosBaseRanking, linha.usuario, linha.grupo);
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${{linha.usuario || linha["Finalizado Por"] || ""}}</td>
          <td>${{linha.grupo || linha["Grupo"] || ""}}</td>
          <td>${{linha.total || linha["Total"] || 0}}</td>
          <td><span class="variation ${{variacao.classe}}">${{variacao.texto}}</span></td>
        `;
        rankingBody.appendChild(tr);
      }});
    }}

    function agruparRankingVotacao(registros) {{
      const mapa = new Map();

      registros.forEach((registro) => {{
        const tecnico = obterUsuarioVotoConsolidado(registro) || "Sem técnico";
        mapa.set(tecnico, (mapa.get(tecnico) || 0) + 1);
      }});

      return [...mapa.entries()]
        .map(([tecnico, total]) => ({{
          tecnico,
          total,
        }}))
        .sort((a, b) => b.total - a.total || a.tecnico.localeCompare(b.tecnico, "pt-BR", {{ sensitivity: "base" }}));
    }}

    function renderRankingVotosResumo(registros) {{
      rankingVotosResumoBody.innerHTML = "";
      const linhas = agruparRankingVotacao(deduplicarVotosPorIpEData(registros));

      if (!linhas.length) {{
        rankingVotosResumoBody.innerHTML = '<tr><td colspan="2" class="empty">Nenhum voto encontrado para o recorte atual.</td></tr>';
        return;
      }}

      linhas.forEach((linha) => {{
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${{linha.tecnico}}</td>
          <td>${{linha.total}}</td>
        `;
        rankingVotosResumoBody.appendChild(tr);
      }});
    }}

    function obterResumoFiltrosTitulo() {{
      const partes = [];
      const inicio = formatarDataTitulo(filtroDataInicial.value || dataInicialPadrao || "");
      const fim = formatarDataTitulo(filtroDataFinal.value || dataFinalPadrao || "");
      if (inicio && fim) partes.push(`${{inicio}} a ${{fim}}`);
      else if (inicio) partes.push(`a partir de ${{inicio}}`);
      else if (fim) partes.push(`até ${{fim}}`);
      if (filtroUsuario.value) partes.push(`Usuário: ${{filtroUsuario.value}}`);
      if (filtroGrupo.value) partes.push(`Grupo: ${{filtroGrupo.value}}`);
      if (filtroPop.value) partes.push(`POP: ${{filtroPop.value}}`);
      if (filtroBusca.value.trim()) partes.push(`Busca: ${{filtroBusca.value.trim()}}`);
      return partes.length ? partes.join(" | ") : "Todos os filtros";
    }}

    function atualizarTitulosPaineis() {{
      const resumo = obterResumoFiltrosTitulo();
      tituloEncerramentos.textContent = `Encerramentos | ${{resumo}}`;
      tituloStatusOperacional.textContent = `Status Operacional | ${{resumo}}`;
      tituloMovimentacoes.textContent = `Movimentações | ${{resumo}}`;
      tituloPops.textContent = `POPs | ${{resumo}}`;
      tituloDetalhamentoPops.textContent = `Detalhamento por POP | ${{resumo}}`;
      tituloTempoBacklog.textContent = `Tempo médio e backlog | ${{resumo}}`;
      tituloRanking.textContent = `Ranking por finalizador | ${{resumo}}`;
      tituloRankingVotosResumo.textContent = `Ranking de votação | ${{resumo}}`;
      tituloRankingVotos.textContent = `Detalhamento dos votos | ${{resumo}}`;
      tituloGraficoMensal.textContent = `Gráfico mensal | ${{resumo}}`;
      tituloGraficoDiario.textContent = `Evolução diária dos grupos | ${{resumo}}`;
      tituloDetalhamento.textContent = `Detalhamento | ${{resumo}}`;
      tituloReincidencia.textContent = `Reincidência por cliente/contrato | ${{resumo}}`;
    }}

    function obterValorOrdenacao(registro, coluna) {{
      if (coluna === "grupo_dashboard") return obterGrupo(registro);
      if (coluna === "data_finalizacao_dashboard") return normalizarTexto(registro.data_finalizacao_dashboard || "");
      if (coluna === "finalizado_por_dashboard") return obterUsuario(registro);
      return normalizarTexto(registro[coluna]);
    }}

    function obterValorOrdenacaoVoto(registro, coluna) {{
      if (coluna === "data") return obterDataVotoTexto(registro);
      if (coluna === "responsavel_dupla_dashboard") return obterUsuarioVotoConsolidado(registro);
      return normalizarTexto(registro[coluna]);
    }}

    function compararRegistrosPorColuna(a, b, coluna) {{
      const valorA = obterValorOrdenacao(a, coluna);
      const valorB = obterValorOrdenacao(b, coluna);
      return compararRegistrosPorColunaGenerica(valorA, valorB);
    }}

    function compararRegistrosPorColunaGenerica(valorA, valorB) {{
      const numeroA = Number(valorA);
      const numeroB = Number(valorB);

      if (valorA && valorB && !Number.isNaN(numeroA) && !Number.isNaN(numeroB)) {{
        return numeroA - numeroB;
      }}

      return valorA.localeCompare(valorB, "pt-BR", {{ sensitivity: "base" }});
    }}

    function atualizarIndicadoresOrdenacao() {{
      detalhesHead.querySelectorAll(".sort-header").forEach((botao) => {{
        const ativo = botao.dataset.col === ordenacaoDetalhes.col;
        const indicador = botao.querySelector(".sort-indicator");
        const cabecalho = botao.closest("th");
        if (!indicador || !cabecalho) return;
        indicador.textContent = ativo ? (ordenacaoDetalhes.dir === "asc" ? "▲" : "▼") : "△";
        cabecalho.setAttribute("aria-sort", ativo ? (ordenacaoDetalhes.dir === "asc" ? "ascending" : "descending") : "none");
      }});

      rankingVotosHead.querySelectorAll(".sort-header").forEach((botao) => {{
        const ativo = botao.dataset.col === ordenacaoRankingVotos.col;
        const indicador = botao.querySelector(".sort-indicator");
        const cabecalho = botao.closest("th");
        if (!indicador || !cabecalho) return;
        indicador.textContent = ativo ? (ordenacaoRankingVotos.dir === "asc" ? "▲" : "▼") : "△";
        cabecalho.setAttribute("aria-sort", ativo ? (ordenacaoRankingVotos.dir === "asc" ? "ascending" : "descending") : "none");
      }});

      reincidenciasHead.querySelectorAll(".sort-header").forEach((botao) => {{
        const ativo = botao.dataset.col === ordenacaoReincidencias.col;
        const indicador = botao.querySelector(".sort-indicator");
        const cabecalho = botao.closest("th");
        if (!indicador || !cabecalho) return;
        indicador.textContent = ativo ? (ordenacaoReincidencias.dir === "asc" ? "▲" : "▼") : "△";
        cabecalho.setAttribute("aria-sort", ativo ? (ordenacaoReincidencias.dir === "asc" ? "ascending" : "descending") : "none");
      }});
    }}

    function renderRankingVotos(registros) {{
      atualizarIndicadoresOrdenacao();
      rankingVotosBody.innerHTML = "";

      if (!votosDisplayCols.length) {{
        rankingVotosBody.innerHTML = '<tr><td class="empty">Nenhuma coluna disponível na base de votos.</td></tr>';
        return;
      }}

      if (!registros.length) {{
        rankingVotosBody.innerHTML = `<tr><td colspan="${len(votos_display_cols) if votos_display_cols else 1}" class="empty">Nenhum voto encontrado para o recorte atual.</td></tr>`;
        return;
      }}

      const analiseDuplicidade = analisarDuplicidadeVotos(registros);
      const linhas = [...registros].sort((a, b) => {{
        const comparacaoBase = compararRegistrosPorColunaGenerica(
          obterValorOrdenacaoVoto(a, ordenacaoRankingVotos.col),
          obterValorOrdenacaoVoto(b, ordenacaoRankingVotos.col),
        );
        return ordenacaoRankingVotos.dir === "asc" ? comparacaoBase : -comparacaoBase;
      }});

      linhas.forEach((registro) => {{
        const tr = document.createElement("tr");
        const possuiDuplicidadeIpData = analiseDuplicidade.chavesDuplicadas.has(obterChaveDuplicidadeVoto(registro));
        if (possuiDuplicidadeIpData) {{
          tr.classList.add("duplicate-vote-row");
        }}
        votosDisplayCols.forEach((coluna) => {{
          const td = document.createElement("td");
          const valor = coluna === "responsavel_dupla_dashboard"
            ? (analiseDuplicidade.registrosValidos.has(registro) ? obterUsuarioVotoConsolidado(registro) : "-")
            : normalizarTexto(registro[coluna]);
          td.textContent = valor;
          if ((coluna === "ip" || coluna === "data") && possuiDuplicidadeIpData) {{
            td.classList.add("duplicate-vote-cell");
          }}
          tr.appendChild(td);
        }});
        rankingVotosBody.appendChild(tr);
      }});
    }}

    function renderDetalhes(registros) {{
      atualizarIndicadoresOrdenacao();
      detalhesBody.innerHTML = "";

      if (!registros.length) {{
        detalhesBody.innerHTML = `<tr><td colspan="${len(detalhe_cols) if detalhe_cols else 1}" class="empty">Nenhum registro encontrado para os filtros atuais.</td></tr>`;
        return;
      }}

      const linhas = [...registros].sort((a, b) => {{
        const comparacaoBase = compararRegistrosPorColuna(a, b, ordenacaoDetalhes.col)
          || normalizarTexto(a.id || a.ordem_servico).localeCompare(normalizarTexto(b.id || b.ordem_servico), "pt-BR", {{ sensitivity: "base" }});
        return ordenacaoDetalhes.dir === "asc" ? comparacaoBase : -comparacaoBase;
      }});

      linhas.forEach((registro) => {{
        const tr = document.createElement("tr");
        const linkSgp = obterLinkSgp(registro);
        if (linkSgp) {{
          tr.classList.add("row-link");
          tr.title = "Abrir no SGP";
          tr.addEventListener("click", () => {{
            window.open(linkSgp, "_blank", "noopener,noreferrer");
          }});
        }}
        detalheCols.forEach((coluna) => {{
          const td = document.createElement("td");
          td.textContent = coluna === "grupo_dashboard"
            ? obterGrupo(registro)
            : normalizarTexto(registro[coluna]);
          tr.appendChild(td);
        }});
        detalhesBody.appendChild(tr);
      }});
    }}

    function obterIntervaloReincidencia30Dias() {{
      const intervaloSelecionado = obterIntervaloSelecionado();
      const fimTexto = intervaloSelecionado?.fim || dataFinalPadrao || dataMaxDisponivel || "";
      if (!fimTexto) return null;

      const fim = new Date(`${{fimTexto}}T00:00:00`);
      if (Number.isNaN(fim.getTime())) return null;

      const inicio = new Date(fim);
      inicio.setDate(inicio.getDate() - 29);

      return {{
        inicio: formatarDataInput(inicio),
        fim: formatarDataInput(fim),
      }};
    }}

    function obterChavesReincidentes(registros) {{
      const intervaloReincidencia = obterIntervaloReincidencia30Dias();
      const mapa = new Map();

      registros.forEach((registro) => {{
        const dataBase = obterDataBaseTexto(registro);
        if (!intervaloReincidencia || !dataBase) return;
        if (dataBase < intervaloReincidencia.inicio || dataBase > intervaloReincidencia.fim) return;

        const cliente = normalizarTexto(registro.cliente);
        const contrato = normalizarTexto(registro.contrato);
        if (!cliente && !contrato) return;

        const chave = `${{cliente}}|||${{contrato}}`;
        if (!mapa.has(chave)) {{
          mapa.set(chave, {{
            cliente,
            contrato,
            ids: [],
          }});
        }}

        const item = mapa.get(chave);
        const id = normalizarTexto(registro.id || registro.ordem_servico);
        if (id) item.ids.push(id);
      }});

      return new Set(
        [...mapa.entries()]
          .map(([chave, item]) => [chave, [...new Set(item.ids)]])
          .filter(([, ids]) => ids.length > 1)
          .map(([chave]) => chave)
      );
    }}

    function renderReincidencias(registros) {{
      atualizarIndicadoresOrdenacao();
      const chavesReincidentes = obterChavesReincidentes(registros);
      const intervaloReincidencia = obterIntervaloReincidencia30Dias();
      reincidenciasBody.innerHTML = "";

      if (!chavesReincidentes.size) {{
        reincidenciasBody.innerHTML = `<tr><td colspan="${len(detalhe_cols) if detalhe_cols else 1}" class="empty">Nenhuma reincidência encontrada para os filtros atuais.</td></tr>`;
        return;
      }}

      const linhas = registros
        .filter((registro) => {{
          const dataBase = obterDataBaseTexto(registro);
          if (!intervaloReincidencia || !dataBase) return false;
          if (dataBase < intervaloReincidencia.inicio || dataBase > intervaloReincidencia.fim) return false;

          const cliente = normalizarTexto(registro.cliente);
          const contrato = normalizarTexto(registro.contrato);
          const chave = `${{cliente}}|||${{contrato}}`;
          return chavesReincidentes.has(chave);
        }})
        .sort((a, b) => {{
          const clienteA = normalizarTexto(a.cliente);
          const clienteB = normalizarTexto(b.cliente);
          const contratoA = normalizarTexto(a.contrato);
          const contratoB = normalizarTexto(b.contrato);
          const dataA = obterDataBaseTexto(a);
          const dataB = obterDataBaseTexto(b);
          const comparacaoBase = compararRegistrosPorColuna(a, b, ordenacaoReincidencias.col)
            || clienteA.localeCompare(clienteB, "pt-BR", {{ sensitivity: "base" }})
            || contratoA.localeCompare(contratoB, "pt-BR", {{ sensitivity: "base" }})
            || dataA.localeCompare(dataB, "pt-BR", {{ sensitivity: "base" }});
          return ordenacaoReincidencias.dir === "asc" ? comparacaoBase : -comparacaoBase;
        }});

      linhas.forEach((registro) => {{
        const tr = document.createElement("tr");
        const linkSgp = obterLinkSgp(registro);
        if (linkSgp) {{
          tr.classList.add("row-link");
          tr.title = "Abrir no SGP";
          tr.addEventListener("click", () => {{
            window.open(linkSgp, "_blank", "noopener,noreferrer");
          }});
        }}
        detalheCols.forEach((coluna) => {{
          const td = document.createElement("td");
          td.textContent = coluna === "grupo_dashboard"
            ? obterGrupo(registro)
            : normalizarTexto(registro[coluna]);
          tr.appendChild(td);
        }});
        reincidenciasBody.appendChild(tr);
      }});
    }}

	    const graficoMensal = new Chart(document.getElementById("graficoMensal"), {{
      type: "bar",
      data: {{
        labels: mesesOrdem,
        datasets: [
          {{ label: "Finalizadas", data: [], backgroundColor: "#17624c" }},
          {{ label: "Técnicos", data: [], backgroundColor: "#4e9c83" }},
          {{ label: "Infra", data: [], backgroundColor: "#7bc6ac" }},
          {{ label: "Inviabilidade", data: [], backgroundColor: "#d18b2c" }},
          {{ label: "Outros", data: [], backgroundColor: "#b8d8c8" }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ position: "top" }}
        }},
        scales: {{
          y: {{ beginAtZero: true }},
          x: {{ grid: {{ display: false }} }}
        }}
	      }}
	    }});

	    const graficoDiario = new Chart(document.getElementById("graficoDiario"), {{
	      type: "line",
	      data: {{
	        labels: [],
	        datasets: []
	      }},
	      options: {{
	        responsive: true,
	        maintainAspectRatio: false,
	        interaction: {{ mode: "index", intersect: false }},
	        plugins: {{
	          legend: {{ position: "top" }}
	        }},
	        scales: {{
	          y: {{ beginAtZero: true, ticks: {{ precision: 0 }} }},
	          x: {{ grid: {{ display: false }} }}
	        }}
	      }}
	    }});

	    const paletaGraficoDiario = [
	      "#17624c",
	      "#4e9c83",
	      "#d18b2c",
	      "#7f5af0",
	      "#e85d75",
	      "#227c9d",
	      "#8f6f3a",
	      "#c05621",
	      "#3d7a57",
	      "#5c6ac4",
	      "#b83280",
	      "#2b6cb0",
	    ];

	    function hexParaRgba(hex, alpha) {{
	      const valor = hex.replace("#", "");
	      const r = Number.parseInt(valor.slice(0, 2), 16);
	      const g = Number.parseInt(valor.slice(2, 4), 16);
	      const b = Number.parseInt(valor.slice(4, 6), 16);
	      return `rgba(${{r}}, ${{g}}, ${{b}}, ${{alpha}})`;
	    }}

	    function renderGrafico(registros) {{
	      const resumo = agruparResumo(registros);
	      graficoMensal.data.datasets[0].data = resumo.map((item) => item.finalizadas);
      graficoMensal.data.datasets[1].data = resumo.map((item) => item.tecnicos);
      graficoMensal.data.datasets[2].data = resumo.map((item) => item.infra);
      graficoMensal.data.datasets[3].data = resumo.map((item) => item.inviabilidade);
	      graficoMensal.data.datasets[4].data = resumo.map((item) => item.outros);
	      graficoMensal.update();
	    }}

	    function obterIntervaloSelecionado() {{
	      const inicio = filtroDataInicial.value || dataInicialPadrao;
	      const fim = filtroDataFinal.value || dataFinalPadrao;
	      if (!inicio || !fim) return null;
	      return {{ inicio, fim }};
	    }}

	    function agruparResumoDiario(registros) {{
	      const intervalo = obterIntervaloSelecionado();
	      if (!intervalo) {{
	        return {{ labels: [], datasets: [], intervalo: null }};
	      }}

	      const labels = [];
	      const mapaIndices = new Map();
	      const cursor = new Date(`${{intervalo.inicio}}T00:00:00`);
	      const fim = new Date(`${{intervalo.fim}}T00:00:00`);
	      while (cursor <= fim) {{
	        const data = `${{cursor.getFullYear()}}-${{String(cursor.getMonth() + 1).padStart(2, "0")}}-${{String(cursor.getDate()).padStart(2, "0")}}`;
	        mapaIndices.set(data, labels.length);
	        labels.push(data.slice(8, 10) + "/" + data.slice(5, 7));
	        cursor.setDate(cursor.getDate() + 1);
	      }}
	      const mapaMembros = new Map();

	      registros.forEach((registro) => {{
	        const data = obterDataBaseTexto(registro);
	        if (!data || !mapaIndices.has(data)) return;

	        const membro = obterUsuario(registro) || "Sem usuário";
	        const indice = mapaIndices.get(data);
	        if (!mapaMembros.has(membro)) {{
	          mapaMembros.set(membro, Array.from({{ length: labels.length }}, () => 0));
	        }}
	        mapaMembros.get(membro)[indice] += 1;
	      }});

	      const datasets = [...mapaMembros.entries()]
	        .map(([membro, valores]) => ({{
	          membro,
	          valores,
	          total: valores.reduce((acc, valor) => acc + valor, 0),
	        }}))
	        .sort((a, b) => b.total - a.total || a.membro.localeCompare(b.membro, "pt-BR", {{ sensitivity: "base" }}))
	        .map((item, indice) => {{
	          const cor = paletaGraficoDiario[indice % paletaGraficoDiario.length];
	          return {{
	            label: item.membro,
	            data: item.valores,
	            borderColor: cor,
	            backgroundColor: hexParaRgba(cor, 0.14),
	            tension: 0.28,
	            fill: false,
	          }};
	        }});

	      return {{ labels, datasets, intervalo }};
	    }}

	    function renderGraficoDiario(registros) {{
	      const registrosBase = filtroGrupo.value
	        ? registros.filter((registro) => obterGrupoFiltro(registro) === filtroGrupo.value)
	        : registros;
	      const resumo = agruparResumoDiario(registrosBase);
	      graficoDiario.data.labels = resumo.labels;
	      graficoDiario.data.datasets = resumo.datasets;
	      graficoDiario.update();

	      if (!resumo.intervalo) {{
	        graficoDiarioMeta.textContent = "Sem dados suficientes para montar a evolução diária.";
	        return;
	      }}

	      const contextoGrupo = filtroGrupo.value ? ` do grupo ${{filtroGrupo.value}}` : "";
	      graficoDiarioMeta.textContent = `Evolução diária por membro${{contextoGrupo}} entre ${{resumo.intervalo.inicio}} e ${{resumo.intervalo.fim}}, usando a data-base de encerramento da O.S.`;
	    }}

    function atualizarMetas(registrosFinalizados, totalDetalhes, totalVotosValidos, totalVotosDetalhamento, totalDetalhamentoPops) {{
      const partes = [];
      if (filtroDataInicial.value) partes.push(`Data inicial: ${{filtroDataInicial.value}}`);
      if (filtroDataFinal.value) partes.push(`Data final: ${{filtroDataFinal.value}}`);
      if (filtroUsuario.value) partes.push(`Usuário: ${{filtroUsuario.value}}`);
      if (filtroGrupo.value) partes.push(`Grupo: ${{filtroGrupo.value}}`);
      if (filtroPop.value) partes.push(`POP: ${{filtroPop.value}}`);
      if (filtroBusca.value.trim()) partes.push(`Busca: ${{filtroBusca.value.trim()}}`);

      const textoFiltro = partes.length ? partes.join(" | ") : "Todos";
      atualizarTitulosPaineis();
      painelTempoMeta.textContent = `Tempo médio e backlog para o recorte: ${{textoFiltro}}.`;
      detalhamentoPopsMeta.textContent = `Tabela de POPs com ${{totalDetalhamentoPops}} O.S. no recorte atual, considerando os filtros aplicados na página.`;
      rankingMeta.textContent = `Ranking atualizado com ${{registrosFinalizados.length}} OS encerradas no recorte atual.`;
      rankingVotosResumoMeta.textContent = `Ranking atualizado com ${{totalVotosValidos}} voto(s) válido(s), considerando apenas 1 voto por IP e data no recorte atual.`;
      rankingVotosMeta.textContent = `Tabela de votos atualizada com ${{totalVotosDetalhamento}} registro(s) do recorte atual; duplicidades por IP e data ficam destacadas em vermelho.`;
      detalheMeta.textContent = `Mostrando ${{totalDetalhes}} registro(s) após aplicar os filtros.`;
      const intervaloReincidencia = obterIntervaloReincidencia30Dias();
      const descricaoReincidencia = intervaloReincidencia
        ? `janela de 30 dias entre ${{intervaloReincidencia.inicio}} e ${{intervaloReincidencia.fim}}`
        : "janela de 30 dias indisponível";
      reincidenciaMeta.textContent = `Mostrando as O.S. reincidentes de cliente/contrato na ${{descricaoReincidencia}}: ${{textoFiltro}}.`;
    }}

	    function aplicarFiltros() {{
	      normalizarPeriodoSelecionado();
	      salvarFiltros();
	      const registros = filtrarDetalhes();
      const registrosDetalhamentoPops = filtrarDetalhamentoPops(registros);
      const registrosFinalizados = registros.filter((registro) => ehStatusEncerrada(registro));
      const registrosVotos = filtrarVotosPorData();
      const registrosVotosUnicos = deduplicarVotosPorIpEData(registrosVotos);
      const registrosBaseEncerramentos = filtrarBaseEncerramentos().filter((registro) => ehStatusEncerrada(registro));
      const registrosBaseRanking = filtrarBaseRankingComparativo().filter((registro) => ehStatusEncerrada(registro));
      const registrosBaseReincidencias = filtrarBaseReincidencias();
	      renderStatusCards(registros);
	      renderMotivoCards(registros);
	      renderPopCards(registros);
	      renderDetalhamentoPops(registrosDetalhamentoPops);
	      renderCardsEncerramentos(registrosBaseEncerramentos);
	      renderTempoBacklog(registros, registrosFinalizados);
	      renderRanking(registrosFinalizados, registrosBaseRanking);
	      renderRankingVotosResumo(registrosVotos);
	      renderRankingVotos(registrosVotos);
	      renderDetalhes(registros);
	      renderReincidencias(registrosBaseReincidencias);
	      renderGrafico(registrosFinalizados);
	      renderGraficoDiario(registrosFinalizados);
	      atualizarMetas(registrosFinalizados, registros.length, registrosVotosUnicos.length, registrosVotos.length, registrosDetalhamentoPops.length);
	    }}

    function formatarDataInput(data) {{
      const ano = data.getFullYear();
      const mes = String(data.getMonth() + 1).padStart(2, "0");
      const dia = String(data.getDate()).padStart(2, "0");
      return `${{ano}}-${{mes}}-${{dia}}`;
    }}

    function aplicarAtalhoPeriodo(tipo) {{
      const referencia = dataMaxDisponivel
        ? new Date(`${{dataMaxDisponivel}}T00:00:00`)
        : new Date();
      referencia.setHours(0, 0, 0, 0);
      let inicio = new Date(referencia);
      let fim = new Date(referencia);

      if (tipo === "ontem") {{
        inicio.setDate(inicio.getDate() - 1);
        fim = new Date(inicio);
      }} else if (tipo === "7dias") {{
        inicio.setDate(inicio.getDate() - 6);
      }} else if (tipo === "30dias") {{
        inicio.setDate(inicio.getDate() - 29);
      }} else if (tipo === "mes-atual") {{
        inicio = new Date(referencia.getFullYear(), referencia.getMonth(), 1);
      }}

      filtroDataInicial.value = formatarDataInput(inicio);
      filtroDataFinal.value = formatarDataInput(fim);
      normalizarPeriodoSelecionado();
      aplicarFiltros();
    }}

    [filtroDataInicial, filtroDataFinal, filtroUsuario, filtroGrupo, filtroPop].forEach((select) => {{
      select.addEventListener("change", aplicarFiltros);
    }});

    filtroBusca.addEventListener("input", aplicarFiltros);
    quickRangeButtons.forEach((button) => {{
      button.addEventListener("click", () => aplicarAtalhoPeriodo(button.dataset.range));
    }});

    function formatarTempo(totalSegundos) {{
      const minutos = Math.floor(totalSegundos / 60);
      const segundos = totalSegundos % 60;
      return `${{String(minutos).padStart(2, "0")}}:${{String(segundos).padStart(2, "0")}}`;
    }}

    function atualizarVisibilidadeOverlay(ativo, mensagem = "", status = "", erro = false) {{
      updateOverlay.classList.toggle("active", ativo);
      updateOverlay.classList.toggle("error", Boolean(erro));
      updateOverlay.setAttribute("aria-hidden", ativo ? "false" : "true");
      if (mensagem) updateOverlayMessage.textContent = mensagem;
      if (status) updateOverlayStatus.textContent = status;
    }}

    function encerrarEstadoAtualizacao() {{
      atualizandoArquivos = false;
      refreshNowButton.disabled = false;
      restanteRefresh = refreshSeconds;
      refreshCountdown.textContent = formatarTempo(restanteRefresh);
      if (pollingAtualizacaoId) {{
        window.clearInterval(pollingAtualizacaoId);
        pollingAtualizacaoId = null;
      }}
    }}

    async function consultarStatusAtualizacao() {{
      try {{
        const resposta = await window.fetch(refreshStatusUrl, {{
          method: "GET",
          mode: "cors",
          headers: {{
            "Accept": "application/json",
          }},
        }});
        const payload = await resposta.json().catch(() => ({{ running: false, ok: false, message: "Resposta inválida do servidor." }}));

        if (payload.running) {{
          updateOverlayStatus.textContent = payload.message || "Atualização em andamento...";
          return;
        }}

        if (payload.ok) {{
          updateOverlayStatus.textContent = payload.message || "Dados atualizados com sucesso. Recarregando a página...";
          encerrarEstadoAtualizacao();
          window.setTimeout(() => {{
            window.location.reload();
          }}, 700);
          return;
        }}

        throw new Error(payload.message || "Falha ao atualizar arquivos.");
      }} catch (erro) {{
        const mensagemErro = erro instanceof Error ? erro.message : "Falha ao consultar atualização.";
        const dicaServidor = window.location.protocol === "file:"
          ? "Inicie o servidor local com `./.venv/bin/python dashboard_server.py --host 127.0.0.1 --port 8765`."
          : "Confirme se o servidor local do dashboard está em execução.";
        atualizarVisibilidadeOverlay(
          true,
          `Não foi possível acompanhar a atualização. ${{dicaServidor}}`,
          mensagemErro,
          true,
        );
        encerrarEstadoAtualizacao();
      }}
    }}

    function iniciarPollingAtualizacao() {{
      if (pollingAtualizacaoId) {{
        window.clearInterval(pollingAtualizacaoId);
      }}
      pollingAtualizacaoId = window.setInterval(() => {{
        consultarStatusAtualizacao();
      }}, 1500);
      consultarStatusAtualizacao();
    }}

    async function executarAtualizacaoArquivos(origem) {{
      if (atualizandoArquivos) return;

      atualizandoArquivos = true;
      refreshNowButton.disabled = true;
      const target = origem === "auto" ? "os" : "all";
      const mensagem = origem === "auto"
        ? "A contagem chegou ao fim e o dashboard está atualizando apenas as O.S. mais recentes."
        : "O dashboard está executando uma atualização completa de O.S. e votos.";
      atualizarVisibilidadeOverlay(true, mensagem, "Executando rotina automática de atualização...");
      refreshCountdown.textContent = "atualizando";
      salvarFiltros();

      try {{
        const urlAtualizacao = `${{refreshApiUrl}}?target=${{encodeURIComponent(target)}}`;
        const resposta = await window.fetch(urlAtualizacao, {{
          method: "POST",
          mode: "cors",
          headers: {{
            "Accept": "application/json",
          }},
        }});
        const payload = await resposta.json().catch(() => ({{ ok: false, message: "Resposta inválida do servidor." }}));

        if (!resposta.ok || !payload.ok) {{
          throw new Error(payload.message || "Não foi possível atualizar os arquivos.");
        }}
        updateOverlayStatus.textContent = payload.message || "Atualização iniciada. Acompanhando progresso...";
        iniciarPollingAtualizacao();
      }} catch (erro) {{
        const mensagemErro = erro instanceof Error ? erro.message : "Falha ao atualizar arquivos.";
        const dicaServidor = window.location.protocol === "file:"
          ? "Inicie o servidor local com `./.venv/bin/python dashboard_server.py --host 127.0.0.1 --port 8765`."
          : "Confirme se o servidor local do dashboard está em execução.";
        atualizarVisibilidadeOverlay(
          true,
          `Não foi possível gerar os arquivos agora. ${{dicaServidor}}`,
          mensagemErro,
          true,
        );
        encerrarEstadoAtualizacao();
      }}
    }}

    function iniciarAutoRefresh() {{
      refreshCountdown.textContent = formatarTempo(restanteRefresh);

      intervaloRefreshId = window.setInterval(() => {{
        if (atualizandoArquivos) return;

        restanteRefresh -= 1;
        if (restanteRefresh <= 0) {{
          refreshCountdown.textContent = "00:00";
          executarAtualizacaoArquivos("auto");
          return;
        }}
        refreshCountdown.textContent = formatarTempo(restanteRefresh);
      }}, 1000);
    }}

    refreshNowButton.addEventListener("click", () => {{
      executarAtualizacaoArquivos("manual");
    }});
    detalhesHead.addEventListener("click", (event) => {{
      const botao = event.target.closest(".sort-header");
      if (!botao) return;
      const coluna = botao.dataset.col;
      ordenacaoDetalhes = {{
        col: coluna,
        dir: ordenacaoDetalhes.col === coluna && ordenacaoDetalhes.dir === "asc" ? "desc" : "asc",
      }};
      renderDetalhes(filtrarDetalhes());
    }});
    rankingVotosHead.addEventListener("click", (event) => {{
      const botao = event.target.closest(".sort-header");
      if (!botao) return;
      const coluna = botao.dataset.col;
      ordenacaoRankingVotos = {{
        col: coluna,
        dir: ordenacaoRankingVotos.col === coluna && ordenacaoRankingVotos.dir === "asc" ? "desc" : "asc",
      }};
      renderRankingVotos(filtrarVotosPorData());
    }});
    reincidenciasHead.addEventListener("click", (event) => {{
      const botao = event.target.closest(".sort-header");
      if (!botao) return;
      const coluna = botao.dataset.col;
      ordenacaoReincidencias = {{
        col: coluna,
        dir: ordenacaoReincidencias.col === coluna && ordenacaoReincidencias.dir === "asc" ? "desc" : "asc",
      }};
      renderReincidencias(filtrarDetalhes());
    }});

    recalcularMetadadosBase();
    carregarDadosDashboardRemotos().finally(() => {{
      popularFiltros();
      restaurarFiltros();
      aplicarFiltros();
      iniciarAutoRefresh();
    }});
  </script>
</body>
</html>
"""
    Path(output_html).write_text(html, encoding="utf-8")
