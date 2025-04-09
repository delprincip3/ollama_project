from langchain_community.llms import Ollama

def test_mistral():
    # Inizializza il modello
    llm = Ollama(model="mistral")
    
    # Test con una domanda
    risposta = llm.invoke("Dimmi qualcosa sull'intelligenza artificiale.")
    print("Risposta del modello:")
    print(risposta)

if __name__ == "__main__":
    test_mistral()
