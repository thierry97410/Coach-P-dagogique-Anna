import streamlit as st
import pandas as pd
import os
from PyPDF2 import PdfReader
import google.generativeai as genai
from fpdf import FPDF

# --- 1. DESIGN "SÉRÉNITÉ ET LISIBILITÉ TOTALE" ---
st.set_page_config(page_title="Anna : Mon Assistant", layout="wide")

st.markdown("""
    <style>
    /* FORCE LE BLANC ET LE PASTEL SUR TOUT L'ÉCRAN */
    .stApp, [data-testid="stAppViewContainer"] {
        background-color: #F0FDF4 !important; /* Vert menthe très pâle */
        color: #1E3A8A !important;
    }

    /* SIDEBAR : Bleu lagon doux */
    [data-testid="stSidebar"] {
        background-color: #E0F2FE !important;
        border-right: 2px solid #BAE6FD !important;
    }

    /* FIX RADICAL POUR LES FENÊTRES NOIRES (Inputs, Select, Uploader) */
    div[data-baseweb="select"], div[data-baseweb="input"], textarea, 
    div[data-testid="stFileUploader"], div[data-testid="stFileUploadDropzone"],
    .stSelectbox, .stMultiSelect, div[role="listbox"] {
        background-color: white !important;
        color: #1E3A8A !important;
        border: 2px solid #BFDBFE !important;
        border-radius: 10px !important;
    }

    /* Force la couleur du texte dans les menus déroulants */
    div[data-baseweb="popover"] * {
        color: #1E3A8A !important;
        background-color: white !important;
    }

    /* Titres et labels */
    h1, h2, h3, label { 
        color: #1E40AF !important; 
        font-family: 'Segoe UI', Tahoma, sans-serif !important;
        font-weight: bold !important;
    }

    /* Bouton principal */
    .stButton>button {
        background-color: #3B82F6 !important;
        color: white !important;
        font-weight: bold !important;
        border-radius: 50px !important;
        padding: 0.8rem 2rem !important;
        border: none !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
    }
    
    /* Masquer les éléments noirs de l'interface Streamlit */
    header, footer { visibility: hidden !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONFIGURATION API (Moteur Musclé Gemini 2.5 Pro) ---
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("🚨 Clé API manquante dans les secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# Utilisation du modèle stable identifié dans ton diagnostic
# Note : on retire le préfixe 'models/' car le SDK l'ajoute souvent lui-même
MODEL_NAME = 'gemini-2.5-pro'
model = genai.GenerativeModel(MODEL_NAME)

# --- 3. FONCTIONS TECHNIQUES ---

def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    # Nettoyage latin-1 pour éviter les erreurs de caractères spéciaux
    clean_text = text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 10, txt=clean_text)
    return pdf.output(dest='S').encode('latin-1')

def extract_pdf_text(file):
    try:
        reader = PdfReader(file)
        return "".join([p.extract_text() for p in reader.pages if p.extract_text()])
    except: return ""

def load_all_contexts(folder, matieres_list):
    combined_text = ""
    if not os.path.exists(folder): return ""
    for mat in matieres_list:
        prefix = mat[:4].upper()
        files = [f for f in os.listdir(folder) if f.upper().startswith(prefix) and f.lower().endswith(".pdf")]
        for filename in files:
            with open(os.path.join(folder, filename), "rb") as f:
                combined_text += f"\n--- SOURCE {mat} ---\n" + extract_pdf_text(f)
    return combined_text[:200000] # Capacité accrue grâce au modèle Pro

# --- 4. INTERFACE ANNA ---

st.title("🎓 Anna : mon assistant pédagogique")

CSV_PATH = "bibliotheque/programme.csv"
if os.path.exists(CSV_PATH):
    df = pd.read_csv(CSV_PATH, sep=",")
    df.columns = df.columns.str.strip()
else:
    st.error("Fichier programme.csv introuvable dans 'bibliotheque'.")
    st.stop()

with st.sidebar:
    st.header("📋 Ma Session")
    mat_dispos = df["Matiere"].unique()
    choix_mat = st.multiselect("Matières à travailler :", mat_dispos, default=[mat_dispos[0]])
    
    # Durée intelligente
    n = len(choix_mat)
    d_min = 15 if n <= 1 else (30 if n == 2 else 45)
    duree = st.select_slider("Durée prévue :", options=["15 min", "30 min", "45 min", "1h", "1h30"], value=f"{d_min} min")
    
    st.divider()
    doc_eleve = st.file_uploader("📂 Document à joindre (PDF)", type="pdf")

st.subheader("📝 Ce que nous allons faire ensemble :")
besoin = st.text_area("Dis à Joris ce que tu veux apprendre ou l'exercice qui te pose problème :", 
                      placeholder="Ex: Aide-moi à comprendre l'exercice sur les forces en physique...", height=120)

if st.button("🚀 Commencer ma séance"):
    if not besoin and not doc_eleve:
        st.info("Explique-moi ton projet de séance pour que je puisse t'aider !")
    else:
        with st.spinner("Joris analyse tes supports (Modèle Pro activé)..."):
            contexte_bib = load_all_contexts("bibliotheque", choix_mat)
            contexte_exo = extract_pdf_text(doc_eleve) if doc_eleve else ""

            prompt = f"""
            Tu es Joris, l'assistant d'Anna (14 ans, 3ème). Ton ton est calme, bienveillant et structuré.
            Anna a accès à Lumni et YouTube Premium. 
            
            DURÉE : {duree} | MATIÈRES : {', '.join(choix_mat)}
            
            MISSION :
            1. Propose des recherches spécifiques Lumni/YouTube pour 60% du temps.
            2. Utilise les PDF officiels pour la théorie : {contexte_bib}
            3. Sois très encourageant et utilise des emojis.
            4. FINIS PAR : '### 📝 Ton petit défi' (3 questions de compréhension).
            """

            try:
                response = model.generate_content(prompt)
                st.session_state['resp'] = response.text
                st.session_state['q'] = besoin
            except Exception as e:
                st.error(f"Erreur avec le modèle Pro : {e}")

# --- 5. SUIVI ET EXPORT ---

if 'resp' in st.session_state:
    st.markdown("---")
    st.subheader("📊 Ta progression")
    c1, c2, c3 = st.columns(3)
    with c1: v = st.checkbox("Vidéo trouvée 📺")
    with c2: l = st.checkbox("Cours compris 📖")
    with c3: d = st.checkbox("Défi terminé ✅")
    st.progress(sum([v, l, d]) / 3)
    
    col_l, col_r = st.columns(2)
    with col_l:
        q = st.session_state['q']
        st.link_button("🔍 Chercher sur Lumni", f"https://www.lumni.fr/recherche?query={q}")
        st.link_button("🎥 YouTube Premium", f"https://www.youtube.com/results?search_query={q}")
    with col_r:
        pdf_data = create_pdf(st.session_state['resp'])
        st.download_button("📥 Télécharger ma fiche (PDF)", data=pdf_data, file_name="ma_seance.pdf")

    st.markdown("---")
    st.markdown(st.session_state['resp'])
