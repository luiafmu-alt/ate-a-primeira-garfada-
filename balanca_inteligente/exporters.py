"""Exportação dos registros em JSON ou CSV."""
from __future__ import annotations

import csv
import io
import json
from typing import Dict, List

from .models import CATEGORIAS

COLUNAS_CSV = (
    ["id", "data_hora", "atendimento_id", "alimentos", "peso_total_g", "temperatura_c",
     "origem_alimentos", "origem_peso", "origem_temperatura", "dados_simulados",
     "campos_simulados", "demonstracao", "schema_versao"]
    + [f"pct_{c}" for c in CATEGORIAS]
)


def para_json(registros: List[Dict]) -> str:
    return json.dumps(registros, ensure_ascii=False, indent=2)


def para_csv(registros: List[Dict]) -> str:
    """Listas viram texto separado por ';'; composição vira uma coluna por categoria."""
    saida = io.StringIO()
    escritor = csv.DictWriter(saida, fieldnames=COLUNAS_CSV, lineterminator="\n")
    escritor.writeheader()
    for r in registros:
        linha = {c: r.get(c, "") for c in COLUNAS_CSV}
        linha["alimentos"] = ";".join(r.get("alimentos", []))
        linha["campos_simulados"] = ";".join(r.get("campos_simulados", []))
        for c in CATEGORIAS:
            linha[f"pct_{c}"] = r.get("composicao_pct", {}).get(c, 0)
        escritor.writerow(linha)
    return saida.getvalue()
