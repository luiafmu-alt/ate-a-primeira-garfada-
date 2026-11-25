#!/usr/bin/env python3
"""Inicia o módulo Balança Inteligente: python3 run.py [--porta 8000] [--db data/pesagens.db]"""
import argparse

from balanca_inteligente import criar_servico
from balanca_inteligente.server import criar_servidor


def main():
    ap = argparse.ArgumentParser(description="Até a primeira Garfada — Balança Inteligente")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--porta", type=int, default=8000)
    ap.add_argument("--db", default="data/pesagens.db")
    ap.add_argument("--seed", type=int, default=None, help="semente do simulador (reprodutível)")
    args = ap.parse_args()

    servico = criar_servico(args.db, seed=args.seed)
    servidor = criar_servidor(servico, args.host, args.porta)
    print(f"Balança Inteligente (MODO SIMULAÇÃO) em http://{args.host}:{args.porta}  |  banco: {args.db}")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrado.")


if __name__ == "__main__":
    main()
