import streamlit as st
import pandas as pd
import os
from PyPDF2 import PdfReader
import google.generativeai as genai
from fpdf import FPDF

# --- 1. DESIGN "SÉRÉNITÉ ET ÉVEIL" (Anti-Noir & Anti-Gris) ---
st.set_page_config(page_title="Anna : Mon Assistant", layout="wide")

st.markdown("""
    <style>
    :root { color-scheme: light; }
    .stApp { background-color: #F0FDF4 !important; color: #1E3A8A !important; }
    [data-testid="stSidebar"] { background-color: #E0F2FE !important; border-right: 2px solid #BAE6FD !important; }
    
    /* On force le BLANC sur les boîtes de saisie */
    div[data-baseweb="select"], div[data-baseweb="input"], textarea, 
    div[data-testid="stFileUploader"], .stMultiSelect, div[role="listbox"] {
        background-color: white !important;
        color: #1E3A8A !important;
        border: 2px solid #BFDBFE !important;
        border-radius: 10px !important;
    }
    
    /* Fix pour le texte */
    span, p, label, li, div, input, textarea { color: #1E3A8A !important; }
    h1, h2, h3 { color: #1E40AF !important; font-family: 'Segoe UI', sans-serif !important; }

    .stButton>button { 
        background-color: #3B82F6 !important; color: white !important; 
        border-radius: 50px !important; padding: 0.8rem 2rem !important;
        font-weight: bold !important; border: none !important;
    }
    header, footer { visibility: hidden !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONFIGURATION API ---
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Clé API manquante.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

# --- 3. FONCTIONS TECHNIQUES ---

def create_pdf(text):
    """Génère un PDF (fix pour fpdf2)."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    clean_text = text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 10, txt=clean_text)
    return pdf.output() # fpdf2 renvoie des bytes directement

def extract_pdf_text(file):
    try:
        reader = PdfReader(file)
        return "".join([p.extract_text() for p in reader.pages if p.extract_text()])
    except: return ""

def load_all_contexts(folder, matiere):
    """Charge les PDF de la bibliothèque selon la matière."""
    combined_text = ""
    if not os.path.exists(folder): return ""
    prefix = matiere[:4].upper()
    files = [f for f in os.listdir(folder) if f.upper().startswith(prefix) and f.lower().endswith(".pdf")]
    for filename in files:
        with open(os.path.join(folder, filename), "rb") as f:
            combined_text += extract_pdf_text(f)
    return combined_text[:120000]

# --- 4. INTERFACE ---

st.title("🎓 Anna : mon assistant pédagogique")

CSV_PATH = "bibliotheque/programme.csv"
if os.path.exists(CSV_PATH):
    df = pd.read_csv(CSV_PATH, sep=",")
    df.columns = df.columns.str.strip()
else:
    st.error("Fichier programme.csv introuvable.")
    st.stop()

with st.sidebar:
    st.header("📖 Programme de 3ème")
    matieres = df["Matiere"].unique()
    choix_mat = st.selectbox("Quelle matière travailles-tu ?", matieres)
    
    chapitres = df[df["Matiere"] == choix_mat]["Chapitre"].tolist()
    st.write("---")
    st.write("**Progression suggérée :**")
    choix_chap = st.radio("Sélectionne ton chapitre :", chapitres)
    
    st.divider()
    duree = st.select_slider("Temps de la séance :", options=["15 min", "30 min", "1h", "1h30"], value="30 min")
    doc_eleve = st.file_uploader("📂 Joindre un document (facultatif)", type="pdf")

# Zone de travail
st.subheader(f"📍 {choix_mat} : {choix_chap}")

if st.button("🚀 Lancer ma séance personnalisée"):
    with st.spinner("Joris prépare ton cours et tes surprises..."):
        contexte_bib = load_all_contexts("bibliotheque", choix_mat)
        contexte_exo = extract_pdf_text(doc_eleve) if doc_eleve else ""

        prompt = f"""
        Tu es Joris, le tuteur d'Anna (14 ans). Tu dois concevoir une séance de {duree} sur le chapitre : {choix_chap}.
        
        STRUCTURE OBLIGATOIRE DE TA RÉPONSE :
        1. **Introduction (Le but du jour)** : Présente le chapitre de façon motivante.
        2. **Le Cours (L'essentiel)** : Basé sur le contexte PDF : {contexte_bib}. Sois clair et visuel.
        3. **Support Ludique** : Propose un titre de vidéo précise (Lumni ou YouTube) à chercher.
        4. **L'exercice original** : Crée un exercice inédit, pas trop scolaire, basé sur le cours.
        5. **Le savais-tu ?** : Une anecdote rigolote ou surprenante en lien avec le sujet.
        6. **### 📝 Le Quiz final** : 3 questions rapides pour valider la séance.

        TON TON : Pédagogique, complice, encourageant. Utilise des emojis.
        """

        try:
            response = model.generate_content(prompt)
            st.session_state['resp'] = response.text
        except Exception as e:
            st.error(f"Erreur technique : {e}")

# --- 5. RÉSULTATS ---

if 'resp' in st.session_state:
    st.markdown("---")
    st.subheader("📊 Validation de ta séance")
    
    c1, c2, c3 = st.columns(3)
    with c1: st.checkbox("Recherche vidéo faite 📺")
    with c2: st.checkbox("Exercice terminé ✍️")
    with c3: st.checkbox("Quiz validé ✅")
    
    col_l, col_r = st.columns(2)
    with col_l:
        search_query = f"3eme {choix_mat} {choix_chap}"
        st.link_button("🔍 Chercher sur YouTube / Lumni", f"https://www.youtube.com/results?search_query={search_query}")
    
    with col_r:
        pdf_bytes = create_pdf(st.session_state['resp'])
        st.download_button("📥 Enregistrer ma fiche de cours (PDF)", data=pdf_bytes, file_name=f"Anna_{choix_mat}.pdf")

    st.markdown("---")
    st.markdown(st.session_state['resp'])
