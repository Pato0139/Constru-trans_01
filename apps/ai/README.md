# Módulo de Inteligencia Artificial de Constru-Trans

## Estructura

```
apps/ai/
├── __init__.py          # Archivo principal del módulo
├── README.md            # Este archivo
├── django/              # Integración con Django (ERP)
│   └── ia/              # App Django de IA (original)
│       ├── migrations/
│       ├── services/
│       ├── templates/
│       ├── forms/
│       ├── views/
│       ├── tests/
│       ├── models.py
│       ├── admin.py
│       ├── apps.py
│       ├── urls.py
│       └── setup_ollama.py
├── infra/               # Infraestructura Docker Compose
│   └── docker-compose.yml
└── service/             # Servicio FastAPI independiente
    ├── app/
    │   ├── agents/
    │   ├── api/
    │   ├── core/
    │   ├── db/
    │   ├── llm/
    │   ├── memory/
    │   ├── rag/
    │   ├── schemas/
    │   ├── services/
    │   ├── tests/
    │   ├── tools/
    │   └── main.py
    ├── training/        # Scripts de entrenamiento (LoRA, QLoRA)
    │   ├── datasets/
    │   ├── train_lora.py
    │   └── train_qlora.py
    ├── .env
    ├── .env.example
    ├── requirements.txt
    └── Dockerfile
```

## Descripción

- **django/**: Contiene la app Django original, integrada con el ERP de Constru-Trans.
- **infra/**: Infraestructura Docker Compose para ejecutar el servicio de IA completo
  (PostgreSQL, Redis, ChromaDB, FastAPI).
- **service/**: Nuevo servicio FastAPI con arquitectura limpia, preparado para escalar.
  - Proveedores LLM intercambiables (Ollama, OpenAI-compatible)
  - Memoria semántica (ChromaDB)
  - Sistema de herramientas (Tool Registry)
  - Preparado para JWT y seguridad empresarial

## Uso

Para más detalles, revisa los READMEs de cada subcarpeta.
