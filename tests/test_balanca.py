import csv
import io
import json
import os
import sys
import threading
import unittest
import urllib.request
from urllib.error import HTTPError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from balanca_inteligente import criar_servico  # noqa: E402
from balanca_inteligente import exporters  # noqa: E402
from balanca_inteligente.models import CATEGORIAS, LeituraCamera, LeituraInvalida, validar_leituras  # noqa: E402
from balanca_inteligente.models import LeituraPeso, LeituraTemperatura  # noqa: E402
from balanca_inteligente.server import criar_servidor  # noqa: E402

CAMPOS_OBRIGATORIOS = {
    "id", "data_hora", "atendimento_id", "alimentos", "composicao_pct", "peso_total_g",
    "temperatura_c", "origem_alimentos", "origem_peso", "origem_temperatura",
    "dados_simulados", "campos_simulados", "demonstracao", "schema_versao",
}


class TestServico(unittest.TestCase):
    def setUp(self):
        self.s = criar_servico(":memory:", seed=42)

    def test_registro_tem_schema_completo_e_marca_simulado(self):
        r = self.s.registrar_pesagem()
        self.assertTrue(CAMPOS_OBRIGATORIOS <= set(r))
        self.assertEqual(r["id"], "PESAGEM_001")
        self.assertTrue(r["dados_simulados"])
        self.assertEqual(r["origem_temperatura"], "simulada")
        self.assertEqual(set(r["campos_simulados"]), {"alimentos", "composicao_pct", "peso_total_g", "temperatura_c"})
        self.assertTrue(r["atendimento_id"].startswith("ATD-"))
        self.assertFalse(r["demonstracao"])

    def test_composicao_soma_100_e_categorias_validas(self):
        for _ in range(200):
            r = self.s.registrar_pesagem()
            self.assertAlmostEqual(sum(r["composicao_pct"].values()), 100.0, delta=0.11)
            self.assertTrue(set(r["composicao_pct"]) <= set(CATEGORIAS))
            self.assertTrue(220 <= r["peso_total_g"] <= 800)
            self.assertTrue(28 <= r["temperatura_c"] <= 72)

    def test_ids_sequenciais_unicos_e_nao_reutilizados(self):
        ids = [self.s.registrar_pesagem()["id"] for _ in range(3)]
        self.assertEqual(ids, ["PESAGEM_001", "PESAGEM_002", "PESAGEM_003"])
        self.s.gerar_demonstracao(2)
        self.s.repo.limpar_demonstracao()
        self.assertEqual(self.s.registrar_pesagem()["id"], "PESAGEM_006")

    def test_demonstracao_marcada_e_limpeza_preserva_reais(self):
        self.s.registrar_pesagem()
        demos = self.s.gerar_demonstracao(5)
        self.assertTrue(all(d["demonstracao"] for d in demos))
        self.assertEqual(self.s.repo.limpar_demonstracao(), 5)
        self.assertEqual(self.s.repo.resumo()["total_pesagens"], 1)

    def test_resumo(self):
        vazio = self.s.repo.resumo()
        self.assertEqual(vazio["total_pesagens"], 0)
        self.assertIsNone(vazio["peso_medio_g"])
        regs = [self.s.registrar_pesagem() for _ in range(10)]
        res = self.s.repo.resumo()
        self.assertEqual(res["total_pesagens"], 10)
        self.assertAlmostEqual(res["peso_medio_g"], sum(r["peso_total_g"] for r in regs) / 10, delta=0.06)
        self.assertEqual(res["registros_simulados"], 10)

    def test_leitura_invalida_e_rejeitada(self):
        ok_c = LeituraCamera(["arroz"], {"carboidrato": 100.0}, "simulada")
        ok_p = LeituraPeso(400, "simulada")
        ok_t = LeituraTemperatura(40.0, "simulada")
        validar_leituras(ok_c, ok_p, ok_t)
        with self.assertRaises(LeituraInvalida):
            validar_leituras(LeituraCamera(["arroz"], {"carboidrato": 60.0}, "simulada"), ok_p, ok_t)
        with self.assertRaises(LeituraInvalida):
            validar_leituras(ok_c, LeituraPeso(-5, "simulada"), ok_t)
        with self.assertRaises(LeituraInvalida):
            validar_leituras(ok_c, ok_p, LeituraTemperatura(40.0, "termometro_inventado"))

    def test_hardware_real_nao_implementado_falha_com_clareza(self):
        from balanca_inteligente.sensors import BalancaReal
        s = criar_servico(":memory:", balanca=BalancaReal())
        with self.assertRaises(NotImplementedError):
            s.registrar_pesagem()


class TestExport(unittest.TestCase):
    def test_csv_e_json(self):
        s = criar_servico(":memory:", seed=1)
        for _ in range(3):
            s.registrar_pesagem()
        regs = s.repo.todos()
        linhas = list(csv.DictReader(io.StringIO(exporters.para_csv(regs))))
        self.assertEqual(len(linhas), 3)
        self.assertEqual(list(linhas[0].keys()), exporters.COLUNAS_CSV)
        self.assertIn("pct_proteina", linhas[0])
        self.assertEqual(json.loads(exporters.para_json(regs)), regs)


class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.servico = criar_servico(":memory:", seed=7)
        cls.srv = criar_servidor(cls.servico, "127.0.0.1", 0)
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def req(self, caminho, metodo="GET"):
        rq = urllib.request.Request(self.base + caminho, method=metodo)
        with urllib.request.urlopen(rq) as r:
            return r.status, r.headers, r.read()

    def test_fluxo_completo(self):
        st, _, corpo = self.req("/api/pesagens", "POST")
        self.assertEqual(st, 201)
        reg = json.loads(corpo)
        st, _, corpo = self.req(f"/api/pesagens/{reg['id']}")
        self.assertEqual(json.loads(corpo)["id"], reg["id"])
        st, _, corpo = self.req("/api/pesagens")
        self.assertTrue(any(r["id"] == reg["id"] for r in json.loads(corpo)))
        st, _, corpo = self.req("/api/resumo")
        self.assertGreaterEqual(json.loads(corpo)["total_pesagens"], 1)
        st, h, corpo = self.req("/api/exportar?formato=csv")
        self.assertIn("text/csv", h["Content-Type"])
        self.assertIn(reg["id"], corpo.decode("utf-8-sig"))
        st, h, corpo = self.req("/api/exportar?formato=json")
        self.assertIsInstance(json.loads(corpo), list)
        st, h, corpo = self.req("/")
        self.assertIn("Até a primeira Garfada", corpo.decode("utf-8"))

    def test_erros(self):
        for caminho, codigo in [("/api/pesagens/XYZ", 400), ("/api/pesagens/PESAGEM_999999", 404),
                                ("/api/exportar?formato=xml", 400), ("/nao-existe", 404)]:
            with self.assertRaises(HTTPError) as ctx:
                self.req(caminho)
            self.assertEqual(ctx.exception.code, codigo, caminho)

    def test_demo_via_api(self):
        st, _, corpo = self.req("/api/demo?n=3", "POST")
        self.assertEqual(json.loads(corpo)["criados"], 3)
        st, _, corpo = self.req("/api/demo", "DELETE")
        self.assertGreaterEqual(json.loads(corpo)["removidos"], 3)


if __name__ == "__main__":
    unittest.main()
