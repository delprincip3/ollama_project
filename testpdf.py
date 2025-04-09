from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaLLM
from langchain_ollama import OllamaEmbeddings
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
import gradio as gr
import os
import tempfile
import time
import threading
import glob
import json
from datetime import datetime, timedelta
from pathlib import Path
import re
from typing import Optional
from metrics import MetricsManager
from chromadb.config import Settings

class UserManager:
    def __init__(self):
        self.active_users = {}
        self.max_users = 2
        self.session_time = 600  # 10 minuti in secondi
        self.users_file = "active_users.json"
        self.metrics = MetricsManager()  # Inizializza metrics prima di load_users
        self.load_users()

    def load_users(self):
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r') as f:
                    self.active_users = json.load(f)
                    # Aggiorna le metriche degli utenti attivi
                    self.metrics.track_active_users(len(self.active_users))
        except Exception as e:
            print(f"Errore nel caricamento degli utenti: {str(e)}")
            self.active_users = {}
            self.metrics.track_active_users(0)

    def save_users(self):
        try:
            with open(self.users_file, 'w') as f:
                json.dump(self.active_users, f)
        except Exception as e:
            print(f"Errore nel salvataggio degli utenti: {str(e)}")

    def add_user(self, username):
        start_time = time.time()
        current_time = time.time()
        # Rimuovi utenti scaduti
        self.active_users = {k: v for k, v in self.active_users.items() 
                           if current_time - v['login_time'] < self.session_time}
        
        if len(self.active_users) >= self.max_users:
            self.metrics.track_response_time(time.time() - start_time, "add_user_failed")
            return False, "Numero massimo di utenti raggiunto. Riprova più tardi."
        
        if username in self.active_users:
            self.metrics.track_response_time(time.time() - start_time, "add_user_failed")
            return False, "Utente già connesso."
        
        self.active_users[username] = {
            'login_time': current_time,
            'last_activity': current_time
        }
        self.save_users()
        self.metrics.track_active_users(len(self.active_users))
        self.metrics.track_response_time(time.time() - start_time, "add_user_success")
        return True, "Accesso effettuato con successo!"

    def update_activity(self, username):
        if username in self.active_users:
            self.active_users[username]['last_activity'] = time.time()
            self.save_users()
            return True
        return False

    def get_remaining_time(self, username):
        if username in self.active_users:
            elapsed = time.time() - self.active_users[username]['login_time']
            remaining = self.session_time - elapsed
            return max(0, remaining)
        return 0

    def remove_user(self, username):
        if username in self.active_users:
            del self.active_users[username]
            self.save_users()

