from __future__ import annotations

import ast
import pandas as pd
from typing import Dict, Any, List


MAPA_MESES = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}


def normalizar_nome(valor: Any) -> str:
    return str(valor or "").strip().lower()


def normalizar_status(valor: Any, status_id: Any) -> str:
    texto = str(valor or "").strip()
    if texto:
        return texto

    mapa_status = {
        0: "Aberta",
        1: "Encerrada",
        2: "Em execução",
        3: "Pendente",
    }

    try:
        return mapa_status.get(int(status_id), "Desconhecido")
    except (TypeError, ValueError):
        return "Desconhecido"


def classificar_finalizador(nome: Any, tecnicos: List[str], infra_keywords: List[str]) -> str:
    nome_norm = normalizar_nome(nome)

    if not nome_norm:
        return "Outros"

    if any(chave in nome_norm for chave in infra_keywords):
        return "Infra"

    if nome_norm in tecnicos:
        return "Técnicos"

    return "Outros"


def classificar_grupo(
    finalizador: Any,
    responsavel: Any,
    tecnicos_auxiliares: Any,
    contrato_status: Any,
    tecnicos: List[str],
    infra_keywords: List[str],
) -> str:
    nome_norm = normalizar_nome(finalizador)
    responsavel_norm = normalizar_nome(responsavel)
    auxiliares_norm = extrair_auxiliares(tecnicos_auxiliares)
    contrato_status_norm = normalizar_nome(contrato_status)

    if contrato_status_norm == normalizar_nome("Inviabilidade Técnica"):
        return "Inviabilidade"

    nomes_operacionais = [valor for valor in [nome_norm, responsavel_norm, *auxiliares_norm] if valor]

    if any(any(chave in valor for chave in infra_keywords) for valor in nomes_operacionais):
        return "Infra"

    if any(valor in tecnicos for valor in nomes_operacionais):
        return "Técnicos"

    if any(chave in nome_norm for chave in infra_keywords):
        return "Infra"

    if nome_norm in tecnicos:
        return "Técnicos"

    return "Outros"


def classificar_grupo_encerramento(
    finalizador: Any,
    responsavel: Any,
    tecnicos: List[str],
    infra_keywords: List[str],
) -> str:
    finalizador_norm = normalizar_nome(finalizador)
    responsavel_norm = normalizar_nome(responsavel)

    # Regra de negocio: quando houver divergencia, "Finalizado Por" prevalece.
    if responsavel_norm and responsavel_norm != finalizador_norm:
        return classificar_finalizador(finalizador, tecnicos, infra_keywords)

    return classificar_finalizador(finalizador, tecnicos, infra_keywords)


def classificar_responsavel_encerramento(finalizador: Any, responsavel: Any) -> str:
    finalizador_norm = normalizar_nome(finalizador)
    responsavel_norm = normalizar_nome(responsavel)

    if finalizador_norm and responsavel_norm and finalizador_norm == responsavel_norm:
        return "Pelo responsável"

    return "Por outros"


def extrair_auxiliares(valor: Any) -> List[str]:
    if valor is None:
        return []

    if isinstance(valor, list):
        return [normalizar_nome(item) for item in valor if normalizar_nome(item)]

    texto = str(valor).strip()
    if not texto or texto == "[]":
        return []

    try:
        convertido = ast.literal_eval(texto)
    except (ValueError, SyntaxError):
        convertido = [texto]

    if isinstance(convertido, list):
        return [normalizar_nome(item) for item in convertido if normalizar_nome(item)]

    return [normalizar_nome(convertido)] if normalizar_nome(convertido) else []


def classificar_total_os_encerramento(finalizador: Any, responsavel: Any, tecnicos_auxiliares: Any) -> str:
    finalizador_norm = normalizar_nome(finalizador)
    responsavel_norm = normalizar_nome(responsavel)
    auxiliares_norm = extrair_auxiliares(tecnicos_auxiliares)

    equipe_responsavel = {nome for nome in [responsavel_norm, *auxiliares_norm] if nome}
    if finalizador_norm and finalizador_norm in equipe_responsavel:
        return "Na equipe responsável"

    return "Fora da equipe responsável"


def detectar_coluna(df: pd.DataFrame, candidatas: List[str]) -> str:
    cols_norm = {str(c).strip().lower(): c for c in df.columns}
    for cand in candidatas:
        if cand.lower() in cols_norm:
            return cols_norm[cand.lower()]
    raise KeyError(f"Nenhuma das colunas candidatas foi encontrada: {candidatas}")


