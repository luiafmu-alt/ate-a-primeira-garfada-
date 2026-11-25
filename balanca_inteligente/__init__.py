"""Módulo Balança Inteligente — projeto "Até a primeira Garfada" (Bovinu'S).

Uso rápido como biblioteca (para integrar ao sistema principal):

    from balanca_inteligente import criar_servico
    servico = criar_servico("data/pesagens.db")
    registro = servico.registrar_pesagem()
"""
from .service import BalancaInteligente, criar_servico

__all__ = ["BalancaInteligente", "criar_servico"]
