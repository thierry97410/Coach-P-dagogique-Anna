import streamlit as st
import pandas as pd
import os
from PyPDF2 import PdfReader
import google.generativeai as genai

# --- 1. DESIGN & CONFIGURATION ---
st.set_page_config(page_title="Anna : Mon Assistant", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #1E293B; color: #F8FAFC; }
    h1, h2, h3 { color: #FDE047 !important; }
    [data-testid="stSidebar"] { background-color: #0F172A; border-right: 1px solid #334155; }
    .stButton>button { background-color: #FDE047; color: #0F172A; font-weight: bold; border-radius: 8px; }
    .stDownloadButton>button { background-color: #10B981; color: white; border-radius: 8px; }
    .stCheckbox { background-color: #334155; padding: 10px; border-radius: 10px; margin: 5px 0; }
    </style>
    """, unsafe_allow_html=True)

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Clé API manquante.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-pro')

# --- 2. FONCTIONS ---

def extract_pdf_text(file):
    try:
        reader = PdfReader(file)
        return "".join([page.extract_text() for page in reader.pages if page.extract_text()])
    except: return ""

def load_all_contexts(folder, matieres_list):
    combined_text = ""
    if not os.path.exists(folder): return ""
    for mat in matieres_list:
        prefix = mat[:4].upper()
        files = [f for f in os.listdir(folder) if f.upper().startswith(prefix) and f.lower().endswith(".pdf")]
        for filename in files:
            with open(os.path.join(folder, filename), "rb") as f:
                combined_text += f"\n--- {mat} ---\n" + extract_pdf_text(f)
    return combined_text[:150000]

# --- 3. INTERFACE ---

st.title("🎓 Anna : mon assistant pédagogique")

CSV_PATH = "bibliotheque/programme.csv"
if os.path.exists(CSV_PATH):
    df = pd.read_csv(CSV_PATH, sep=",")
    df.columns = df.columns.str.strip()
else:
    st.error("Fichier programme.csv introuvable.")
    st.stop()

with st.sidebar:
    st.header("⚙️ Ma Séance")
    matieres_dispos = df["Matiere"].unique()
    choix_matieres = st.multiselect("Matières :", matieres_dispos, default=[matieres_dispos[0]])
    
    # Durée automatique
    nb_mat = len(choix_matieres)
    duree_suggeree = 15 if nb_mat <= 1 else (30 if nb_mat == 2 else 45)
    duree = st.select_slider("Durée :", options=["15 min", "30 min", "45 min", "1h", "1h30"], value=f"{duree_suggeree} min")
    
    supports = st.multiselect("Supports :", ["Écrit", "Vidéo (Lumni/YouTube)", "Mixte"], default=["Mixte"])
    
    st.divider()
    doc_eleve = st.file_uploader("Document à analyser (PDF)", type="pdf")

besoin = st.text_area("Sur quoi veux-tu te concentrer Anna ?", placeholder="Ex: Les guerres mondiales...", height=100)

if st.button("🚀 C'est parti !"):
    if not besoin and not doc_eleve:
        st.warning("Indique un sujet pour commencer.")
    else:
        with st.spinner("Joris prépare ton parcours..."):
            contexte_bib = load_all_contexts("bibliotheque", choix_matieres)
            contexte_exo = extract_pdf_text(doc_eleve) if doc_eleve else ""

            prompt = f"""
            Tu es Joris, l'assistant d'Anna. 
            DURÉE : {duree} | MATIÈRES : {', '.join(choix_matieres)} | SUPPORTS : {', '.join(supports)}
            
            MISSION :
            1. Propose 1 ou 2 thèmes de recherche ultra-précis pour Lumni et YouTube (50-60% du temps).
            2. Donne un résumé structuré basé sur les PDF : {contexte_bib}
            3. Termine par un quiz de 3 questions.
            4. TON TON : Amical, direct, encourageant.
            """

            response = model.generate_content(prompt)
            st.session_state['last_response'] = response.text
            st.session_state['search_query'] = besoin

# --- 4. JOURNAL DE BORD ET ACTIONS (Post-Génération) ---

if 'last_response' in st.session_state:
    st.markdown("---")
    
    # Zone d'outils interactifs
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📋 Ton Journal de Bord")
        st.checkbox("J'ai trouvé et regardé la vidéo conseillée 📺")
        st.checkbox("J'ai lu le résumé de Joris 📖")
        st.checkbox("J'ai répondu au quiz de fin ✅")
    
    with col2:
        st.subheader("🔗 Liens Rapides")
        q = st.session_state['search_query']
        st.link_button("🔍 Chercher sur Lumni", f"https://www.lumni.fr/recherche?query={q}")
        st.link_button("🎥 Chercher sur YouTube Premium", f"https://www.youtube.com/results?search_query={q}")
        
        # Mode "Hors-ligne" : Téléchargement de la séance
        st.download_button("📥 Sauvegarder la séance (PDF/Texte)", 
                           data=st.session_state['last_response'], 
                           file_name=f"seance_anna_{choix_matieres[0]}.txt",
                           mime="text/plain")

    st.markdown("---")
    st.markdown(st.session_state['last_response'])
