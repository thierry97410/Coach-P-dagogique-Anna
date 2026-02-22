import streamlit as st
import pandas as pd
import os
import re
from PyPDF2 import PdfReader
import google.generativeai as genai
import streamlit.components.v1 as components

# --- 1. CONFIGURATION DE L'AGENT ---
SYSTEM_PROMPT = """
Tu es Joris, l'allié intellectuel d'Anna (14 ans, HPI). 
Ton rôle est double :
1. Générer des séances de travail denses, structurées et passionnantes (Cours, Lexique, Vidéo, Atelier de réflexion, Schémas Mermaid, Quiz).
2. Dialoguer avec elle pour approfondir, clarifier ou explorer des paradoxes liés au sujet.
Tu tutoies Anna avec respect et complicité. Tu ne simplifies jamais à l'excès, tu nourris sa soif de complexité.
"""

st.set_page_config(page_title="L'Espace d'Anna", layout="wide")

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Clé API manquante.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=SYSTEM_PROMPT)

# Initialisation de la mémoire de l'agent
if "chat" not in st.session_state:
    st.session_state.chat = model.start_chat(history=[])
if "current_session" not in st.session_state:
    st.session_state.current_session = None

# --- 2. FONCTIONS TECHNIQUES ---

def render_mermaid(code):
    html = f"""
    <div class="mermaid" style="background-color: white; padding: 10px; border-radius: 10px;">{code}</div>
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

# --- 3. INTERFACE ---

st.title("🎓 Ton Espace d'Apprentissage")

CSV_PATH = "bibliotheque/programme.csv"
if os.path.exists(CSV_PATH):
    df = pd.read_csv(CSV_PATH, sep=",")
    df.columns = df.columns.str.strip()
else: st.stop()

with st.sidebar:
    st.header("📖 Navigation")
    choix_mat = st.selectbox("Matière :", df["Matiere"].unique())
    chapitres = df[df["Matiere"] == choix_mat]["Chapitre"].tolist()
    choix_chap = st.radio("Chapitre :", chapitres)
    
    st.divider()
    if st.button("♻️ Réinitialiser Joris"):
        st.session_state.chat = model.start_chat(history=[])
        st.session_state.current_session = None
        st.rerun()

# --- 4. CRÉATION DE LA SÉANCE ---

if not st.session_state.current_session:
    st.subheader(f"📍 Nouveau sujet : {choix_chap}")
    message_intro = st.text_area("Un mot pour Joris avant de commencer ?", height=70)
    
    if st.button("🚀 Générer la séance de travail"):
        with st.spinner("Joris prépare ton exploration..."):
            contexte = load_context("bibliotheque", choix_mat)
            
            prompt_initial = f"""
            Génère une séance complète sur : {choix_chap} ({choix_mat}).
            Message d'Anna : {message_intro}.
            Contexte PDF : {contexte}.
            
            Structure : 
            # Accueil & Sens
            # Exploration Approfondie (gras pour les concepts)
            ## 📖 Lexique des Curieux ([MOT]: [DEF])
            ## 🎥 Support Humain (Vidéo)
            # 🖋️ Atelier de Réflexion (2 questions ouvertes)
            # 🧠 Architecture Logique (Mermaid)
            # ⏳ Chronologie (Mermaid)
            # 📝 Quiz Flash (3 QCM)
            RECO:[MATIERE]|[CHAPITRE]
            """
            response = st.session_state.chat.send_message(prompt_initial)
            st.session_state.current_session = response.text
        st.rerun()

# --- 5. AFFICHAGE ET DIALOGUE ---

if st.session_state.current_session:
    # Zone de la Séance (Scrollable)
    with st.container():
        parts = re.split(r'(```mermaid.*?```|## 📖 Lexique des Curieux.*?\n\n)', st.session_state.current_session, flags=re.DOTALL)
        for part in parts:
            if part.startswith('```mermaid'):
                m_code = part.replace('```mermaid', '').replace('```', '').strip()
                render_mermaid(m_code)
            elif "Lexique des Curieux" in part:
                st.subheader("📖 Lexique des Curieux")
                for line in part.split('\n'):
                    if ':' in line and '[' in line:
                        t, d = line.split(':', 1)
                        with st.expander(f"🔹 {t.strip(' []')}"): st.write(d.strip())
            else:
                st.markdown(re.sub(r'RECO:.*?\|.*', '', part))

    st.divider()
    st.subheader("🗨️ Discussion avec Joris")
    
    # Historique du Chat (uniquement les échanges APRÈS la création de séance)
    for message in st.session_state.chat.history[2:]: # On saute le prompt initial
        role = "Joris" if message.role == "model" else "Anna"
        with st.chat_message(role):
            st.markdown(message.parts[0].text)

    # Entrée du Chat
    if prompt_interactif := st.chat_input("Pose une question, demande une précision ou un approfondissement..."):
        with st.chat_message("Anna"):
            st.markdown(prompt_interactif)
        
        with st.spinner("Joris te répond..."):
            response = st.session_state.chat.send_message(prompt_interactif)
            with st.chat_message("Joris"):
                st.markdown(response.text)
