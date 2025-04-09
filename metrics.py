from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import os
from dotenv import load_dotenv
import time

# Carica le variabili d'ambiente dal file .env
load_dotenv()

class MetricsManager:
    def __init__(self):
        # Ottieni le variabili d'ambiente
        self.influxdb_url = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
        self.influxdb_token = os.getenv('INFLUXDB_TOKEN')
        self.influxdb_org = os.getenv('INFLUXDB_ORG')
        self.influxdb_bucket = os.getenv('INFLUXDB_BUCKET')

        # Verifica che tutte le variabili d'ambiente siano presenti
        if not all([self.influxdb_url, self.influxdb_token, self.influxdb_org, self.influxdb_bucket]):
            raise ValueError("Mancano alcune variabili d'ambiente necessarie per InfluxDB. Verifica il file .env")

        # Assicurati che l'URL sia correttamente formattato
        if not self.influxdb_url.startswith(('http://', 'https://')):
            self.influxdb_url = 'http://' + self.influxdb_url

        try:
            self.client = InfluxDBClient(
                url=self.influxdb_url,
                token=self.influxdb_token,
                org=self.influxdb_org,
                verify_ssl=False  # Disabilita la verifica SSL per localhost
            )
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.bucket = self.influxdb_bucket
        except Exception as e:
            print(f"Errore nella connessione a InfluxDB: {str(e)}")
            self.client = None
            self.write_api = None
            self.bucket = None

    def track_active_users(self, count: int):
        """Traccia il numero di utenti attivi"""
        if not self.write_api:
            print("InfluxDB non è disponibile. Impossibile tracciare gli utenti attivi.")
            return

        try:
            point = Point("active_users") \
                .field("count", count) \
                .time(time.time_ns())
            
            self.write_api.write(bucket=self.bucket, record=point)
        except Exception as e:
            print(f"Errore nel tracciamento degli utenti attivi: {str(e)}")

    def track_response_time(self, response_time: float, operation: str):
        """Traccia il tempo di risposta per diverse operazioni"""
        if not self.write_api:
            print("InfluxDB non è disponibile. Impossibile tracciare il tempo di risposta.")
            return

        try:
            point = Point("response_times") \
                .field("duration", response_time) \
                .tag("operation", operation) \
                .time(time.time_ns())
            
            self.write_api.write(bucket=self.bucket, record=point)
        except Exception as e:
            print(f"Errore nel tracciamento del tempo di risposta: {str(e)}")

    def close(self):
        """Chiude la connessione con InfluxDB"""
        self.client.close() 