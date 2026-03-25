from __future__ import annotations

import json
from html import escape
from pathlib import Path
import pandas as pd


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
        "responsavel_encerramento_dashboard",
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


def gerar_html_dashboard(
    resumo_df: pd.DataFrame,
    ranking_df: pd.DataFrame,
    detalhes_df: pd.DataFrame,
    finalizadas_df: pd.DataFrame,
    ano: int,
    mes_selecionado: str,
    refresh_seconds: int,
    sgp_base_url: str,
    output_html: str,
) -> None:
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
        "data_base_dashboard": "Data base",
        "data_criacao_dashboard": "Criada em",
        "finalizado_por_dashboard": "Finalizado por",
        "grupo_dashboard": "Grupo",
        "status_dashboard": "Status",
    }

    cards = {
        "aberta": int((detalhes_df["status_dashboard"] == "Aberta").sum()) if not detalhes_df.empty else 0,
        "encerrada": int(len(finalizadas_df)) if not finalizadas_df.empty else 0,
        "pendente": int((detalhes_df["status_dashboard"] == "Pendente").sum()) if not detalhes_df.empty else 0,
        "em_execucao": int((detalhes_df["status_dashboard"] == "Em execução").sum()) if not detalhes_df.empty else 0,
        "inviabilidade": int((detalhes_df["contrato_status_dashboard"].fillna("").astype(str).str.strip() == "Inviabilidade Técnica").sum())
        if "contrato_status_dashboard" in detalhes_df.columns and not detalhes_df.empty else 0,
        "instalacoes": int((detalhes_df["motivo"].fillna("").astype(str).str.strip() == "Instalação de KIT").sum()) if "motivo" in detalhes_df.columns else 0,
        "remocoes": int((detalhes_df["motivo"].fillna("").astype(str).str.strip() == "Remoção de KIT").sum()) if "motivo" in detalhes_df.columns else 0,
        "pelo_responsavel": int((finalizadas_df["responsavel_encerramento_dashboard"] == "Pelo responsável").sum())
        if "responsavel_encerramento_dashboard" in finalizadas_df.columns and not finalizadas_df.empty else 0,
        "por_outros": int((finalizadas_df["responsavel_encerramento_dashboard"] == "Por outros").sum())
        if "responsavel_encerramento_dashboard" in finalizadas_df.columns and not finalizadas_df.empty else 0,
    }

    detalhes_data = _serializar_registros(detalhes_df, detalhe_cols) if detalhe_cols else []
    meses_ordem = resumo_df["mes_nome"].tolist()
    refresh_seconds = max(int(refresh_seconds), 30)

    if "data_base_dashboard" in detalhes_df.columns and not detalhes_df["data_base_dashboard"].dropna().empty:
        data_inicial_padrao = detalhes_df["data_base_dashboard"].dropna().min().strftime("%Y-%m-%d")
        data_final_padrao = detalhes_df["data_base_dashboard"].dropna().max().strftime("%Y-%m-%d")
    else:
        data_inicial_padrao = ""
        data_final_padrao = ""

    titulo_periodo = "Base principal: data de encerramento"
    header_cols = "".join(f"<th>{escape(detalhe_labels.get(col, col))}</th>" for col in detalhe_cols)

    html = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Dashboard OS SGP</title>
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
    }}
    .summary-card.secondary {{
      grid-template-columns: 1fr;
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
      grid-template-columns: repeat(3, minmax(0, 1fr));
      width: 100%;
      justify-content: stretch;
      align-content: start;
      align-items: stretch;
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
    .metric-value {{
      display: block;
      font-size: 32px;
      font-weight: 800;
      letter-spacing: -0.03em;
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
    tbody tr:nth-child(even) {{
      background: rgba(220, 239, 231, 0.23);
    }}
    tbody tr:hover {{
      background: rgba(220, 239, 231, 0.40);
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
  <div class="wrap">
    <section class="hero">
      <div class="hero-head">
        <div class="hero-titles">
          <h1>Dashboard de OS SGP</h1>
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
        <label for="filtroUsuario">Finalizado por</label>
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
	      <div class="summary-card primary">
	        <div class="summary-card-head">
	          <h3>Encerramentos</h3>
	          <p class="caption">Visão consolidada das O.S. encerradas e da comparação entre responsável e finalizador.</p>
	        </div>
	        <div class="metric-grid cols-2">
	          <div class="metric-item"><span class="metric-label">Total de O.S. encerradas</span><span class="metric-value" id="cardEncerrada">{cards['encerrada']}</span></div>
	          <div class="metric-item"><span class="metric-label">Encerradas pelo responsável</span><span class="metric-value" id="cardPeloResponsavel">{cards['pelo_responsavel']}</span></div>
	          <div class="metric-item"><span class="metric-label">Encerradas por outros</span><span class="metric-value" id="cardPorOutros">{cards['por_outros']}</span></div>
	        </div>
	      </div>
	      <div class="summary-card secondary">
	        <div class="summary-card-head">
	          <h3>Status Operacional</h3>
	          <p class="caption">Panorama das ordens ainda em andamento ou com impedimentos no período filtrado.</p>
	        </div>
	        <div class="metric-grid cols-2">
	          <div class="metric-item"><span class="metric-label">Em aberto</span><span class="metric-value" id="cardAberta">{cards['aberta']}</span></div>
	          <div class="metric-item"><span class="metric-label">Pendentes</span><span class="metric-value" id="cardPendente">{cards['pendente']}</span></div>
	          <div class="metric-item"><span class="metric-label">Em execução</span><span class="metric-value" id="cardEmExecucao">{cards['em_execucao']}</span></div>
	        </div>
	      </div>
	      <div class="summary-card tertiary">
	        <div class="summary-card-head">
	          <h3>Movimentações</h3>
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
	          <h3>POPs</h3>
	          <p class="caption">Distribuição das O.S. por POP no recorte filtrado.</p>
	        </div>
	        <div class="metric-grid flow scrollable" id="popsGrid">
	          <div class="metric-item compact"><span class="metric-label">Sem POPs no recorte</span><span class="metric-value">0</span></div>
	        </div>
	      </div>
	    </div>

	    <div class="grid-panels">
	      <div class="panel">
	        <h2 class="section-title">Tempo médio e backlog</h2>
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

      <div class="panel">
        <h2 class="section-title">Ranking por finalizador</h2>
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
    </div>

	    <div class="panel full">
	      <h2 class="section-title">Gráfico mensal</h2>
	      <canvas id="graficoMensal"></canvas>
	    </div>

	    <div class="panel full">
	      <h2 class="section-title">Evolução diária dos grupos</h2>
	      <div class="panel-meta" id="graficoDiarioMeta">Mostrando a evolução diária por grupo no mês selecionado.</div>
	      <canvas id="graficoDiario"></canvas>
	    </div>

	    <div class="panel full">
	      <h2 class="section-title">Detalhamento</h2>
	      <div class="panel-meta" id="detalheMeta">Mostrando os registros filtrados.</div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>{header_cols}</tr>
          </thead>
          <tbody id="detalhesBody"></tbody>
        </table>
      </div>
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <script>
    const detalheCols = {json.dumps(detalhe_cols, ensure_ascii=False)};
    const mesesOrdem = {json.dumps(meses_ordem, ensure_ascii=False)};
    const detalhes = {json.dumps(detalhes_data, ensure_ascii=False)};
    const dataInicialPadrao = "{data_inicial_padrao}";
    const dataFinalPadrao = "{data_final_padrao}";
    const refreshSeconds = {refresh_seconds};
    const sgpBaseUrl = {json.dumps(sgp_base_url.rstrip("/"), ensure_ascii=False)};
    const filtroDataInicial = document.getElementById("filtroDataInicial");
    const filtroDataFinal = document.getElementById("filtroDataFinal");
    const filtroUsuario = document.getElementById("filtroUsuario");
    const filtroGrupo = document.getElementById("filtroGrupo");
    const filtroPop = document.getElementById("filtroPop");
    const filtroBusca = document.getElementById("filtroBusca");
    const quickRangeButtons = Array.from(document.querySelectorAll("[data-range]"));
    const refreshCountdown = document.getElementById("refreshCountdown");
    const refreshNowButton = document.getElementById("refreshNowButton");
	    const tempoBacklogBody = document.getElementById("tempoBacklogBody");
		    const rankingBody = document.getElementById("rankingBody");
		    const detalhesBody = document.getElementById("detalhesBody");
		    const painelTempoMeta = document.getElementById("painelTempoMeta");
		    const rankingMeta = document.getElementById("rankingMeta");
	    const graficoDiarioMeta = document.getElementById("graficoDiarioMeta");
    const detalheMeta = document.getElementById("detalheMeta");
	    const movimentacoesGrid = document.getElementById("movimentacoesGrid");
	    const popsGrid = document.getElementById("popsGrid");
    const storageKey = "dashboard_tecnico_filtros";

    function normalizarTexto(valor) {{
      return String(valor || "").trim();
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
	      if (responsavel && responsavel.localeCompare(usuarioNorm, "pt-BR", {{ sensitivity: "base" }}) === 0) {{
	        return true;
	      }}

	      return obterTecnicosAuxiliares(registro).some((auxiliar) =>
	        auxiliar.localeCompare(usuarioNorm, "pt-BR", {{ sensitivity: "base" }}) === 0
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
      }} catch (_erro) {{
        window.localStorage.removeItem(storageKey);
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

      preencherSelect(filtroUsuario, usuarios, "Todos os finalizadores");
      preencherSelect(filtroGrupo, grupos, "Todos os grupos");
      preencherSelect(filtroPop, pops, "Todos os POPs");

      const datasDisponiveis = detalhes.map(obterDataBaseTexto).filter(Boolean).sort();
      const dataMin = datasDisponiveis[0] || dataInicialPadrao;
      const dataMax = datasDisponiveis[datasDisponiveis.length - 1] || dataFinalPadrao;

      if (dataMin) {{
        filtroDataInicial.min = dataMin;
        filtroDataFinal.min = dataMin;
      }}
      if (dataMax) {{
        filtroDataInicial.max = dataMax;
        filtroDataFinal.max = dataMax;
      }}

      if (!filtroDataInicial.value) {{
        filtroDataInicial.value = dataInicialPadrao || dataMin || "";
      }}
      if (!filtroDataFinal.value) {{
        filtroDataFinal.value = dataFinalPadrao || dataMax || "";
      }}
    }}

    function dataDentroDoIntervalo(registro) {{
      const data = obterDataBaseTexto(registro);
      if (!data) return false;
      if (filtroDataInicial.value && data < filtroDataInicial.value) return false;
      if (filtroDataFinal.value && data > filtroDataFinal.value) return false;
      return true;
    }}

    function filtrarDetalhes() {{
      const busca = normalizarTexto(filtroBusca.value).toLowerCase();

      return detalhes.filter((registro) => {{
        if (!dataDentroDoIntervalo(registro)) return false;
        if (filtroUsuario.value && obterUsuario(registro) !== filtroUsuario.value) return false;
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
        if (filtroUsuario.value && obterUsuario(registro) !== filtroUsuario.value) return false;
        if (filtroGrupo.value && obterGrupoFiltro(registro) !== filtroGrupo.value) return false;
        if (filtroPop.value && obterPop(registro) !== filtroPop.value) return false;
        if (busca && !obterTextoBusca(registro).includes(busca)) return false;
        return true;
      }});
    }}

	    function filtrarBaseEncerramentos() {{
	      const busca = normalizarTexto(filtroBusca.value).toLowerCase();

	      return detalhes.filter((registro) => {{
	        if (!dataDentroDoIntervalo(registro)) return false;
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
	      let peloResponsavel = 0;
	      let porOutros = 0;
	      const usuarioFiltro = normalizarTexto(filtroUsuario.value);

	      registros.forEach((registro) => {{
	        const finalizador = normalizarTexto(registro.finalizado_por_dashboard);
	        const responsavel = normalizarTexto(registro.responsavel);

	        if (usuarioFiltro) {{
	          if (!usuarioNaEquipeResponsavel(registro, usuarioFiltro)) return;
	          totalOs += 1;
	          if (finalizador && finalizador.localeCompare(usuarioFiltro, "pt-BR", {{ sensitivity: "base" }}) === 0) {{
	            peloResponsavel += 1;
	          }} else {{
	            porOutros += 1;
	          }}
	        }} else {{
	          totalOs += 1;
	          if (finalizador && responsavel && finalizador.localeCompare(responsavel, "pt-BR", {{ sensitivity: "base" }}) === 0) {{
	            peloResponsavel += 1;
	          }} else {{
	            porOutros += 1;
	          }}
	        }}
	      }});

      return {{
        totalOs,
        peloResponsavel,
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

	      const cardInviabilidade = document.createElement("div");
	      cardInviabilidade.className = "metric-item compact";
	      cardInviabilidade.innerHTML = `<span class="metric-label">Inviabilidades</span><span class="metric-value">${{inviabilidade}}</span>`;
	      movimentacoesGrid.appendChild(cardInviabilidade);

	      if (!itens.length) {{
	        movimentacoesGrid.innerHTML = '<div class="metric-item compact"><span class="metric-label">Sem motivos no recorte</span><span class="metric-value">0</span></div>';
	        movimentacoesGrid.prepend(cardInviabilidade);
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

    function renderCardsEncerramentos(registros) {{
      const cards = calcularCardsEncerramentos(registros);
      document.getElementById("cardEncerrada").textContent = cards.totalOs;
      document.getElementById("cardPeloResponsavel").textContent = cards.peloResponsavel;
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

    function obterReferenciaMensalRanking(registros) {{
      const referencias = registros
        .map((registro) => obterDataBaseTexto(registro))
        .filter((data) => data && data.length >= 7)
        .map((data) => data.slice(0, 7))
        .sort();

      if (!referencias.length) return null;

      return referencias[referencias.length - 1];
    }}

    function calcularVariacaoRanking(registrosAtuais, registrosBase, usuario, grupo) {{
      const referenciaAtual = obterReferenciaMensalRanking(registrosAtuais);
      if (!referenciaAtual) {{
        return {{ texto: "-", classe: "flat" }};
      }}

      const [anoAtual, mesAtual] = referenciaAtual.split("-").map(Number);
      const dataAnterior = new Date(anoAtual, mesAtual - 2, 1);
      const referenciaAnterior = `${{dataAnterior.getFullYear()}}-${{String(dataAnterior.getMonth() + 1).padStart(2, "0")}}`;

      const atual = registrosBase.filter((registro) =>
        obterUsuario(registro) === usuario &&
        obterGrupoFiltro(registro) === grupo &&
        obterDataBaseTexto(registro).startsWith(referenciaAtual)
      ).length;

      const anterior = registrosBase.filter((registro) =>
        obterUsuario(registro) === usuario &&
        obterGrupoFiltro(registro) === grupo &&
        obterDataBaseTexto(registro).startsWith(referenciaAnterior)
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

    function renderDetalhes(registros) {{
      detalhesBody.innerHTML = "";

      if (!registros.length) {{
        detalhesBody.innerHTML = `<tr><td colspan="${len(detalhe_cols) if detalhe_cols else 1}" class="empty">Nenhum registro encontrado para os filtros atuais.</td></tr>`;
        return;
      }}

      registros.forEach((registro) => {{
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

    function atualizarMetas(registrosFinalizados, totalDetalhes) {{
      const partes = [];
      if (filtroDataInicial.value) partes.push(`Data inicial: ${{filtroDataInicial.value}}`);
      if (filtroDataFinal.value) partes.push(`Data final: ${{filtroDataFinal.value}}`);
      if (filtroUsuario.value) partes.push(`Finalizado por: ${{filtroUsuario.value}}`);
      if (filtroGrupo.value) partes.push(`Grupo: ${{filtroGrupo.value}}`);
      if (filtroPop.value) partes.push(`POP: ${{filtroPop.value}}`);
      if (filtroBusca.value.trim()) partes.push(`Busca: ${{filtroBusca.value.trim()}}`);

      const textoFiltro = partes.length ? partes.join(" | ") : "Todos";
      painelTempoMeta.textContent = `Tempo médio e backlog para o recorte: ${{textoFiltro}}.`;
      rankingMeta.textContent = `Ranking atualizado com ${{registrosFinalizados.length}} OS encerradas no recorte atual.`;
      detalheMeta.textContent = `Mostrando ${{totalDetalhes}} registro(s) após aplicar os filtros.`;
    }}

	    function aplicarFiltros() {{
	      if (filtroDataInicial.value && filtroDataFinal.value && filtroDataInicial.value > filtroDataFinal.value) {{
	        filtroDataFinal.value = filtroDataInicial.value;
	      }}
	      salvarFiltros();
	      const registros = filtrarDetalhes();
      const registrosFinalizados = registros.filter((registro) => ehStatusEncerrada(registro));
      const registrosBaseEncerramentos = filtrarBaseEncerramentos().filter((registro) => ehStatusEncerrada(registro));
      const registrosBaseRanking = filtrarBaseRanking().filter((registro) => ehStatusEncerrada(registro));
	      renderStatusCards(registros);
	      renderMotivoCards(registros);
	      renderPopCards(registros);
	      renderCardsEncerramentos(registrosBaseEncerramentos);
	      renderTempoBacklog(registros, registrosFinalizados);
	      renderRanking(registrosFinalizados, registrosBaseRanking);
	      renderDetalhes(registros);
	      renderGrafico(registrosFinalizados);
	      renderGraficoDiario(registrosFinalizados);
	      atualizarMetas(registrosFinalizados, registros.length);
	    }}

    function formatarDataInput(data) {{
      const ano = data.getFullYear();
      const mes = String(data.getMonth() + 1).padStart(2, "0");
      const dia = String(data.getDate()).padStart(2, "0");
      return `${{ano}}-${{mes}}-${{dia}}`;
    }}

    function aplicarAtalhoPeriodo(tipo) {{
      const hoje = new Date();
      hoje.setHours(0, 0, 0, 0);
      let inicio = new Date(hoje);
      let fim = new Date(hoje);

      if (tipo === "ontem") {{
        inicio.setDate(inicio.getDate() - 1);
        fim = new Date(inicio);
      }} else if (tipo === "7dias") {{
        inicio.setDate(inicio.getDate() - 6);
      }} else if (tipo === "30dias") {{
        inicio.setDate(inicio.getDate() - 29);
      }} else if (tipo === "mes-atual") {{
        inicio = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
      }}

      filtroDataInicial.value = formatarDataInput(inicio);
      filtroDataFinal.value = formatarDataInput(fim);
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

    function iniciarAutoRefresh() {{
      let restante = refreshSeconds;
      refreshCountdown.textContent = formatarTempo(restante);

      window.setInterval(() => {{
        restante -= 1;
        if (restante <= 0) {{
          refreshCountdown.textContent = "00:00";
          salvarFiltros();
          window.location.reload();
          return;
        }}
        refreshCountdown.textContent = formatarTempo(restante);
      }}, 1000);
    }}

    refreshNowButton.addEventListener("click", () => {{
      refreshCountdown.textContent = "00:00";
      salvarFiltros();
      window.location.reload();
    }});

    popularFiltros();
    restaurarFiltros();
    aplicarFiltros();
    iniciarAutoRefresh();
  </script>
</body>
</html>
"""
    Path(output_html).write_text(html, encoding="utf-8")