class DocumentQA:
    def __init__(self):
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        self.qa_system = None
        self.pdf_path = None
        self.current_db = None
        self.last_activity = time.time()
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        self.user_manager = UserManager()
        self.current_user = None
        self.max_file_size = 10 * 1024 * 1024  # 10MB limite
        self.allowed_extensions = {'.pdf'}
        self.sanitize_pattern = re.compile(r'[^a-zA-Z0-9-_\.]')
        self.metrics = MetricsManager()  # Aggiungo l'istanza di MetricsManager

    def _cleanup_loop(self):
        """Loop di pulizia che controlla e rimuove i database inattivi"""
        while True:
            try:
                current_time = time.time()
                # Cerca tutti i database vettoriali
                for db_path in glob.glob("dbv_*"):
                    # Ottieni il timestamp di ultima modifica
                    last_modified = os.path.getmtime(db_path)
                    # Se il database non è stato usato negli ultimi 10 minuti
                    if current_time - last_modified > 600:  # 600 secondi = 10 minuti
                        print(f"🗑️ Rimozione database inattivo: {db_path}")
                        import shutil
                        shutil.rmtree(db_path)
            except Exception as e:
                print(f"Errore nella pulizia: {str(e)}")
            time.sleep(60)  # Controlla ogni minuto

    def _get_db_name(self, pdf_name):
        """Genera un nome univoco per il database basato sul nome del PDF e dell'utente"""
        base_name = os.path.splitext(os.path.basename(pdf_name))[0][:6]
        return f"dbv_{self.current_user}_{base_name}"

    def login(self, username):
        if not username:
            return False, "Inserisci un nome utente valido."
        
        # Controllo parola segreta
        if username == "qwer":
            # Rimuovi tutti gli utenti attivi
            for user in list(self.user_manager.active_users.keys()):
                self.user_manager.remove_user(user)
                # Rimuovi anche i database vettoriali associati
                for db_path in glob.glob(f"dbv_{user}_*"):
                    try:
                        import shutil
                        shutil.rmtree(db_path)
                    except Exception as e:
                        print(f"Errore nella rimozione del database {db_path}: {str(e)}")
            return True, "Parola segreta rilevata. Tutti gli utenti sono stati disconnessi. La pagina si ricaricherà automaticamente."
        
        success, message = self.user_manager.add_user(username)
        if success:
            self.current_user = username
            return True, message
        return False, message

    def check_session(self):
        if not self.current_user:
            return False, "Sessione non valida. Effettua il login."
        
        remaining_time = self.user_manager.get_remaining_time(self.current_user)
        if remaining_time <= 0:
            self.user_manager.remove_user(self.current_user)
            self.current_user = None
            return False, "Sessione scaduta. Effettua nuovamente il login."
        
        self.user_manager.update_activity(self.current_user)
        return True, f"Tempo rimanente: {int(remaining_time)} secondi"

    def sanitize_filename(self, filename: str) -> str:
        """Sanitizza il nome del file per prevenire path traversal"""
        return self.sanitize_pattern.sub('', filename)

    def validate_file(self, file_path: str) -> bool:
        """Valida il file prima del caricamento"""
        try:
            # Verifica l'estensione
            if not Path(file_path).suffix.lower() in self.allowed_extensions:
                return False
            
            # Verifica la dimensione
            if os.path.getsize(file_path) > self.max_file_size:
                return False
            
            # Verifica che il file sia effettivamente un PDF
            with open(file_path, 'rb') as f:
                header = f.read(4)
                if header != b'%PDF':
                    return False
            
            return True
        except Exception:
            return False

    def carica_pdf(self, file):
        if not self.current_user:
            return "Effettua il login prima di caricare un PDF."
        
        success, message = self.check_session()
        if not success:
            return message

        try:
            print("\n=== Inizio caricamento PDF ===")
            if file is None:
                print("❌ Nessun file selezionato")
                return "Per favore, seleziona un file PDF."
            
            # Sanitizza il nome del file
            safe_filename = self.sanitize_filename(file.name)
            print(f"📄 File ricevuto: {safe_filename}")
            
            # Crea un file temporaneo sicuro
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                print(f"📝 Percorso file temporaneo: {tmp_file.name}")
                
                # Leggi e scrivi il file in chunks per gestire file grandi
                chunk_size = 8192
                total_size = 0
                
                if hasattr(file, 'read'):
                    while True:
                        chunk = file.read(chunk_size)
                        if not chunk:
                            break
                        total_size += len(chunk)
                        if total_size > self.max_file_size:
                            os.unlink(tmp_file.name)
                            return "File troppo grande. Dimensione massima consentita: 10MB"
                        tmp_file.write(chunk)
                else:
                    with open(file.name, 'rb') as f:
                        while True:
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            total_size += len(chunk)
                            if total_size > self.max_file_size:
                                os.unlink(tmp_file.name)
                                return "File troppo grande. Dimensione massima consentita: 10MB"
                            tmp_file.write(chunk)
                
                self.pdf_path = tmp_file.name

            # Valida il file
            if not self.validate_file(self.pdf_path):
                os.unlink(self.pdf_path)
                return "File non valido o corrotto."

            print("\n=== Inizializzazione sistema QA ===")
            # Crea il sistema QA con il nuovo PDF
            self.qa_system = self.crea_qa_system()
            print("✅ Sistema QA inizializzato con successo")
            return "PDF caricato con successo! Ora puoi fare domande sul documento."
        except Exception as e:
            print(f"\n❌ ERRORE nel caricamento del PDF: {str(e)}")
            if hasattr(self, 'pdf_path') and self.pdf_path and os.path.exists(self.pdf_path):
                os.unlink(self.pdf_path)
            return f"Errore nel caricamento del PDF: {str(e)}"

    def crea_qa_system(self):
        try:
            print("\n=== Creazione sistema QA ===")
            print("🤖 Inizializzazione modello Mistral...")
            llm = OllamaLLM(
                model="mistral",
                system="Sei un assistente italiano specializzato in analisi di documenti. "
                       "IMPORTANTE: Rispondi SOLO in italiano, mai in inglese. "
                       "Usa un linguaggio chiaro, professionale e accessibile."
            )
            print("✅ Modello Mistral inizializzato")
            
            print("\n🔄 Creazione embeddings...")
            embeddings = OllamaEmbeddings(model="mistral")
            print("✅ Embeddings creati")
            
            # Creiamo un database vettoriale univoco per questo PDF
            self.current_db = self._get_db_name(self.pdf_path)
            print(f"\n🔄 Creazione database vettoriale: {self.current_db}")
            print(f"📄 Caricamento PDF da: {self.pdf_path}")
            
            loader = PyPDFLoader(self.pdf_path)
            text_splitter = CharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            print("📝 Divisione del documento in chunks...")
            pages = loader.load_and_split(text_splitter)
            print(f"✅ Documento diviso in {len(pages)} chunks")
            
            print("\n💾 Creazione database vettoriale...")
            # Se esiste già un database con lo stesso nome, lo rimuoviamo
            if os.path.exists(self.current_db):
                import shutil
                shutil.rmtree(self.current_db)
            
            # Creiamo un nuovo client Chroma con le impostazioni corrette
            client_settings = Settings(
                chroma_server_host=os.getenv("CHROMA_SERVER_HOST", "192.168.200.20"),
                chroma_server_http_port=int(os.getenv("CHROMA_SERVER_PORT", "8000")),
                anonymized_telemetry=False,
                allow_reset=True,
                is_persistent=True
            )
            
            # Forziamo la chiusura di eventuali istanze esistenti
            try:
                import chromadb
                chromadb.Client().reset()
            except:
                pass
            
            vectordb = Chroma.from_documents(
                documents=pages,
                embedding=embeddings,
                persist_directory=self.current_db,
                collection_name="pdf_collection",
                collection_metadata={"hnsw:space": "cosine"},
                client_settings=client_settings
            )
            print("✅ Database vettoriale creato e salvato")

            print("\n🔄 Configurazione retriever...")
            retriever = vectordb.as_retriever()
            print("✅ Retriever configurato")

            print("\n📝 Creazione prompt template...")
            prompt_template = PromptTemplate(
                input_variables=["context", "question"],
                template="Contesto: {context}\n\nDomanda: {question}\n\nRispondi in italiano in modo chiaro e conciso:"
            )
            print("✅ Prompt template creato")

            print("\n🔗 Creazione catena conversazionale...")
            qa = ConversationalRetrievalChain.from_llm(
                llm=llm,
                retriever=retriever,
                memory=self.memory,
                combine_docs_chain_kwargs={"prompt": prompt_template}
            )
            print("✅ Catena conversazionale creata")
            return qa
        except Exception as e:
            print(f"\n❌ ERRORE nella creazione del sistema QA: {str(e)}")
            print(f"Tipo di errore: {type(e).__name__}")
            import traceback
            print("Stack trace completo:")
            print(traceback.format_exc())
            return None

    def risposta(self, domanda):
        if not self.current_user:
            return "Effettua il login prima di fare domande."
        
        success, message = self.check_session()
        if not success:
            return message

        if not self.qa_system:
            return "Per favore, carica prima un documento PDF."
        try:
            start_time = time.time()
            # Aggiorna il timestamp di ultima attività
            self.last_activity = time.time()
            if self.current_db and os.path.exists(self.current_db):
                os.utime(self.current_db)
            
            result = self.qa_system({"question": domanda})
            response_time = time.time() - start_time
            self.metrics.track_response_time(response_time, "query_response")
            return result['answer']
        except Exception as e:
            self.metrics.track_response_time(time.time() - start_time, "query_error")
            return f"Errore: {str(e)}"

