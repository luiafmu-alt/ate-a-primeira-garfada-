"""Regra de negócio: junta câmera + balança + termômetro e grava o registro."""
from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .models import (
    ORIGEM_SIMULADA,
    SCHEMA_VERSAO,
    Balanca,
    Camera,
    Termometro,
    validar_leituras,
)
from .sensors import SimuladorBalanca, SimuladorCamera, SimuladorTermometro
from .storage import RepositorioPesagens


class BalancaInteligente:
    def __init__(self, camera: Camera, balanca: Balanca, termometro: Termometro,
                 repositorio: RepositorioPesagens):
        self.camera = camera
        self.balanca = balanca
        self.termometro = termometro
        self.repo = repositorio

    def registrar_pesagem(self, data_hora: Optional[datetime] = None,
                          demonstracao: bool = False) -> Dict:
        """Coleta as três leituras, valida, grava e devolve o registro."""
        cam = self.camera.identificar_alimentos()
        peso = self.balanca.ler_peso()
        temp = self.termometro.ler_temperatura()
        validar_leituras(cam, peso, temp)

        campos_simulados: List[str] = []
        if cam.origem == ORIGEM_SIMULADA:
            campos_simulados += ["alimentos", "composicao_pct"]
        if peso.origem == ORIGEM_SIMULADA:
            campos_simulados.append("peso_total_g")
        if temp.origem == ORIGEM_SIMULADA:
            campos_simulados.append("temperatura_c")

        momento = (data_hora or datetime.now()).replace(microsecond=0)
        registro = {
            "data_hora": momento.isoformat(),
            "atendimento_id": "ATD-" + uuid.uuid4().hex[:8].upper(),  # anônimo
            "alimentos": cam.alimentos,
            "composicao_pct": cam.composicao_pct,
            "peso_total_g": peso.peso_g,
            "temperatura_c": temp.temperatura_c,
            "origem_alimentos": cam.origem,
            "origem_peso": peso.origem,
            "origem_temperatura": temp.origem,
            "dados_simulados": bool(campos_simulados),
            "campos_simulados": campos_simulados,
            "demonstracao": demonstracao,
            "schema_versao": SCHEMA_VERSAO,
        }
        return self.repo.adicionar(registro)

    def gerar_demonstracao(self, quantidade: int = 20, horas: int = 4) -> List[Dict]:
        """Cria pesagens fictícias (marcadas demonstracao=true) espalhadas nas últimas horas."""
        agora = datetime.now()
        rng = random.Random()
        instantes = sorted(agora - timedelta(seconds=rng.randint(0, horas * 3600))
                           for _ in range(quantidade))
        return [self.registrar_pesagem(data_hora=t, demonstracao=True) for t in instantes]


def criar_servico(caminho_db: str = "data/pesagens.db", seed: Optional[int] = None,
                  camera: Optional[Camera] = None, balanca: Optional[Balanca] = None,
                  termometro: Optional[Termometro] = None) -> BalancaInteligente:
    """Fábrica padrão. Sem argumentos de hardware, usa os simuladores.

    Para hardware real, passe suas implementações em camera/balanca/termometro.
    """
    rng = random.Random(seed)
    return BalancaInteligente(
        camera or SimuladorCamera(rng),
        balanca or SimuladorBalanca(rng),
        termometro or SimuladorTermometro(rng),
        RepositorioPesagens(caminho_db),
    )
