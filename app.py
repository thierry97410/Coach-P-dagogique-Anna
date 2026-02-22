import streamlit as st
import pandas as pd
import os
import io
import re
from PyPDF2 import PdfReader
import google.generativeai as genai
from fpdf import FPDF
import streamlit.components.v1 as components

# --- 1. CONFIGURATION DE L'AGENT SPECIALISÉ ---

# C'est ici que l'identité de Joris est scellée, hors de ton compte global.
SYSTEM_PROMPT = """
Tu es Joris, un agent expert en psycho-pédagogie pour Anna (14 ans, HPI, artiste). 
Ton rôle est de la réconcilier avec les apprentissages par la densité et le sens.
- Ton ton : Brillant, complice, tutoiement respectueux, jamais infantilisant.
- Éthique : Tu es un curateur de savoirs humains. Cite les PDF et suggère des vidéos (Lumni/YouTube).
- Visuel : Tu utilises le Markdown riche (# Titre, **gras**) et Mermaid pour structurer la pensée.
- Pédagogie : Tu privilégies la complexité, les questions ouvertes (rédaction) et les schémas logiques.
"""

st.set_page_config(page_title="L'Espace d'Anna", layout="wide")

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Clé API manquante.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# Initialisation de l'agent dédié
model = genai.GenerativeModel(
    model_name='gemini-2.5-flash',
    system_instruction=SYSTEM_PROMPT
)

# Gestion de l'état de la session
if 'resp' not in st.session_state: st.session_state.resp = None
if 'current_mat' not in st.session_state: st.session_state.current_mat = None
if 'current_chap' not in st.session_state: st.session_state.current_chap = None

# --- 2. FONCTIONS TECHNIQUES ---

def render_mermaid(code):
    """Affiche Mermaid avec un thème neutre par défaut."""
    html = f"""
    <div class="mermaid" style="background-color: white; padding: 10px;">
        {code}
    </div>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ startOnLoad: true, theme: 'neutral' }});
    </script>
    """
    components.html(html, height=450, scrolling=True)

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

st.title("🎓 Séance de Travail")

CSV_PATH = "bibliotheque/programme.csv"
if os.path.exists(CSV_PATH):
    df = pd.read_csv(CSV_PATH, sep=",")
    df.columns = df.columns.str.strip()
else: st.stop()

if st.session_state.current_mat is None: st.session_state.current_mat = df["Matiere"].unique()[0]

with st.sidebar:
    st.header("📚 Programme")
    choix_mat = st.selectbox("Matière :", df["Matiere"].unique(), 
                             index=list(df["Matiere"].unique()).index(st.session_state.current_mat))
    chapitres = df[df["Matiere"] == choix_mat]["Chapitre"].tolist()
    choix_chap = st.radio("Chapitre :", chapitres)
    st.session_state.current_mat, st.session_state.current_chap = choix_mat, choix_chap
    
    st.divider()
    doc_eleve = st.file_uploader("📂 Document support (PDF)", type="pdf")

# --- 4. ESPACE DE TRAVAIL ---

st.subheader(f"📍 Sujet : {choix_chap}")
besoin_anna = st.text_area("Anna, une question ou une envie particulière ?", height=80)

if st.button("🚀 Lancer la séance"):
    with st.spinner("Joris prépare ton exploration..."):
        contexte = load_context("bibliotheque", choix_mat)
        
        # Le prompt utilisateur est désormais très simple
        user_prompt = f"""
        Sujet du jour : {choix_chap} (Matière : {choix_mat}).
        Note d'Anna : {besoin_anna}.
        Base de travail : {contexte}.
        
        Produis la séance complète avec :
        1. Accueil & Sens.
        2. Exploration Approfondie (utilise le gras pour les concepts clés).
        3. Lexique des Curieux (Format [MOT]: [DÉFINITION]).
        4. Vidéo recommandée.
        5. Atelier de Réflexion (2 questions ouvertes).
        6. Architecture Logique (Mermaid).
        7. Chronologie (Mermaid).
        8. Quiz Flash (3 QCM).
        9. RECO:[MATIERE]|[CHAPITRE].
        """
        try:
            res = model.generate_content(user_prompt)
            st.session_state.resp = res.text
        except Exception as e: st.error(f"Erreur : {e}")

# --- 5. RÉSULTATS ---

if st.session_state.resp:
    st.divider()
    parts = re.split(r'(```mermaid.*?```|## Lexique des Curieux.*?\n\n)', st.session_state.resp, flags=re.DOTALL)
    
    for part in parts:
        if part.startswith('```mermaid'):
            m_code = part.replace('```mermaid', '').replace('```', '').strip()
            with st.expander("🔍 Voir l'infographie", expanded=True):
                render_mermaid(m_code)
        elif "Lexique des Curieux" in part:
            st.subheader("📖 Lexique des Curieux")
            for line in part.split('\n'):
                if ':' in line and '[' in line:
                    t, d = line.split(':', 1)
                    with st.expander(f"🔹 {t.strip(' []')}"): st.write(d.strip())
        else:
            st.markdown(re.sub(r'RECO:.*?\|.*', '', part))

    # Navigation simplifiée
    reco = re.search(r"RECO:(.*?)\|(.*)", st.session_state.resp)
    if reco:
        m, c = reco.group(1).strip(), reco.group(2).strip()
        if st.button(f"➡️ Suivre le fil : {c}"):
            st.session_state.current_mat, st.session_state.current_chap = m, c
            st.session_state.resp = None
            st.rerun()
