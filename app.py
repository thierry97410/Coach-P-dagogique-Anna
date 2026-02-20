import streamlit as st
import pandas as pd
import os
from PyPDF2 import PdfReader
import google.generativeai as genai
from fpdf import FPDF

# --- 1. DESIGN "CIEL & CLARTÉ" ---
st.set_page_config(page_title="Anna : Mon Assistant", layout="wide")

st.markdown("""
    <style>
    /* Fond très clair et doux */
    .stApp { background-color: #F8FAFC; color: #1E3A8A; }
    
    /* Sidebar douce */
    [data-testid="stSidebar"] { background-color: #E0F2FE; border-right: 2px solid #BAE6FD; }
    
    /* Titres en bleu profond */
    h1, h2, h3 { color: #1E40AF !important; font-family: 'Segoe UI', sans-serif; }
    
    /* Bouton principal en bleu ciel */
    .stButton>button { 
        background-color: #3B82F6; color: white; 
        font-weight: bold; border-radius: 12px; border: none;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .stButton>button:hover { background-color: #2563EB; }
    
    /* Champs de saisie blancs et nets */
    .stTextArea textarea, .stTextInput input { 
        background-color: white !important; color: #1E3A8A !important; 
        border: 1px solid #BFDBFE !important; border-radius: 10px !important;
    }
    
    /* Barre de progression */
    .stProgress > div > div > div > div { background-color: #10B981; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONFIGURATION API ---
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Clé API manquante dans les secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-pro')

# --- 3. FONCTIONS TECHNIQUES ---

def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    # Nettoyage des caractères spéciaux pour le PDF
    clean_text = text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 10, txt=clean_text)
    return pdf.output(dest='S').encode('latin-1')

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

# --- 4. INTERFACE ---

st.title("🌟 Anna : mon assistant pédagogique")

# Chargement CSV
CSV_PATH = "bibliotheque/programme.csv"
if os.path.exists(CSV_PATH):
    df = pd.read_csv(CSV_PATH, sep=",")
    df.columns = df.columns.str.strip()
else:
    st.stop()

with st.sidebar:
    st.header("📋 Ma Session")
    matieres_dispos = df["Matiere"].unique()
    choix_matieres = st.multiselect("Matières :", matieres_dispos, default=[matieres_dispos[0]])
    
    # Durée intelligente
    nb_mat = len(choix_matieres)
    d_min = 15 if nb_mat <= 1 else (30 if nb_mat == 2 else 45)
    duree = st.select_slider("Durée prévue :", options=["15 min", "30 min", "45 min", "1h", "1h30"], value=f"{d_min} min")
    
    supports = st.multiselect("Préférences :", ["Écrit", "Vidéo", "Mixte"], default=["Mixte"])
    doc_eleve = st.file_uploader("Document à joindre", type="pdf")

besoin = st.text_area("Sur quoi veux-tu te concentrer aujourd'hui, Anna ?", height=100)

if st.button("🚀 Lancer la séance"):
    if not besoin and not doc_eleve:
        st.info("Dis-moi juste ce que tu souhaites apprendre !")
    else:
        with st.spinner("Je prépare ton univers de travail..."):
            contexte_bib = load_all_contexts("bibliotheque", choix_matieres)
            contexte_exo = extract_pdf_text(doc_eleve) if doc_eleve else ""

            prompt = f"""
            Tu es Joris, l'assistant d'Anna. 
            DURÉE : {duree} | MATIÈRES : {', '.join(choix_matieres)} | SUPPORTS : {', '.join(supports)}
            
            MISSION :
            1. Si 'Vidéo' est choisi, propose 2 recherches précises sur Lumni et YouTube (60% du temps).
            2. Utilise le CONTEXTE OFFICIEL pour le reste : {contexte_bib}
            3. Sois encourageant, utilise des emojis, et sois très lisible.
            4. FINIS PAR : '### 📝 Ton petit défi' (3 questions).
            """

            response = model.generate_content(prompt)
            st.session_state['last_resp'] = response.text
            st.session_state['q_query'] = besoin

# --- 5. JOURNAL DE BORD ET PROGRESSION ---

if 'last_resp' in st.session_state:
    st.markdown("---")
    
    # Barre de progression visuelle
    st.subheader("📊 Ta progression sur cette séance")
    c1 = st.checkbox("J'ai trouvé la vidéo (Lumni/YouTube) 📺")
    c2 = st.checkbox("J'ai lu et compris l'explication 📖")
    c3 = st.checkbox("J'ai terminé le défi final ✅")
    
    score = sum([c1, c2, c3])
    st.progress(score / 3)
    if score == 3: st.success("Bravo Anna ! Séance terminée avec succès. ✨")

    # Liens et PDF
    col_l, col_r = st.columns(2)
    with col_l:
        q = st.session_state['q_query']
        st.link_button("🔍 Chercher sur Lumni", f"https://www.lumni.fr/recherche?query={q}")
        st.link_button("🎥 YouTube Premium", f"https://www.youtube.com/results?search_query={q}")
    
    with col_r:
        pdf_data = create_pdf(st.session_state['last_resp'])
        st.download_button("📥 Télécharger la fiche (PDF)", data=pdf_data, file_name="ma_seance.pdf", mime="application/pdf")

    st.markdown("---")
    st.markdown(st.session_state['last_resp'])
