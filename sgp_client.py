from __future__ import annotations

import requests
from typing import Dict, List, Any


class SGPClient:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.url_base = config["url_base"].rstrip("/")
        self.auth_mode = config.get("auth_mode", "basic").lower()

    def _build_auth(self):
        if self.auth_mode == "basic":
            auth_cfg = self.config.get("basic_auth", {})
            return (auth_cfg.get("username", ""), auth_cfg.get("password", ""))
        return None

    def _build_base_payload(self) -> Dict[str, Any]:
        if self.auth_mode == "app_token":
            auth_cfg = self.config.get("app_token_auth", {})
            return {
                "app": auth_cfg.get("app", ""),
                "token": auth_cfg.get("token", ""),
            }
        return {}

    def listar_ordens_servico(
        self,
        status: int = 1,
        data_finalizacao_inicio: str | None = None,
        data_finalizacao_fim: str | None = None,
        data_criacao_inicio: str | None = None,
        data_criacao_fim: str | None = None,
        extra_params: Dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        """
        Busca todas as OS paginando até esgotar o resultado.
        """
        endpoint = f"{self.url_base}/api/ura/ordemservico/list/"
        offset = 0
        limit = 1000
        resultados: List[Dict[str, Any]] = []

        while True:
            payload: Dict[str, Any] = {
                "status": status,
                "offset": offset,
                "limit": limit,
            }

            if data_finalizacao_inicio:
                payload["data_finalizacao_inicio"] = data_finalizacao_inicio
            if data_finalizacao_fim:
                payload["data_finalizacao_fim"] = data_finalizacao_fim
            if data_criacao_inicio:
                payload["data_cadastro_inicio"] = data_criacao_inicio
            if data_criacao_fim:
                payload["data_cadastro_fim"] = data_criacao_fim

            payload.update(self._build_base_payload())

            if extra_params:
                payload.update(extra_params)

            response = requests.post(
                endpoint,
                data=payload,
                auth=self._build_auth(),
                timeout=60,
            )
            response.raise_for_status()

            data = response.json()

            # Ajuste aqui se a API devolver em outra chave
            if isinstance(data, list):
                lote = data
            elif isinstance(data, dict):
                lote = (
                    data.get("data")
                    or data.get("results")
                    or data.get("ordens_servicos")
                    or data.get("ordens_servico")
                    or data.get("response")
                    or []
                )
            else:
                lote = []

            if not isinstance(lote, list):
                raise ValueError("Formato inesperado no retorno da API. Revise a chave do JSON.")

            resultados.extend(lote)

            if len(lote) < limit:
                break

            offset += limit

        return resultados

    def listar_ordens_servico_statuses(
        self,
        statuses: List[int],
        data_finalizacao_inicio: str | None = None,
        data_finalizacao_fim: str | None = None,
        data_criacao_inicio: str | None = None,
        data_criacao_fim: str | None = None,
        extra_params: Dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        resultados: List[Dict[str, Any]] = []

        for status in statuses:
            resultados.extend(
                self.listar_ordens_servico(
                    status=status,
                    data_finalizacao_inicio=data_finalizacao_inicio,
                    data_finalizacao_fim=data_finalizacao_fim,
                    data_criacao_inicio=data_criacao_inicio,
                    data_criacao_fim=data_criacao_fim,
                    extra_params=extra_params,
                )
            )

        return resultados
