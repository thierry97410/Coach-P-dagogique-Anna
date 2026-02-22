import streamlit as st
import pandas as pd
import os
import io
from PyPDF2 import PdfReader
import google.generativeai as genai

# --- 1. CONFIGURATION DE L'AGENT ---
SYSTEM_PROMPT = """
Tu es Joris, un psycho-pédagogue expert pour Anna (14 ans, HPI, déscolarisée). 
Ton but est de lui redonner le goût d'apprendre par des séances denses et passionnantes.
Tu tutoies Anna avec bienveillance et respect.
Tu ne te contentes pas de résumer : tu expliques le SENS des choses en profondeur.
Tu utilises les documents fournis MAIS tu complètes avec tes propres connaissances pour enrichir le cours.
"""

st.set_page_config(page_title="L'Espace d'Anna", layout="wide")

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Clé API manquante.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel(
    model_name='gemini-2.5-flash',
    system_instruction=SYSTEM_PROMPT
)

# --- 2. FONCTIONS DE CHARGEMENT ---

def load_context(folder, matiere):
    text = ""
    prefix = matiere[:4].upper()
    if os.path.exists(folder):
        files = [f for f in os.listdir(folder) if f.upper().startswith(prefix) and f.lower().endswith(".pdf")]
        for f_name in files:
            with open(os.path.join(folder, f_name), "rb") as f:
                reader = PdfReader(f)
                text += "".join([p.extract_text() for p in reader.pages if p.extract_text()])
    return text[:150000]

# --- 3. INTERFACE ÉPURÉE ---

st.title("📚 Séance d'Apprentissage")

CSV_PATH = "bibliotheque/programme.csv"
if os.path.exists(CSV_PATH):
    df = pd.read_csv(CSV_PATH, sep=",")
    df.columns = df.columns.str.strip()
else:
    st.error("Fichier programme.csv introuvable.")
    st.stop()

with st.sidebar:
    st.header("📖 Programme")
    matieres = df["Matiere"].unique()
    choix_mat = st.selectbox("Choisir une matière :", matieres)
    
    chapitres = df[df["Matiere"] == choix_mat]["Chapitre"].tolist()
    choix_chap = st.radio("Sélectionner le chapitre :", chapitres)

# --- 4. CŒUR DE LA SÉANCE ---

st.subheader(f"📍 Sujet : {choix_chap}")
besoin_anna = st.text_area("Coucou Anna, as-tu une question ou une envie particulière pour aujourd'hui ?", 
                           placeholder="Ex: 'Je ne comprends pas l'utilité de ce cours' ou 'Peux-tu me donner des exemples concrets ?'",
                           height=100)

if st.button("🚀 Lancer la séance"):
    with st.spinner("Joris prépare tes ressources..."):
        contexte_pdf = load_context("bibliotheque", choix_mat)
        
        prompt = f"""
        ANNA te demande de travailler sur : {choix_chap} (Matière : {choix_mat}).
        Son message : "{besoin_anna}".
        Contenu des PDF (à utiliser comme base) : {contexte_pdf}.
        
        DÉROULEMENT DE LA SÉANCE :
        1. **L'essentiel du Cours** : Développe le sujet de manière riche et captivante. Utilise tes connaissances pour rendre le cours plus vivant que de simples notes. Mets en **gras** les concepts clés.
        2. **La Minute Curiosité (Vidéo)** : Suggère un titre précis de vidéo (Lumni ou YouTube) pour illustrer le sujet.
        3. **Les Exercices d'Application** : Propose 2 ou 3 exercices variés pour mettre en pratique ce qui vient d'être vu.
        4. **Le Quiz de Fin** : 3 à 5 questions rapides pour vérifier que les points importants sont compris.
        """
        
        try:
            response = model.generate_content(prompt)
            st.session_state['current_resp'] = response.text
        except Exception as e:
            st.error(f"Erreur technique : {e}")

# --- 5. AFFICHAGE DU CONTENU ---

if 'current_resp' in st.session_state:
    st.divider()
    st.markdown(st.session_state['current_resp'])
    
    # Option de téléchargement simple
    st.download_button("📥 Garder cette séance en texte", 
                       st.session_state['current_resp'], 
                       file_name=f"Seance_{choix_chap}.txt")
