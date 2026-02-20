import streamlit as st
import pandas as pd
import os
from PyPDF2 import PdfReader
import google.generativeai as genai
from fpdf import FPDF

# --- 1. DESIGN "SÉRÉNITÉ ET HAUTE LISIBILITÉ" ---
st.set_page_config(page_title="Anna : Mon Assistant", layout="wide")

st.markdown("""
    <style>
    /* 1. FOND PRINCIPAL : Blanc cassé très propre */
    .stApp { 
        background-color: #F0F7FF !important; 
        color: #1E3A8A !important; 
    }

    /* 2. SIDEBAR : Bleu ciel distinct pour ne pas se mélanger au fond */
    [data-testid="stSidebar"] { 
        background-color: #D1E9FF !important; 
        border-right: 3px solid #60A5FA !important;
    }
    [data-testid="stSidebar"] * { color: #1E3A8A !important; }

    /* 3. TITRES : Bleu Roi très lisible */
    h1, h2, h3, h4 { 
        color: #1D4ED8 !important; 
        font-family: 'Helvetica Neue', Arial, sans-serif !important;
        font-weight: 800 !important;
    }

    /* 4. DRAG & DROP (File Uploader) : On force le fond blanc et contour bleu */
    section[data-testid="stFileUploader"] {
        background-color: white !important;
        border: 2px dashed #3B82F6 !important;
        border-radius: 15px !important;
        padding: 20px !important;
    }
    section[data-testid="stFileUploader"] label { color: #1E3A8A !important; font-weight: bold !important; }
    section[data-testid="stFileUploader"] div div { color: #1E3A8A !important; }

    /* 5. INPUTS (Text Area, Selectbox) : Fond blanc, texte marine */
    .stTextArea textarea, .stTextInput input, .stSelectbox div { 
        background-color: white !important; 
        color: #1E3A8A !important; 
        border: 2px solid #BFDBFE !important;
        border-radius: 10px !important;
    }

    /* 6. BOUTONS : Bleu vif, texte blanc pur pour le contraste */
    .stButton>button { 
        background-color: #2563EB !important; 
        color: white !important; 
        font-weight: bold !important;
        font-size: 18px !important;
        border-radius: 50px !important;
        border: none !important;
        padding: 10px 24px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
    }
    .stButton>button:hover { background-color: #1D4ED8 !important; transform: scale(1.02); }

    /* 7. BARRE DE PROGRESSION : Vert émeraude */
    .stProgress > div > div > div > div { background-color: #10B981 !important; }

    /* 8. SUPPRESSION DU BANDEAU GITHUB/HEADER NOIR */
    header { visibility: hidden !important; }
    #MainMenu { visibility: hidden !important; }
    footer { visibility: hidden !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIQUE API & PDF ---
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Oups ! La clé API est manquante dans les secrets.")
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
                combined_text += f"\n--- SOURCE {mat} ---\n" + extract_pdf_text(f)
    return combined_text[:150000]

# --- 3. INTERFACE ---

st.title("🌟 Anna : mon assistant pédagogique")

CSV_PATH = "bibliotheque/programme.csv"
if os.path.exists(CSV_PATH):
    df = pd.read_csv(CSV_PATH, sep=",")
    df.columns = df.columns.str.strip()
else:
    st.error("Le fichier 'programme.csv' n'est pas dans le dossier 'bibliotheque'.")
    st.stop()

with st.sidebar:
    st.header("📋 Ma Session")
    mat_dispos = df["Matiere"].unique()
    choix_mat = st.multiselect("Quelles matières ?", mat_dispos, default=[mat_dispos[0]])
    
    # Durée automatique selon le nombre de matières
    n = len(choix_mat)
    d_auto = 15 if n <= 1 else (30 if n == 2 else 45)
    duree = st.select_slider("Durée prévue :", options=["15 min", "30 min", "45 min", "1h", "1h30"], value=f"{d_auto} min")
    
    supports = st.multiselect("Supports favoris :", ["Écrit", "Vidéo", "Mixte"], default=["Mixte"])
    st.markdown("---")
    doc_eleve = st.file_uploader("📂 Document à joindre", type="pdf")

besoin = st.text_area("Sur quoi souhaites-tu te concentrer aujourd'hui, Anna ?", height=120, placeholder="Ex: Aide-moi à comprendre l'exercice sur les séismes...")

if st.button("🚀 Commencer ma séance"):
    if not besoin and not doc_eleve:
        st.info("Explique-moi ce que tu veux faire pour que je puisse t'aider !")
    else:
        with st.spinner("Je prépare ton univers de travail..."):
            contexte_bib = load_all_contexts("bibliotheque", choix_mat)
            contexte_exo = extract_pdf_text(doc_eleve) if doc_eleve else ""

            prompt = f"""
            Tu es Joris, l'assistant d'Anna (3ème). 
            DURÉE : {duree} | MATIÈRES : {', '.join(choix_mat)} | SUPPORTS : {', '.join(supports)}
            
            MISSION :
            1. Si 'Vidéo' est choisi, propose des recherches précises sur Lumni/YouTube (60% du temps).
            2. Utilise les PDF officiels pour le reste : {contexte_bib}
            3. Sois très encourageant et lisible.
            4. FINIS PAR : '### 📝 Ton petit défi' (3 questions).
            """

            response = model.generate_content(prompt)
            st.session_state['resp'] = response.text
            st.session_state['q'] = besoin

# --- 4. JOURNAL DE BORD ET SUIVI ---

if 'resp' in st.session_state:
    st.markdown("---")
    st.subheader("📊 Ta progression")
    c1 = st.checkbox("J'ai trouvé la vidéo 📺")
    c2 = st.checkbox("J'ai bien lu les explications 📖")
    c3 = st.checkbox("J'ai fait le petit défi ✅")
    
    st.progress(sum([c1, c2, c3]) / 3)

    col1, col2 = st.columns(2)
    with col1:
        q = st.session_state['q']
        st.link_button("🔍 Chercher sur Lumni", f"https://www.lumni.fr/recherche?query={q}")
        st.link_button("🎥 Chercher sur YouTube", f"https://www.youtube.com/results?search_query={q}")
    
    with col2:
        pdf_data = create_pdf(st.session_state['resp'])
        st.download_button("📥 Télécharger ma fiche (PDF)", data=pdf_data, file_name="ma_seance.pdf", mime="application/pdf")

    st.markdown("---")
    st.markdown(st.session_state['resp'])
