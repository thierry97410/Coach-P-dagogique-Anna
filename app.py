import streamlit as st
import pandas as pd
import os
from PyPDF2 import PdfReader
import google.generativeai as genai
from fpdf import FPDF

# --- 1. CONFIGURATION VISUELLE (LUMIÈRE TOTALE) ---
st.set_page_config(page_title="Anna : Mon Assistant", layout="wide")

st.markdown("""
    <style>
    :root { color-scheme: light; }
    .stApp { background-color: #F0FDF4 !important; color: #1E3A8A !important; }
    [data-testid="stSidebar"] { background-color: #E0F2FE !important; border-right: 2px solid #BAE6FD !important; }
    
    /* On force le BLANC sur absolument TOUTES les boîtes de saisie */
    div[data-baseweb="select"], div[data-baseweb="input"], textarea, 
    div[data-testid="stFileUploader"], .stMultiSelect, div[role="listbox"],
    div[data-baseweb="popover"] {
        background-color: white !important;
        color: #1E3A8A !important;
        border: 2px solid #BFDBFE !important;
        border-radius: 10px !important;
    }
    
    /* Fix pour le texte noir sur fond noir dans les menus */
    span, p, label, li, div, input, textarea { color: #1E3A8A !important; }

    h1, h2, h3 { color: #1E40AF !important; font-family: 'Segoe UI', sans-serif !important; }

    .stButton>button { 
        background-color: #3B82F6 !important; color: white !important; 
        border-radius: 50px !important; padding: 0.8rem 2rem !important; border: none !important;
        font-weight: bold !important;
    }
    header, footer { visibility: hidden !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONFIGURATION MOTEUR ---
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Clé API manquante.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
# Utilisation de la version Flash 2.5 (plus robuste pour ton quota)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- 3. FONCTIONS ---

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
    return combined_text[:100000]

# --- 4. INTERFACE ---

st.title("🎓 Anna : mon assistant pédagogique")

# Chargement du programme
CSV_PATH = "bibliotheque/programme.csv"
if os.path.exists(CSV_PATH):
    df = pd.read_csv(CSV_PATH, sep=",")
    df.columns = df.columns.str.strip()
else:
    st.error("Fichier programme.csv introuvable.")
    st.stop()

with st.sidebar:
    st.header("📋 Mon Parcours Scolaire")
    
    matieres = df["Matiere"].unique()
    choix_mat = st.selectbox("Quelle matière étudions-nous ?", matieres)
    
    # Filtrage des chapitres pour la matière choisie
    chapitres_matiere = df[df["Matiere"] == choix_mat]["Chapitre"].tolist()
    
    st.write("---")
    st.write("**Progression suggérée :**")
    # Simulation d'un prof qui guide Anna chapitre par chapitre
    choix_chap = st.radio("Chapitre actuel :", chapitres_matiere)
    
    st.write("---")
    duree = st.select_slider("Temps disponible :", options=["15 min", "30 min", "45 min", "1h", "1h30"], value="30 min")
    doc_eleve = st.file_uploader("📂 Joindre un exercice (PDF)", type="pdf")

st.subheader(f"📖 {choix_mat} : {choix_chap}")
st.write(f"Joris va t'aider à maîtriser ce chapitre en {duree}. De quoi as-tu besoin précisément ?")

besoin = st.text_area("Ex: 'Explique-moi les bases', 'Aide-moi pour l'exercice ci-joint', 'Fais-moi un quiz'...", height=100)

if st.button("🚀 Lancer la leçon"):
    with st.spinner("Joris prépare ton cours..."):
        contexte_bib = load_all_contexts("bibliotheque", [choix_mat])
        contexte_exo = extract_pdf_text(doc_eleve) if doc_eleve else ""

        prompt = f"""
        Tu es Joris, le tuteur d'Anna (3ème). Tu dois agir comme un professeur qui suit le programme officiel.
        MATIÈRE : {choix_mat}
        CHAPITRE : {choix_chap}
        TEMPS IMPARTI : {duree}
        
        CONTEXTE : {contexte_bib}
        DEMANDE : {besoin} | {contexte_exo}
        
        MISSION :
        1. Explique la notion du chapitre de manière structurée et progressive.
        2. Propose 1 recherche Lumni/YouTube spécifique pour illustrer le cours.
        3. Termine par : '### 📝 Le défi de compréhension' (3 questions).
        """

        try:
            response = model.generate_content(prompt)
            st.session_state['resp'] = response.text
            st.session_state['q'] = besoin
        except Exception as e:
            st.error(f"Erreur technique : {e}")

# --- 5. SUIVI ---

if 'resp' in st.session_state:
    st.markdown("---")
    st.subheader("📊 Validation de la séance")
    c1, c2, c3 = st.columns(3)
    with c1: v = st.checkbox("J'ai vu la vidéo 📺")
    with c2: l = st.checkbox("J'ai compris la notion 📖")
    with c3: d = st.checkbox("J'ai réussi le défi ✅")
    st.progress(sum([v, l, d]) / 3)
    
    col_l, col_r = st.columns(2)
    with col_l:
        st.link_button("🔍 Lumni", f"https://www.lumni.fr/recherche?query={choix_mat} {choix_chap}")
        st.link_button("🎥 YouTube", f"https://www.youtube.com/results?search_query=3eme {choix_mat} {choix_chap}")
    with col_r:
        pdf_data = create_pdf(st.session_state['resp'])
        st.download_button("📥 Enregistrer ma fiche (PDF)", data=pdf_data, file_name=f"cours_{choix_mat}.pdf")

    st.markdown("---")
    st.markdown(st.session_state['resp'])
