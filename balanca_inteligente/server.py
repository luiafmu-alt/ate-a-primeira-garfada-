"""API HTTP + interface web (somente biblioteca padrão, sem dependências).

Rotas:
  GET    /                        interface
  POST   /api/pesagens            registra nova pesagem
  GET    /api/pesagens?limite=&offset=   histórico (mais recentes primeiro)
  GET    /api/pesagens/<id>       detalhe
  GET    /api/resumo              indicadores
  GET    /api/exportar?formato=json|csv
  POST   /api/demo?n=20           gera pesagens de demonstração
  DELETE /api/demo                apaga só os registros de demonstração
"""
from __future__ import annotations

import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import exporters
from .models import LeituraInvalida
from .service import BalancaInteligente

PASTA_ESTATICA = os.path.join(os.path.dirname(__file__), "static")
ID_RE = re.compile(r"^PESAGEM_\d+$")


def criar_handler(servico: BalancaInteligente):
    class Handler(BaseHTTPRequestHandler):
        server_version = "BalancaInteligente/1.0"

        # ------------------------------------------------------------ helpers
        def _enviar(self, status: int, corpo: bytes, tipo: str, extra=None):
            self.send_response(status)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(corpo)

        def _json(self, status: int, dados):
            self._enviar(status, json.dumps(dados, ensure_ascii=False).encode("utf-8"),
                         "application/json; charset=utf-8")

        def _erro(self, status: int, msg: str):
            self._json(status, {"erro": msg})

        def log_message(self, fmt, *args):  # log enxuto
            print("[%s] %s" % (self.log_date_time_string(), fmt % args))

        @staticmethod
        def _inteiro(qs, nome, padrao, minimo, maximo):
            try:
                v = int(qs.get(nome, [padrao])[0])
            except ValueError:
                v = padrao
            return max(minimo, min(maximo, v))

        # ------------------------------------------------------------- rotas
        def do_GET(self):
            url = urlparse(self.path)
            qs = parse_qs(url.query)
            try:
                if url.path in ("/", "/index.html"):
                    with open(os.path.join(PASTA_ESTATICA, "index.html"), "rb") as f:
                        return self._enviar(200, f.read(), "text/html; charset=utf-8")
                if url.path == "/api/pesagens":
                    limite = self._inteiro(qs, "limite", 100, 1, 1000)
                    offset = self._inteiro(qs, "offset", 0, 0, 10**9)
                    return self._json(200, servico.repo.listar(limite, offset))
                if url.path.startswith("/api/pesagens/"):
                    id_ = url.path.rsplit("/", 1)[1]
                    if not ID_RE.match(id_):
                        return self._erro(400, "id inválido")
                    reg = servico.repo.obter(id_)
                    return self._json(200, reg) if reg else self._erro(404, "pesagem não encontrada")
                if url.path == "/api/resumo":
                    return self._json(200, servico.repo.resumo())
                if url.path == "/api/exportar":
                    formato = qs.get("formato", ["json"])[0].lower()
                    registros = servico.repo.todos()
                    if formato == "csv":
                        corpo = exporters.para_csv(registros).encode("utf-8-sig")
                        return self._enviar(200, corpo, "text/csv; charset=utf-8", {
                            "Content-Disposition": 'attachment; filename="pesagens.csv"'})
                    if formato == "json":
                        corpo = exporters.para_json(registros).encode("utf-8")
                        return self._enviar(200, corpo, "application/json; charset=utf-8", {
                            "Content-Disposition": 'attachment; filename="pesagens.json"'})
                    return self._erro(400, "formato deve ser json ou csv")
                return self._erro(404, "rota não encontrada")
            except Exception as exc:  # pragma: no cover
                return self._erro(500, f"erro interno: {exc}")

        def do_POST(self):
            url = urlparse(self.path)
            qs = parse_qs(url.query)
            try:
                if url.path == "/api/pesagens":
                    return self._json(201, servico.registrar_pesagem())
                if url.path == "/api/demo":
                    n = self._inteiro(qs, "n", 20, 1, 200)
                    criados = servico.gerar_demonstracao(n)
                    return self._json(201, {"criados": len(criados)})
                return self._erro(404, "rota não encontrada")
            except LeituraInvalida as exc:
                return self._erro(422, f"leitura inválida: {exc}")
            except NotImplementedError as exc:
                return self._erro(501, str(exc))
            except Exception as exc:  # pragma: no cover
                return self._erro(500, f"erro interno: {exc}")

        def do_DELETE(self):
            if urlparse(self.path).path == "/api/demo":
                return self._json(200, {"removidos": servico.repo.limpar_demonstracao()})
            return self._erro(404, "rota não encontrada")

    return Handler


def criar_servidor(servico: BalancaInteligente, host: str = "127.0.0.1", porta: int = 8000):
    return ThreadingHTTPServer((host, porta), criar_handler(servico))
