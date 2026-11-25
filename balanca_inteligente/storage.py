"""Persistência em SQLite (biblioteca padrão do Python, arquivo único).

O registro completo fica em `payload` (JSON, formato oficial do módulo);
as colunas ao lado existem só para consultas e agregações rápidas. Outro
módulo pode ler o arquivo .db direto, a API HTTP, ou os exports CSV/JSON.
"""
from __future__ import annotations

import json
import os
import sqlite3
from collections import Counter
from contextlib import contextmanager
from typing import Dict, Iterator, List, Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pesagens (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT UNIQUE NOT NULL,
    data_hora TEXT NOT NULL,
    atendimento_id TEXT NOT NULL,
    peso_total_g REAL NOT NULL,
    temperatura_c REAL NOT NULL,
    origem_temperatura TEXT NOT NULL,
    dados_simulados INTEGER NOT NULL,
    demonstracao INTEGER NOT NULL DEFAULT 0,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pesagens_data ON pesagens (data_hora);
"""


class RepositorioPesagens:
    def __init__(self, caminho: str = "data/pesagens.db"):
        self.caminho = caminho
        if caminho != ":memory:":
            pasta = os.path.dirname(os.path.abspath(caminho))
            os.makedirs(pasta, exist_ok=True)
        self._memoria: Optional[sqlite3.Connection] = None
        if caminho == ":memory:":
            self._memoria = sqlite3.connect(":memory:", check_same_thread=False)
        with self._conexao() as con:
            con.executescript(_SCHEMA)

    @contextmanager
    def _conexao(self) -> Iterator[sqlite3.Connection]:
        if self._memoria is not None:
            con = self._memoria
            try:
                yield con
                con.commit()
            except Exception:
                con.rollback()
                raise
            return
        con = sqlite3.connect(self.caminho, timeout=10)
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    # ------------------------------------------------------------------ escrita
    def adicionar(self, registro: Dict) -> Dict:
        """Grava o registro, gerando o ID sequencial (PESAGEM_001, 002, ...)."""
        with self._conexao() as con:
            cur = con.execute(
                "INSERT INTO pesagens (id, data_hora, atendimento_id, peso_total_g, "
                "temperatura_c, origem_temperatura, dados_simulados, demonstracao, payload) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    f"TMP_{os.urandom(6).hex()}",
                    registro["data_hora"],
                    registro["atendimento_id"],
                    registro["peso_total_g"],
                    registro["temperatura_c"],
                    registro["origem_temperatura"],
                    int(registro["dados_simulados"]),
                    int(registro.get("demonstracao", False)),
                    "{}",
                ),
            )
            novo_id = f"PESAGEM_{cur.lastrowid:03d}"
            final = {"id": novo_id, **registro}
            con.execute(
                "UPDATE pesagens SET id=?, payload=? WHERE seq=?",
                (novo_id, json.dumps(final, ensure_ascii=False), cur.lastrowid),
            )
        return final

    def limpar_demonstracao(self) -> int:
        """Apaga somente registros marcados como demonstração."""
        with self._conexao() as con:
            return con.execute("DELETE FROM pesagens WHERE demonstracao=1").rowcount

    # ------------------------------------------------------------------ leitura
    def obter(self, id_: str) -> Optional[Dict]:
        with self._conexao() as con:
            row = con.execute("SELECT payload FROM pesagens WHERE id=?", (id_,)).fetchone()
        return json.loads(row[0]) if row else None

    def listar(self, limite: int = 100, offset: int = 0) -> List[Dict]:
        """Mais recentes primeiro."""
        with self._conexao() as con:
            rows = con.execute(
                "SELECT payload FROM pesagens ORDER BY data_hora DESC, seq DESC LIMIT ? OFFSET ?",
                (limite, offset),
            ).fetchall()
        return [json.loads(r[0]) for r in rows]

    def todos(self) -> List[Dict]:
        """Todos em ordem cronológica (para exportação/análise)."""
        with self._conexao() as con:
            rows = con.execute("SELECT payload FROM pesagens ORDER BY data_hora ASC, seq ASC").fetchall()
        return [json.loads(r[0]) for r in rows]

    def resumo(self) -> Dict:
        with self._conexao() as con:
            total, peso_medio, temp_media, pmin, pmax, tmin, tmax, simulados, demos = con.execute(
                "SELECT COUNT(*), AVG(peso_total_g), AVG(temperatura_c), MIN(peso_total_g), "
                "MAX(peso_total_g), MIN(temperatura_c), MAX(temperatura_c), "
                "COALESCE(SUM(dados_simulados),0), COALESCE(SUM(demonstracao),0) FROM pesagens"
            ).fetchone()
            payloads = con.execute("SELECT payload FROM pesagens").fetchall()
        freq = Counter(a for (p,) in payloads for a in json.loads(p)["alimentos"])

        def r(v, n=1):
            return None if v is None else round(v, n)

        return {
            "total_pesagens": total,
            "peso_medio_g": r(peso_medio),
            "temperatura_media_c": r(temp_media),
            "peso_min_g": pmin,
            "peso_max_g": pmax,
            "temperatura_min_c": tmin,
            "temperatura_max_c": tmax,
            "registros_simulados": simulados,
            "registros_demonstracao": demos,
            "alimentos_mais_frequentes": [{"alimento": a, "pratos": n} for a, n in freq.most_common(5)],
        }
