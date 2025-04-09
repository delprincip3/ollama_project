# Usa un'immagine base più sicura e leggera
FROM python:3.11-slim

# Imposta variabili d'ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Crea un utente non root
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Crea la directory dell'applicazione
WORKDIR /app

# Copia i file necessari
COPY requirements.txt .

# Installa le dipendenze
RUN pip install --no-cache-dir -r requirements.txt && \
    # Pulisci la cache di pip
    rm -rf /root/.cache/pip/*

# Copia il codice dell'applicazione
COPY . .

# Imposta i permessi corretti
RUN chown -R appuser:appuser /app && \
    chmod -R 755 /app

# Cambia utente
USER appuser

# Esponi la porta
EXPOSE 7860

# Comando di avvio
CMD ["python", "testpdf.py"] 