"""Fontes de leitura: simuladores (funcionam hoje) e stubs de hardware real.

Nada aqui mede algo de verdade. Os simuladores existem para demonstrar o
fluxo completo; toda leitura deles sai com origem = "simulada". Para ligar
equipamentos físicos, implemente as classes *Real* no final do arquivo (ou
escreva outras que cumpram os Protocols de models.py) e injete-as em
`criar_servico`.
"""
from __future__ import annotations

import random
from typing import Dict, List, Optional

from .models import (
    CATEGORIAS,
    ORIGEM_SIMULADA,
    LeituraCamera,
    LeituraPeso,
    LeituraTemperatura,
)

# Catálogo de alimentos reconhecíveis (id sem acento -> categoria).
CATALOGO: Dict[str, str] = {
    "carne": "proteina",
    "frango": "proteina",
    "linguica": "proteina",
    "peixe": "proteina",
    "ovo": "proteina",
    "arroz": "carboidrato",
    "macarrao": "carboidrato",
    "batata": "carboidrato",
    "mandioca": "carboidrato",
    "farofa": "carboidrato",
    "feijao": "leguminosa",
    "lentilha": "leguminosa",
    "salada": "vegetais",
    "couve": "vegetais",
    "legumes": "vegetais",
    "tomate": "vegetais",
    "molho": "outros",
    "queijo": "outros",
}


def _por_categoria(cat: str) -> List[str]:
    return [a for a, c in CATALOGO.items() if c == cat]


def _arredondar_para_100(valores: Dict[str, float]) -> Dict[str, float]:
    """Arredonda em 1 casa e ajusta a maior categoria para a soma ser 100,0."""
    arred = {k: round(v, 1) for k, v in valores.items()}
    diff = round(100.0 - sum(arred.values()), 1)
    if diff and arred:
        maior = max(arred, key=arred.get)
        arred[maior] = round(arred[maior] + diff, 1)
    return arred


class SimuladorCamera:
    """Simula a identificação visual de alimentos por IA."""

    def __init__(self, rng: Optional[random.Random] = None):
        self.rng = rng or random.Random()

    def identificar_alimentos(self) -> LeituraCamera:
        r = self.rng
        escolhidos: List[str] = [r.choice(_por_categoria("carboidrato"))]
        if r.random() < 0.75:
            escolhidos.append(r.choice(_por_categoria("leguminosa")))
        escolhidos += r.sample(_por_categoria("proteina"), k=r.choice([1, 1, 2]))
        if r.random() < 0.65:
            escolhidos += r.sample(_por_categoria("vegetais"), k=r.choice([1, 2]))
        if r.random() < 0.25:
            escolhidos.append(r.choice(_por_categoria("outros")))

        # Porção relativa de cada alimento (apenas para compor o prato simulado).
        porcoes = {a: r.uniform(0.5, 1.5) for a in escolhidos}
        total = sum(porcoes.values())
        comp = {c: 0.0 for c in CATEGORIAS}
        for alimento, p in porcoes.items():
            comp[CATALOGO[alimento]] += 100.0 * p / total
        comp = _arredondar_para_100({c: v for c, v in comp.items() if v > 0})
        return LeituraCamera(alimentos=escolhidos, composicao_pct=comp, origem=ORIGEM_SIMULADA)


class SimuladorBalanca:
    """Simula a leitura de peso total do prato, em gramas."""

    def __init__(self, rng: Optional[random.Random] = None):
        self.rng = rng or random.Random()

    def ler_peso(self) -> LeituraPeso:
        peso = int(round(min(800, max(220, self.rng.gauss(450, 90)))))
        return LeituraPeso(peso_g=peso, origem=ORIGEM_SIMULADA)


class SimuladorTermometro:
    """Simula a temperatura do prato, em °C."""

    def __init__(self, rng: Optional[random.Random] = None):
        self.rng = rng or random.Random()

    def ler_temperatura(self) -> LeituraTemperatura:
        t = min(72.0, max(28.0, self.rng.gauss(48.0, 8.0)))
        return LeituraTemperatura(temperatura_c=round(t, 1), origem=ORIGEM_SIMULADA)


# ---------------------------------------------------------------------------
# Pontos de integração com hardware real (ainda NÃO implementados).
# ---------------------------------------------------------------------------
class CameraIAReal:
    """Deve capturar uma imagem do prato e chamar um modelo de visão
    (classificação/segmentação) retornando LeituraCamera(origem="camera_ia")."""

    def identificar_alimentos(self) -> LeituraCamera:
        raise NotImplementedError("Integração com câmera + modelo de visão ainda não feita")


class BalancaReal:
    """Deve ler a balança (serial/USB/Bluetooth/HTTP do fabricante) e retornar
    LeituraPeso(origem="balanca"), já descontada a tara do prato/bandeja."""

    def ler_peso(self) -> LeituraPeso:
        raise NotImplementedError("Integração com a balança ainda não feita")


class SensorTemperaturaReal:
    """Deve ler um sensor infravermelho ou câmera térmica e retornar
    LeituraTemperatura(origem="sensor" ou "camera_termica")."""

    def ler_temperatura(self) -> LeituraTemperatura:
        raise NotImplementedError("Integração com sensor de temperatura ainda não feita")
