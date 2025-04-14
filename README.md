# Ollama Project - Chatbot Documentale con Gestione Utenti

Un'applicazione web che permette di caricare documenti PDF e interagire con essi attraverso un'interfaccia chat, utilizzando modelli di linguaggio locale tramite Ollama.

## 🚀 Funzionalità

- **Gestione Utenti**: Sistema di login con timeout automatico
- **Caricamento PDF**: Supporto per documenti PDF fino a 10MB
- **Chat Interattiva**: Interfaccia per fare domande sui documenti caricati
- **Monitoraggio**: Integrazione con InfluxDB per il tracciamento delle metriche
- **Database Vettoriale**: Utilizzo di ChromaDB per l'indicizzazione dei documenti
- **Multi-architettura**: Supporto per sistemi ARM64 e AMD64

## 🛠️ Prerequisiti

- Docker
- Ollama (con modello Mistral)
- InfluxDB (opzionale, per le metriche)
- ChromaDB (opzionale, per il database vettoriale)

## 📦 Installazione

1. Clona il repository:
```bash
git clone https://github.com/delprincip3/ollama_project.git
cd ollama_project
```

2. Crea il file `.env` basandoti su `.env.example`:
```bash
cp .env.example .env
```

3. Modifica il file `.env` con le tue configurazioni:
```env
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your_influxdb_token_here
INFLUXDB_ORG=your_organization
INFLUXDB_BUCKET=your_bucket

CHROMA_SERVER_HOST=localhost
CHROMA_SERVER_PORT=8000
```

4. Avvia il container Docker:
```bash
docker run -p 7860:7860 --env-file .env delprincp3/ollama_project:1.0.0
```

## 🌐 Utilizzo

1. Apri il browser e vai a `http://localhost:7860`
2. Effettua il login con un nome utente
3. Carica un documento PDF
4. Inizia a fare domande sul documento

## 🔧 Configurazione

### Variabili d'Ambiente

- `INFLUXDB_URL`: URL del server InfluxDB
- `INFLUXDB_TOKEN`: Token di accesso InfluxDB
- `INFLUXDB_ORG`: Organizzazione InfluxDB
- `INFLUXDB_BUCKET`: Bucket InfluxDB
- `CHROMA_SERVER_HOST`: Host del server ChromaDB
- `CHROMA_SERVER_PORT`: Porta del server ChromaDB

### Timeout e Limiti

- Timeout sessione: 10 minuti
- Dimensione massima PDF: 10MB
- Numero massimo utenti contemporanei: 2

## 🐳 Docker

L'immagine Docker è disponibile su Docker Hub:
```bash
docker pull delprincp3/ollama_project:1.0.0
```

### Build Locale

Per costruire l'immagine localmente:
```bash
docker build -t ollama_project:local .
```

## 📊 Metriche

L'applicazione traccia automaticamente:
- Numero di utenti attivi
- Tempi di risposta delle query
- Errori e eccezioni

## 🤝 Contribuire

1. Fork il repository
2. Crea un branch per la tua feature (`git checkout -b feature/AmazingFeature`)
3. Commit le tue modifiche (`git commit -m 'Add some AmazingFeature'`)
4. Push sul branch (`git push origin feature/AmazingFeature`)
5. Apri una Pull Request

## 📝 Licenza

Questo progetto è distribuito con licenza MIT. Vedi il file `LICENSE` per maggiori dettagli.

## 🙏 Ringraziamenti

- [Ollama](https://ollama.ai/) per i modelli di linguaggio locale
- [LangChain](https://www.langchain.com/) per il framework di LLM
- [Gradio](https://gradio.app/) per l'interfaccia web
- [InfluxDB](https://www.influxdata.com/) per il monitoraggio
- [ChromaDB](https://www.trychroma.com/) per il database vettoriale
