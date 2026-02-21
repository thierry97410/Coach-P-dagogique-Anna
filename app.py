import streamlit as st
import pandas as pd
import os
import io
from PyPDF2 import PdfReader
import google.generativeai as genai
from fpdf import FPDF

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="L'Espace d'Anna", layout="wide")

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Clé API manquante.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

# --- 2. FONCTIONS TECHNIQUES ---

def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    clean_text = text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 10, txt=clean_text)
    return bytes(pdf.output())

def extract_pdf_text(file):
    try:
        reader = PdfReader(file)
        return "".join([p.extract_text() for p in reader.pages if p.extract_text()])
    except: return ""

def load_all_contexts(folder, matiere):
    """Charge les PDF et retourne le texte ainsi que la liste des fichiers sources."""
    combined_text = ""
    sources_utilisees = []
    if not os.path.exists(folder): return "", []
    
    prefix = matiere[:4].upper()
    files = [f for f in os.listdir(folder) if f.upper().startswith(prefix) and f.lower().endswith(".pdf")]
    
    for filename in files:
        with open(os.path.join(folder, filename), "rb") as f:
            combined_text += f"\n--- DOCUMENT : {filename} ---\n"
            combined_text += extract_pdf_text(f)
            sources_utilisees.append(filename)
            
    return combined_text[:120000], sources_utilisees

# --- 3. INTERFACE ---

st.title("🌟 Mon Espace de Découverte")

CSV_PATH = "bibliotheque/programme.csv"
if os.path.exists(CSV_PATH):
    df = pd.read_csv(CSV_PATH, sep=",")
    df.columns = df.columns.str.strip()
else:
    st.error("Fichier programme.csv introuvable.")
    st.stop()

with st.sidebar:
    st.header("⚙️ Configuration")
    matieres = df["Matiere"].unique()
    choix_mat = st.selectbox("Matière :", matieres)
    
    chapitres = df[df["Matiere"] == choix_mat]["Chapitre"].tolist()
    choix_chap = st.radio("Chapitre à explorer :", chapitres)
    
    st.divider()
    duree = st.select_slider("Temps prévu :", options=["15 min", "30 min", "1h"], value="30 min")
    doc_eleve = st.file_uploader("📂 Joindre un document (PDF)", type="pdf")

# --- 4. L'ESPACE D'ANNA ---

st.subheader(f"📍 Séance : {choix_chap}")

st.write("🗨️ **Anna, c'est ton espace.** Pose ta question ou dis à Joris comment tu te sens :")
besoin_anna = st.text_area("Ton message :", height=100)

col_actions = st.columns([1, 1, 3])
with col_actions[0]: lancer = st.button("🚀 Lancer la séance")
with col_actions[1]: pause_zen = st.button("🧘 Pause Zen")

if pause_zen:
    with st.spinner("Joris prépare un petit moment de calme..."):
        prompt_zen = "Tu es Joris, l'allié d'Anna. Propose une pause fascinante sur l'art ou la science créée par des humains. Bref et doux."
        try:
            res_zen = model.generate_content(prompt_zen)
            st.session_state['resp_zen'] = res_zen.text
            if 'resp' in st.session_state: del st.session_state['resp']
        except: st.error("Erreur.")

if lancer:
    with st.spinner("Joris prépare ton parcours éthique..."):
        contexte_bib, liste_sources = load_all_contexts("bibliotheque", choix_mat)
        contexte_exo = extract_pdf_text(doc_eleve) if doc_eleve else ""

        prompt = f"""
        Tu es Joris, l'allié d'Anna (14 ans, artiste HPI). 
        Tu respectes profondément le travail des créateurs humains.
        
        MESSAGE D'ANNA : "{besoin_anna}"
        SÉANCE : {choix_chap} ({choix_mat}) | DURÉE : {duree}.
        
        STRUCTURE :
        1. **Accueil** : Réponds avec empathie à Anna.
        2. **Le Sens** : Pourquoi ce sujet est fascinant ?
        3. **Le Cours** : Basé sur ces documents : {contexte_bib}.
        4. **Support Humain (Vidéo)** : Propose un titre de vidéo Lumni/YouTube précis.
        5. **Défi de l'Artiste** : Exercice créatif manuel.
        6. **Anecdote** : Le savais-tu ?
        7. **Quiz Zen** : 3 questions de confiance.
        8. **Sources & Crédits** : Cite explicitement les fichiers PDF utilisés ({', '.join(liste_sources)}) et nomme le créateur de la vidéo proposée.

        TON : Complice, stimulant, respectueux.
        """
        try:
            response = model.generate_content(prompt)
            st.session_state['resp'] = response.text
            if 'resp_zen' in st.session_state: del st.session_state['resp_zen']
        except Exception as e:
            st.error(f"Erreur : {e}")

# --- 5. AFFICHAGE ---

if 'resp_zen' in st.session_state:
    st.info(st.session_state['resp_zen'])
    if st.button("✨ Reprendre"):
        del st.session_state['resp_zen']
        st.rerun()

if 'resp' in st.session_state:
    st.divider()
    st.subheader("✅ Ta progression")
    c1, c2, c3 = st.columns(3)
    with c1: st.checkbox("Sujet exploré 🧭")
    with c2: st.checkbox("Défi relevé 🎨")
    with c3: st.checkbox("Quiz fini ✨")
    
    col_links = st.columns(2)
    with col_links[0]:
        st.link_button("🔍 Chercher la vidéo humaine", f"https://www.youtube.com/results?search_query=3eme {choix_mat} {choix_chap}")
    with col_links[1]:
        try:
            pdf_bytes = create_pdf(st.session_state['resp'])
            st.download_button("📥 Garder ma fiche (PDF)", data=pdf_bytes, file_name=f"Anna_{choix_mat}.pdf")
        except: st.warning("PDF indisponible.")

    st.markdown("---")
    st.markdown(st.session_state['resp'])