def preparar_dataframe(raw_data: List[Dict[str, Any]], config: Dict[str, Any]) -> pd.DataFrame:
    df = pd.DataFrame(raw_data)

    if df.empty:
        return df

    # Ajuste estas candidatas conforme o JSON real da API
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

    col_data_criacao = detectar_coluna(df, [
        "criada",
        "data_criacao",
        "data cadastro",
        "data_cadastro",
        "created_at",
    ])

    col_status = detectar_coluna(df, [
        "status",
        "status_nome",
        "situacao",
    ])

    try:
        col_status_id = detectar_coluna(df, [
            "status_id",
            "statusid",
            "id_status",
        ])
    except KeyError:
        col_status_id = None

    try:
        col_contrato_status = detectar_coluna(df, [
            "status contrato",
            "status do contrato",
            "contrato_status",
            "status_contrato",
        ])
    except KeyError:
        col_contrato_status = None

    tecnicos = [normalizar_nome(x) for x in config["classificacao"].get("tecnicos", [])]
    infra_keywords = [normalizar_nome(x) for x in config["classificacao"].get("infra_keywords", [])]

    df["finalizado_por_dashboard"] = df[col_finalizado].astype(str).str.strip()
    df["data_finalizacao_dashboard"] = pd.to_datetime(df[col_data_finalizacao], errors="coerce")
    df["data_criacao_dashboard"] = pd.to_datetime(df[col_data_criacao], errors="coerce")
    # A base principal do dashboard usa a data de encerramento; para OS sem encerramento,
    # mantemos a criacao como fallback para nao perder o acompanhamento operacional.
    df["data_base_dashboard"] = df["data_finalizacao_dashboard"].combine_first(df["data_criacao_dashboard"])
    df["contrato_status_dashboard"] = (
        df[col_contrato_status].astype(str).str.strip()
        if col_contrato_status
        else ""
    )
    df["status_dashboard"] = df.apply(
        lambda row: normalizar_status(
            row.get(col_status, ""),
            row.get(col_status_id, "") if col_status_id else "",
        ),
        axis=1,
    )
    df["mes_num"] = df["data_base_dashboard"].dt.month
    df["mes_nome"] = df["mes_num"].map(MAPA_MESES)
    df["mes_criacao_num"] = df["data_criacao_dashboard"].dt.month
    df["mes_criacao_nome"] = df["mes_criacao_num"].map(MAPA_MESES)
    df["grupo_dashboard"] = df.apply(
        lambda row: classificar_grupo(
            finalizador=row.get("finalizado_por_dashboard"),
            responsavel=row.get("responsavel", ""),
            tecnicos_auxiliares=row.get("tecnicos_auxiliares", ""),
            contrato_status=row.get("contrato_status_dashboard", ""),
            tecnicos=tecnicos,
            infra_keywords=infra_keywords,
        ),
        axis=1,
    )
    df["grupo_encerramento_dashboard"] = df.apply(
        lambda row: classificar_grupo_encerramento(
            finalizador=row.get("finalizado_por_dashboard"),
            responsavel=row.get("responsavel", ""),
            tecnicos=tecnicos,
            infra_keywords=infra_keywords,
        ),
        axis=1,
    )
    df["responsavel_encerramento_dashboard"] = df.apply(
        lambda row: classificar_responsavel_encerramento(
            finalizador=row.get("finalizado_por_dashboard"),
            responsavel=row.get("responsavel", ""),
        ),
        axis=1,
    )
    df["total_os_encerramento_dashboard"] = df.apply(
        lambda row: classificar_total_os_encerramento(
            finalizador=row.get("finalizado_por_dashboard"),
            responsavel=row.get("responsavel", ""),
            tecnicos_auxiliares=row.get("tecnicos_auxiliares", ""),
        ),
        axis=1,
    )

    return df


def resumo_mensal(df: pd.DataFrame) -> pd.DataFrame:
    meses_ordem = list(MAPA_MESES.values())
    base = pd.DataFrame({"mes_nome": meses_ordem})

    if df.empty:
        base["Finalizadas"] = 0
        base["Técnicos"] = 0
        base["Infra"] = 0
        base["Inviabilidade"] = 0
        base["Outros"] = 0
        return base

    total = df.groupby("mes_nome").size().rename("Finalizadas")
    tecnicos = df[df["grupo_dashboard"] == "Técnicos"].groupby("mes_nome").size().rename("Técnicos")
    infra = df[df["grupo_dashboard"] == "Infra"].groupby("mes_nome").size().rename("Infra")
    inviabilidade = df[df["grupo_dashboard"] == "Inviabilidade"].groupby("mes_nome").size().rename("Inviabilidade")
    outros = df[df["grupo_dashboard"] == "Outros"].groupby("mes_nome").size().rename("Outros")

    out = (
        base.merge(total, on="mes_nome", how="left")
            .merge(tecnicos, on="mes_nome", how="left")
            .merge(infra, on="mes_nome", how="left")
            .merge(inviabilidade, on="mes_nome", how="left")
            .merge(outros, on="mes_nome", how="left")
            .fillna(0)
    )

    for c in ["Finalizadas", "Técnicos", "Infra", "Inviabilidade", "Outros"]:
        out[c] = out[c].astype(int)

    return out


def ranking_finalizadores(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Finalizado Por", "Grupo", "Total"])

    ranking = (
        df.groupby(["finalizado_por_dashboard", "grupo_dashboard"])
          .size()
          .reset_index(name="Total")
          .sort_values(["Total", "finalizado_por_dashboard"], ascending=[False, True])
          .rename(columns={
              "finalizado_por_dashboard": "Finalizado Por",
              "grupo_dashboard": "Grupo"
          })
    )
    return ranking