def crea_interfaccia():
    qa_bot = DocumentQA()

    with gr.Blocks(theme=gr.themes.Soft()) as iface:
        # Alert iniziale
        with gr.Row():
            gr.Markdown("""
            ⚠️ **ATTENZIONE**: Questa è un'applicazione di testing sviluppata utilizzando solo materiale gratuito.
            Le prestazioni potrebbero essere lente e le risposte potrebbero non essere sempre accurate.
            Si prega di essere pazienti durante l'elaborazione delle richieste.
            """)

        gr.Markdown("# Chatbot Documentale con Gestione Utenti")
        gr.Markdown("⏱️ Ogni utente ha a disposizione 10 minuti di utilizzo")
        
        # Login section
        with gr.Row():
            with gr.Column():
                username_input = gr.Textbox(
                    label="Nome Utente",
                    placeholder="Inserisci il tuo nome"
                )
                login_btn = gr.Button("Accedi", variant="primary")
                status = gr.Textbox(
                    label="Stato",
                    interactive=False
                )
        
        # Main interface (initially hidden)
        with gr.Row(visible=False) as main_interface:
            with gr.Column():
                gr.Markdown("""
                ## Guida all'Utilizzo
                1. Carica un documento PDF usando il pulsante "Carica PDF"
                2. Inserisci una domanda nel campo di testo
                3. Clicca su "Invia Domanda" o premi Invio
                4. La risposta apparirà nel campo sottostante
                5. La sessione scadrà automaticamente dopo 10 minuti
                6. Puoi cambiare PDF in qualsiasi momento usando il pulsante "Cambia PDF"
                """)
                file_input = gr.File(
                    label="Carica il tuo PDF",
                    file_types=[".pdf"]
                )
                upload_status = gr.Textbox(
                    label="Stato Caricamento PDF",
                    interactive=False,
                    visible=True
                )
                with gr.Row():
                    reset_btn = gr.Button("Cambia PDF", variant="secondary")
                    logout_btn = gr.Button("Logout", variant="stop")
            with gr.Column():
                domanda = gr.Textbox(
                    lines=2,
                    placeholder="Inserisci la tua domanda qui...",
                    label="Domanda"
                )
                invia_btn = gr.Button("Invia Domanda", variant="primary")
                risposta = gr.Textbox(
                    lines=5,
                    label="Risposta"
                )

        def update_interface(username):
            success, message = qa_bot.login(username)
            if success:
                if username == "qwer":
                    # Se è stata inserita la parola segreta, ricarica la pagina
                    return {
                        main_interface: gr.update(visible=False),
                        status: message,
                        username_input: gr.update(interactive=True, value=""),
                        login_btn: gr.update(visible=True),
                        upload_status: "",
                        risposta: ""
                    }
                return {
                    main_interface: gr.update(visible=True),
                    status: message,
                    username_input: gr.update(interactive=False),
                    login_btn: gr.update(visible=False)
                }
            return {
                main_interface: gr.update(visible=False),
                status: message,
                username_input: gr.update(interactive=True),
                login_btn: gr.update(visible=True)
            }

        def logout():
            if qa_bot.current_user:
                qa_bot.user_manager.remove_user(qa_bot.current_user)
                qa_bot.current_user = None
                if qa_bot.current_db and os.path.exists(qa_bot.current_db):
                    import shutil
                    shutil.rmtree(qa_bot.current_db)
                return {
                    main_interface: gr.update(visible=False),
                    status: "Logout effettuato con successo",
                    username_input: gr.update(interactive=True, value=""),
                    login_btn: gr.update(visible=True),
                    upload_status: "",
                    risposta: ""
                }
            return {
                status: "Nessun utente connesso"
            }

        def reset_system():
            try:
                print("\n=== Reset del sistema ===")
                if qa_bot.current_db and os.path.exists(qa_bot.current_db):
                    print("🗑️ Rimozione database esistente...")
                    import shutil
                    shutil.rmtree(qa_bot.current_db)
                    print("✅ Database rimosso")
                
                qa_bot.qa_system = None
                qa_bot.pdf_path = None
                qa_bot.current_db = None
                return "Sistema resettato. Ora puoi caricare un nuovo PDF."
            except Exception as e:
                print(f"❌ Errore nel reset del sistema: {str(e)}")
                return f"Errore nel reset del sistema: {str(e)}"

        # Event handlers
        login_btn.click(
            fn=update_interface,
            inputs=username_input,
            outputs=[main_interface, status, username_input, login_btn]
        )

        logout_btn.click(
            fn=logout,
            inputs=[],
            outputs=[main_interface, status, username_input, login_btn, upload_status, risposta]
        )

        reset_btn.click(
            fn=reset_system,
            inputs=[],
            outputs=upload_status
        )

        file_input.change(
            fn=qa_bot.carica_pdf,
            inputs=file_input,
            outputs=upload_status
        )

        invia_btn.click(
            fn=qa_bot.risposta,
            inputs=domanda,
            outputs=risposta
        )

        domanda.submit(
            fn=qa_bot.risposta,
            inputs=domanda,
            outputs=risposta
        )

        gr.Examples(
            examples=[
                ["Qual è l'argomento principale del documento?"],
                ["Puoi spiegarmi meglio questo concetto?"],
                ["Puoi fare un riassunto dei punti principali?"]
            ],
            inputs=domanda
        )

    return iface

if __name__ == "__main__":
    iface = crea_interfaccia()
    iface.launch(share=True)  # Abilitato l'accesso pubblico
