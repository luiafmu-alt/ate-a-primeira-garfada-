# Até a primeira Garfada · Módulo Balança Inteligente

Protótipo funcional da coleta de dados do prato (restaurante Bovinu'S): ao pesar o prato, o sistema registra alimentos, composição, peso, temperatura, horário e um ID único, e guarda tudo para análise posterior.

> **MODO SIMULAÇÃO.** Não há câmera, balança nem sensor conectados. Todas as leituras vêm de simuladores e saem marcadas como `"simulada"` em cada registro e na interface.

## Como rodar

```bash
python3 run.py                 # http://127.0.0.1:8000
python3 run.py --porta 9000 --db data/pesagens.db --seed 1
python3 -m unittest discover -s tests -v
```

Requer apenas Python 3.9+ (sem pip, sem dependências). Na tela: **Pesar prato**, histórico, indicadores, exportar CSV/JSON, gerar/apagar dados de demonstração para o pitch.

## Estrutura

```
balanca_inteligente/
  models.py     contrato: schema, categorias, interfaces Camera/Balanca/Termometro, validação
  sensors.py    simuladores + stubs de hardware real (CameraIAReal, BalancaReal, SensorTemperaturaReal)
  storage.py    SQLite (arquivo único), IDs sequenciais PESAGEM_001...
  service.py    regra de negócio: coleta, valida, marca o que é simulado, grava
  exporters.py  CSV e JSON
  server.py     API HTTP + serve a interface
  static/index.html  interface
run.py · tests/
```

## Registro de uma pesagem

```json
{
  "id": "PESAGEM_001",
  "data_hora": "2026-11-25T12:30:00",
  "atendimento_id": "ATD-C285243D",
  "alimentos": ["macarrao", "feijao", "ovo", "salada"],
  "composicao_pct": {"proteina": 17.6, "carboidrato": 24.7, "leguminosa": 26.7, "vegetais": 31.0},
  "peso_total_g": 340,
  "temperatura_c": 45.4,
  "origem_alimentos": "simulada",
  "origem_peso": "simulada",
  "origem_temperatura": "simulada",
  "dados_simulados": true,
  "campos_simulados": ["alimentos", "composicao_pct", "peso_total_g", "temperatura_c"],
  "demonstracao": false,
  "schema_versao": "1.0"
}
```

Inclui todos os campos do exemplo combinado (`id`, `data_hora`, `alimentos`, `peso_total_g`, `temperatura_c`, `origem_temperatura`, `dados_simulados`) mais os pedidos no briefing (cliente anônimo, composição por categoria, origem de cada dado).

- **Anonimato:** `atendimento_id` é aleatório; nenhum dado pessoal é coletado.
- **Origens permitidas:** alimentos `camera_ia|simulada`, peso `balanca|simulada`, temperatura `sensor|camera_termica|simulada`.
- **`demonstracao`:** `true` nos registros criados pelo botão de demonstração (apagáveis sem tocar nos demais).
- **Categorias:** proteina, carboidrato, leguminosa, vegetais, outros (soma 100%).
- **Armazenamento:** SQLite em `data/pesagens.db`; o JSON completo fica na coluna `payload`. IDs nunca são reutilizados.

## API

| Método | Rota | Função |
|---|---|---|
| POST | `/api/pesagens` | registra nova pesagem |
| GET | `/api/pesagens?limite=&offset=` | histórico (mais recentes primeiro) |
| GET | `/api/pesagens/<id>` | detalhe |
| GET | `/api/resumo` | total, peso médio, temperatura média, min/max, alimentos mais frequentes |
| GET | `/api/exportar?formato=csv\|json` | exportação |
| POST / DELETE | `/api/demo` | gera / apaga dados de demonstração |

## Integração com o sistema principal

Este repositório estava vazio, então não havia stack a seguir; usei só a biblioteca padrão para não conflitar com nada. Opções, da mais simples à mais profunda:

1. **Ler os dados:** o outro módulo consome `/api/exportar?formato=json`, a API, ou abre `pesagens.db` (tabela `pesagens`, coluna `payload`).
2. **Usar como biblioteca:** `from balanca_inteligente import criar_servico` e chamar `registrar_pesagem()` / `repo.todos()` / `repo.resumo()`.
3. **Adaptar ao framework do projeto:** a lógica está em `service.py` e `storage.py`, sem dependência de HTTP. Basta criar rotas Flask/FastAPI/Express que chamem esses métodos (ou trocar `storage.py` por Postgres/Firebase mantendo os mesmos métodos).

Para o tempo "entrada → primeira garfada": ligue `atendimento_id` aos eventos de entrada e de primeira garfada do outro módulo.

## O que falta para conectar equipamento físico

- **Balança:** implementar `BalancaReal.ler_peso()` conforme o protocolo do modelo (serial/USB/Bluetooth/HTTP), com **tara** do prato.
- **Câmera + IA:** implementar `CameraIAReal.identificar_alimentos()`: capturar a imagem e usar um modelo de visão treinado nos pratos do Bovinu'S (ou API de visão) que devolva alimentos e proporção por categoria. A composição por área é estimativa visual, não medida.
- **Temperatura:** uma câmera comum **não mede temperatura**. Use sensor infravermelho ou câmera térmica em `SensorTemperaturaReal`, calibrado, e registre `origem_temperatura` como `sensor` ou `camera_termica`.
- **Disparo:** hoje o botão inicia a pesagem; com hardware, o evento "prato posicionado/peso estável" deve disparar a coleta.
- **Operação:** autenticação na API, backup do banco, sincronismo de relógio e aviso/política de privacidade se houver imagens de clientes.
- Passar as implementações em `criar_servico(camera=..., balanca=..., termometro=...)`; o resto não muda.
