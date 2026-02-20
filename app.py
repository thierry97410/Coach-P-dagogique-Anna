import streamlit as st
import pandas as pd
import os
import io
from PyPDF2 import PdfReader
import google.generativeai as genai
from fpdf import FPDF

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Anna : Mon Assistant", layout="wide")

# Configuration API
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Clé API manquante dans les secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
# Utilisation du modèle stable identifié
model = genai.GenerativeModel('gemini-2.5-flash')

# --- 2. FONCTIONS TECHNIQUES ---

def create_pdf(text):
    """Génère un PDF et le convertit en bytes compatibles avec Streamlit."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    # Nettoyage pour éviter les erreurs de caractères spéciaux
    clean_text = text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 10, txt=clean_text)
    
    # Correction cruciale : on récupère le bytearray et on le transforme en bytes
    return bytes(pdf.output())

def extract_pdf_text(file):
    try:
        reader = PdfReader(file)
        return "".join([p.extract_text() for p in reader.pages if p.extract_text()])
    except: return ""

def load_all_contexts(folder, matiere):
    combined_text = ""
    if not os.path.exists(folder): return ""
    prefix = matiere[:4].upper()
    files = [f for f in os.listdir(folder) if f.upper().startswith(prefix) and f.lower().endswith(".pdf")]
    for filename in files:
        with open(os.path.join(folder, filename), "rb") as f:
            combined_text += extract_pdf_text(f)
    return combined_text[:120000]

# --- 3. INTERFACE DE GUIDAGE ---

st.title("🎓 Anna : mon assistant pédagogique")

# Chargement du programme (CSV)
CSV_PATH = "bibliotheque/programme.csv"
if os.path.exists(CSV_PATH):
    df = pd.read_csv(CSV_PATH, sep=",")
    df.columns = df.columns.str.strip()
else:
    st.error("Fichier programme.csv introuvable.")
    st.stop()

with st.sidebar:
    st.header("📖 Ton Parcours")
    matieres = df["Matiere"].unique()
    choix_mat = st.selectbox("Matière :", matieres)
    
    chapitres = df[df["Matiere"] == choix_mat]["Chapitre"].tolist()
    st.write("---")
    # Guidage pédagogique : Anna voit la suite logique du programme
    choix_chap = st.radio("Sélectionne le chapitre suivant :", chapitres)
    
    st.divider()
    duree = st.select_slider("Durée de la séance :", options=["15 min", "30 min", "1h", "1h30"], value="30 min")
    doc_eleve = st.file_uploader("📂 Joindre un document (facultatif)", type="pdf")

# --- 4. LA SÉANCE SCÉNARISÉE ---

st.subheader(f"📍 {choix_mat} : {choix_chap}")

if st.button("🚀 Lancer la séance guidée"):
    with st.spinner("Joris prépare ton cours, tes exercices et tes anecdotes..."):
        contexte_bib = load_all_contexts("bibliotheque", choix_mat)
        contexte_exo = extract_pdf_text(doc_eleve) if doc_eleve else ""

        prompt = f"""
        Tu es Joris, le tuteur d'Anna (14 ans, 3ème). Tu dois créer une séance complète de {duree}.
        CHAPITRE : {choix_chap} ({choix_mat}).
        
        STRUCTURE STRICTE À SUIVRE :
        1. **Introduction** : Pourquoi ce chapitre est important et fascinant.
        2. **Le Cours** : Synthèse pédagogique basée sur : {contexte_bib}.
        3. **Support Ludique** : Propose un titre exact de vidéo à chercher sur Lumni ou YouTube.
        4. **L'exercice original** : Crée un exercice pratique inédit (pas une simple question de cours).
        5. **Le savais-tu ?** : Une anecdote historique, scientifique ou rigolote sur le sujet.
        6. **Quiz final** : 3 questions rapides pour vérifier que tout est compris.

        TON TON : Direct, amical, comme un grand frère prof. Utilise des emojis.
        """

        try:
            response = model.generate_content(prompt)
            st.session_state['resp'] = response.text
        except Exception as e:
            st.error(f"Erreur avec Joris : {e}")

# --- 5. RÉSULTATS ET SUIVI ---

if 'resp' in st.session_state:
    st.markdown("---")
    st.subheader("📊 Suivi de ta progression")
    
    c1, c2, c3 = st.columns(3)
    with c1: st.checkbox("Recherche vidéo faite 📺")
    with c2: st.checkbox("Exercice inédit terminé ✍️")
    with c3: st.checkbox("Quiz validé ✅")
    
    col_l, col_r = st.columns(2)
    with col_l:
        search_query = f"3eme {choix_mat} {choix_chap}"
        st.link_button("🔍 Chercher sur YouTube / Lumni", f"https://www.youtube.com/results?search_query={search_query}")
    
    with col_r:
        # Export PDF avec les bytes corrigés
        try:
            pdf_bytes = create_pdf(st.session_state['resp'])
            st.download_button(
                label="📥 Télécharger ma fiche de cours (PDF)",
                data=pdf_bytes,
                file_name=f"Anna_{choix_mat}_{choix_chap.replace(' ', '_')}.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"Erreur de création du PDF : {e}")

    st.markdown("---")
    st.markdown(st.session_state['resp'])
