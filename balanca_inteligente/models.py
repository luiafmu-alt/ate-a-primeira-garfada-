"""Contratos de dados do módulo.

Tudo que um outro módulo (análise/recomendações) precisa saber sobre um
registro de pesagem está definido aqui: o schema do registro e as interfaces
(Protocols) que câmera, balança e termômetro devem cumprir.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Protocol

SCHEMA_VERSAO = "1.0"

# Categorias fixas de composição do prato (estimativa visual, em % do prato).
CATEGORIAS = ("proteina", "carboidrato", "leguminosa", "vegetais", "outros")

# Valores permitidos para a origem de cada leitura.
ORIGEM_SIMULADA = "simulada"
ORIGENS_ALIMENTOS = ("camera_ia", ORIGEM_SIMULADA)
ORIGENS_PESO = ("balanca", ORIGEM_SIMULADA)
ORIGENS_TEMPERATURA = ("sensor", "camera_termica", ORIGEM_SIMULADA)


@dataclass
class LeituraCamera:
    alimentos: List[str]
    composicao_pct: Dict[str, float]  # categoria -> % (soma 100)
    origem: str  # "camera_ia" | "simulada"


@dataclass
class LeituraPeso:
    peso_g: int
    origem: str  # "balanca" | "simulada"


@dataclass
class LeituraTemperatura:
    temperatura_c: float
    origem: str  # "sensor" | "camera_termica" | "simulada"


class Camera(Protocol):
    def identificar_alimentos(self) -> LeituraCamera: ...


class Balanca(Protocol):
    def ler_peso(self) -> LeituraPeso: ...


class Termometro(Protocol):
    def ler_temperatura(self) -> LeituraTemperatura: ...


class LeituraInvalida(ValueError):
    """Leitura de sensor fora do contrato (ex.: composição que não soma 100)."""


def validar_leituras(cam: LeituraCamera, peso: LeituraPeso, temp: LeituraTemperatura) -> None:
    if not cam.alimentos:
        raise LeituraInvalida("a câmera não identificou nenhum alimento")
    if cam.origem not in ORIGENS_ALIMENTOS:
        raise LeituraInvalida(f"origem de alimentos inválida: {cam.origem!r}")
    if set(cam.composicao_pct) - set(CATEGORIAS):
        raise LeituraInvalida("composição com categoria desconhecida")
    if abs(sum(cam.composicao_pct.values()) - 100.0) > 0.5:
        raise LeituraInvalida("a composição do prato deve somar 100%")
    if peso.origem not in ORIGENS_PESO:
        raise LeituraInvalida(f"origem de peso inválida: {peso.origem!r}")
    if not 0 < peso.peso_g < 5000:
        raise LeituraInvalida(f"peso fora do intervalo plausível: {peso.peso_g} g")
    if temp.origem not in ORIGENS_TEMPERATURA:
        raise LeituraInvalida(f"origem de temperatura inválida: {temp.origem!r}")
    if not -10 <= temp.temperatura_c <= 150:
        raise LeituraInvalida(f"temperatura fora do intervalo plausível: {temp.temperatura_c} °C")
