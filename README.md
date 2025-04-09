# Ollama Project

Questo progetto implementa un sistema di QA (Question Answering) basato su documenti PDF utilizzando LangChain e Ollama.

## Requisiti

- Docker
- Python 3.11+
- Accesso a InfluxDB
- Accesso a ChromaDB

## Configurazione

1. Crea un file `.env` con le seguenti variabili:
```
INFLUXDB_URL=http://192.168.200.111:8086
INFLUXDB_TOKEN=your_token
INFLUXDB_ORG=infobasic
INFLUXDB_BUCKET=delprincipe

# Configurazioni Chroma
CHROMA_SERVER_HOST=192.168.200.20
CHROMA_SERVER_PORT=8000
```

## Esecuzione con Docker

```bash
# Pull dell'immagine
docker pull delprincp3/ollama_project:1.0.0

# Esecuzione del container
docker run -p 7860:7860 --env-file .env delprincp3/ollama_project:1.0.0
```

L'applicazione sarà disponibile all'indirizzo: http://localhost:7860

## Sviluppo

Per lo sviluppo locale:

1. Crea un ambiente virtuale:
```bash
python -m venv venv
source venv/bin/activate  # Su Windows: venv\Scripts\activate
```

2. Installa le dipendenze:
```bash
pip install -r requirements.txt
```

3. Esegui l'applicazione:
```bash
python testpdf.py
```

## GitHub Actions

Il progetto include un workflow di GitHub Actions che:
- Costruisce automaticamente l'immagine Docker
- Supporta le architetture amd64 e arm64
- Pusha l'immagine su Docker Hub

Per utilizzare il workflow, configura i seguenti secrets nel tuo repository GitHub:
- `DOCKER_USERNAME`
- `DOCKER_PASSWORD`
