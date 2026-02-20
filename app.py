import streamlit as st
import pandas as pd
import os
from PyPDF2 import PdfReader
import google.generativeai as genai

# --- CONFIGURATION ---
st.set_page_config(page_title="Le Coach d'Anna", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("Clé API manquante dans les secrets Streamlit.")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-pro')

# --- FONCTIONS ---

def extract_pdf_text(file):
    """Extrait le texte d'un PDF."""
    try:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
        return text
    except Exception as e:
        return f"Erreur de lecture : {e}"

@st.cache_data
def get_subject_content(folder, matiere):
    """Charge les PDF de la matière. PLANTE si aucun fichier n'est trouvé."""
    if not os.path.exists(folder):
        st.error(f"❌ DOSSIER INTROUVABLE : Le dossier '{folder}' n'existe pas.")
        st.stop()
    
    prefix = matiere[:4].upper()
    files = [f for f in os.listdir(folder) if f.upper().startswith(prefix) and f.lower().endswith(".pdf")]
    
    # --- LOGIQUE DE STABILITÉ DEMANDÉE ---
    if not files:
        st.error(f"🚨 ERREUR DE FICHIER : Aucun PDF trouvé pour la matière '{matiere}'.")
        st.info(f"Vérifie que tes fichiers commencent bien par '{prefix}_' dans le dossier bibliothèque.")
        st.stop() # Arrête l'exécution ici
    
    full_text = ""
    for filename in files:
        with open(os.path.join(folder, filename), "rb") as f:
            full_text += f"\n--- DOCUMENT : {filename} ---\n"
            full_text += extract_pdf_text(f)
            
    return full_text[:120000]

# --- INTERFACE ---

st.title("🎓 Le Coach Scolaire d'Anna")
st.caption("Système de continuité pédagogique - Mode Sécurité Activé")

if not os.path.exists("bibliotheque/programme.csv"):
    st.error("🚨 FICHIER MANQUANT : 'programme.csv' est introuvable.")
    st.stop()

df_prog = pd.read_csv("bibliotheque/programme.csv", sep=";")

with st.sidebar:
    st.header("📚 Session de travail")
    liste_matieres = df_prog["Matiere"].unique()
    choix_matiere = st.selectbox("Matière", liste_matieres)
    
    chapitres = df_prog[df_prog["Matiere"] == choix_matiere]["Chapitre"].tolist()
    choix_chapitre = st.selectbox("Chapitre", chapitres)
    
    st.divider()
    doc_eleve = st.file_uploader("Document d'exercice (Optionnel)", type="pdf")

sujet = st.text_input("Sujet ou question d'Anna :", placeholder="Ex: C'est quoi un ion ?")

if st.button("🚀 Lancer la séance", type="primary"):
    with st.spinner("Joris vérifie les sources et prépare le cours..."):
        # Cette fonction va 'stoppper' l'appli si le fichier est mal nommé
        contexte_officiel = get_subject_content("bibliotheque", choix_matiere)
        contexte_exercice = extract_pdf_text(doc_eleve) if doc_eleve else "Aucun document d'exercice fourni."
        
        prompt = f"""
        Tu es Joris, le tuteur d'Anna (élève de 3ème en instruction à domicile).
        Anna n'a pas accès à ses professeurs, tu dois être précis et rigoureux.

        CONTEXTE OFFICIEL (Bibliothèque) :
        {contexte_officiel}

        DEMANDE D'ANNA : {sujet} (Chapitre : {choix_chapitre})
        EXERCICE FOURNI : {contexte_exercice}

        TON RÔLE :
        1. Explique la notion en t'appuyant sur les documents officiels.
        2. Guide-la dans son exercice sans donner les réponses.
        3. Termine TOUJOURS par une section '### 📝 Petit Quiz de fin' avec 3 questions rapides pour vérifier sa compréhension.
        4. Sois direct, encourageant et assure-toi qu'elle ne décroche pas.
        """
        
        try:
            response = model.generate_content(prompt)
            st.markdown("---")
            st.markdown(response.text)
        except Exception as e:
            st.error(f"Erreur technique Gemini : {e}")
