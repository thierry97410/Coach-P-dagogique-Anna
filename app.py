import streamlit as st
import pandas as pd
import os
from PyPDF2 import PdfReader
import google.generativeai as genai
from fpdf import FPDF

# --- 1. LE BLINDAGE CSS (Lumière Totale & Anti-Mode Sombre) ---
st.set_page_config(page_title="Anna : Mon Assistant", layout="wide")

st.markdown("""
    <style>
    /* 1. FORCE LE FOND GLOBAL */
    .stApp, [data-testid="stAppViewContainer"] {
        background-color: #F0FDF4 !important;
        color: #1E3A8A !important;
    }

    /* 2. FORCE LA SIDEBAR */
    [data-testid="stSidebar"], [data-testid="stSidebarContent"] {
        background-color: #E0F2FE !important;
        border-right: 2px solid #BAE6FD !important;
    }
    [data-testid="stSidebar"] * { color: #1E3A8A !important; }

    /* 3. LE MUSCLAGE DES INPUTS (Select, MultiSelect, TextArea) */
    /* On force le fond blanc sur TOUS les composants de saisie */
    div[data-baseweb="select"], div[data-baseweb="input"], textarea, .stSelectbox, .stMultiSelect {
        background-color: white !important;
        color: #1E3A8A !important;
        border-radius: 10px !important;
    }
    
    /* On force la couleur du texte à l'intérieur des listes et des champs */
    input, textarea, div[role="listbox"], div[data-baseweb="popover"] * {
        color: #1E3A8A !important;
        background-color: white !important;
    }

    /* 4. FIX POUR LE DRAG & DROP (La case noire) */
    [data-testid="stFileUploader"], [data-testid="stFileUploadDropzone"] {
        background-color: white !important;
        border: 2px dashed #10B981 !important;
        border-radius: 15px !important;
    }
    [data-testid="stFileUploader"] * { color: #1E3A8A !important; }
    
    /* 5. LES ÉTIQUETTES (Tags des matières) */
    span[data-baseweb="tag"] {
        background-color: #BFDBFE !important;
        color: #1E3A8A !important;
        border: 1px solid #60A5FA !important;
    }

    /* 6. LES TITRES ET LABELS */
    h1, h2, h3, label, p, .stMarkdown {
        color: #1E40AF !important;
        font-family: 'Segoe UI', sans-serif !important;
    }

    /* 7. LES BOUTONS */
    .stButton>button {
        background-color: #3B82F6 !important;
        color: white !important;
        border-radius: 12px !important;
        font-weight: bold !important;
        border: none !important;
    }
    
    /* Masquer les menus Streamlit */
    header, footer, #MainMenu { visibility: hidden !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIQUE API & FONCTIONS ---
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Clé API manquante.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-pro')

def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
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
                combined_text += f"\n--- {mat} ---\n" + extract_pdf_text(f)
    return combined_text[:150000]

# --- 3. INTERFACE ANNA ---

st.title("🎓 Anna : mon assistant pédagogique")

# Chargement du programme
CSV_PATH = "bibliotheque/programme.csv"
if os.path.exists(CSV_PATH):
    df = pd.read_csv(CSV_PATH, sep=",")
    df.columns = df.columns.str.strip()
else:
    st.stop()

with st.sidebar:
    st.header("📋 Ma Session")
    matieres_dispos = df["Matiere"].unique()
    choix_matieres = st.multiselect("Matières à travailler :", matieres_dispos, default=[matieres_dispos[0]])
    
    # Durée automatique sécurisée
    nb_mat = len(choix_matieres)
    d_min = 15 if nb_mat <= 1 else (30 if nb_mat == 2 else 45)
    duree = st.select_slider("Durée de la séance :", options=["15 min", "30 min", "45 min", "1h", "1h30"], value=f"{d_min} min")
    
    supports = st.multiselect("Supports préférés :", ["Écrit", "Vidéo", "Mixte"], default=["Mixte"])
    st.markdown("---")
    doc_eleve = st.file_uploader("📂 Document à joindre (PDF)", type="pdf")

# LA CASE DE DIALOGUE (Ce que nous allons faire ensemble)
st.subheader("📝 Ce que nous allons faire ensemble :")
besoin = st.text_area("Explique ici tes besoins ou pose ta question :", 
                      placeholder="Ex: Aide-moi à comprendre l'exercice 4 du chapitre sur les fractions...", height=120)

if st.button("🚀 Commencer ma séance"):
    if not besoin and not doc_eleve:
        st.info("Dis-moi ce que tu veux travailler pour que Joris puisse t'aider !")
    else:
        with st.spinner("Je prépare ton univers de travail..."):
            contexte_bib = load_all_contexts("bibliotheque", choix_matieres)
            contexte_exo = extract_pdf_text(doc_eleve) if doc_eleve else ""

            prompt = f"""
            Tu es Joris, l'assistant d'Anna. 
            SÉANCE : {duree} | MATIÈRES : {', '.join(choix_matieres)} | SUPPORTS : {', '.join(supports)}
            
            MISSION :
            1. Si 'Vidéo' ou 'Mixte' : propose 2 titres précis de vidéos Lumni/YouTube (60% du temps).
            2. Utilise les PDF officiels pour le contenu théorique : {contexte_bib}
            3. Sois très encourageant, clair et utilise des emojis.
            4. FINIS PAR : '### 📝 Ton petit défi' (3 questions de compréhension).
            """

            response = model.generate_content(prompt)
            st.session_state['last_resp'] = response.text
            st.session_state['q_query'] = besoin

# --- 4. SUIVI DE PROGRESSION ---

if 'last_resp' in st.session_state:
    st.markdown("---")
    st.subheader("📊 Ta progression")
    
    c1, c2, c3 = st.columns(3)
    with c1: v_check = st.checkbox("Vidéo trouvée 📺")
    with c2: l_check = st.checkbox("Cours compris 📖")
    with c3: d_check = st.checkbox("Défi terminé ✅")
    
    st.progress(sum([v_check, l_check, d_check]) / 3)
    
    col_l, col_r = st.columns(2)
    with col_l:
        q = st.session_state['q_query']
        st.link_button("🔍 Chercher sur Lumni", f"https://www.lumni.fr/recherche?query={q}")
        st.link_button("🎥 Chercher sur YouTube", f"https://www.youtube.com/results?search_query={q}")
    
    with col_r:
        pdf_data = create_pdf(st.session_state['last_resp'])
        st.download_button("📥 Télécharger ma fiche (PDF)", data=pdf_data, file_name="ma_seance.pdf", mime="application/pdf")

    st.markdown("---")
    st.markdown(st.session_state['last_resp'])
