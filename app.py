import streamlit as st
import pandas as pd
import os
from PyPDF2 import PdfReader
import google.generativeai as genai
from fpdf import FPDF

# --- 1. DESIGN "LAGON & MENTHE" (Haute Lisibilité Pastel) ---
st.set_page_config(page_title="Anna : Mon Assistant", layout="wide")

st.markdown("""
    <style>
    /* 1. FOND PRINCIPAL : Vert menthe très pâle */
    .stApp { 
        background-color: #F0FDF4 !important; 
        color: #164E63 !important; 
    }

    /* 2. SIDEBAR : Bleu lagon pastel */
    [data-testid="stSidebar"] { 
        background-color: #E0F2FE !important; 
        border-right: 2px solid #BAE6FD !important;
    }
    [data-testid="stSidebar"] * { color: #1E3A8A !important; }

    /* 3. TITRES : Bleu profond apaisant */
    h1, h2, h3 { 
        color: #1E40AF !important; 
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
    }

    /* 4. MULTISELECT & SELECTBOX : On tue le corail et le noir */
    /* Fond des cases de sélection */
    .stMultiSelect div, .stSelectbox div {
        background-color: white !important;
        color: #1E3A8A !important;
    }
    /* Les "tags" (matières sélectionnées) : Fond bleu ciel, texte marine */
    span[data-baseweb="tag"] {
        background-color: #BFDBFE !important;
        color: #1E3A8A !important;
        border: 1px solid #60A5FA !important;
    }
    /* La petite croix de suppression des tags */
    span[data-baseweb="tag"] span { color: #1E3A8A !important; }

    /* 5. DRAG & DROP : Blanc pur, contour vert menthe */
    section[data-testid="stFileUploader"] {
        background-color: white !important;
        border: 2px dashed #10B981 !important;
        border-radius: 15px !important;
    }
    section[data-testid="stFileUploader"] * { color: #065F46 !important; }

    /* 6. INPUTS & TEXTAREA */
    .stTextArea textarea { 
        background-color: white !important; 
        color: #1E3A8A !important; 
        border: 2px solid #BFDBFE !important;
    }

    /* 7. BOUTON : Bleu Roi, texte blanc */
    .stButton>button { 
        background-color: #3B82F6 !important; 
        color: white !important; 
        border-radius: 12px !important;
        border: none !important;
        padding: 0.5rem 2rem !important;
        font-weight: bold !important;
    }
    .stButton>button:hover { background-color: #2563EB !important; }

    /* 8. BARRE DE PROGRESSION : Vert émeraude */
    .stProgress > div > div > div > div { background-color: #10B981 !important; }

    /* Masquer les éléments parasites de Streamlit */
    header { visibility: hidden !important; }
    footer { visibility: hidden !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIQUE TECHNIQUE ---
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

# --- 3. INTERFACE ---

st.title("🎓 Anna : mon assistant pédagogique")

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
    
    # Durée automatique + sécurité
    nb_mat = len(choix_matieres)
    d_min = 15 if nb_mat <= 1 else (30 if nb_mat == 2 else 45)
    duree = st.select_slider("Durée de la séance :", options=["15 min", "30 min", "45 min", "1h", "1h30"], value=f"{d_min} min")
    
    supports = st.multiselect("Supports :", ["Écrit", "Vidéo", "Mixte"], default=["Mixte"])
    st.markdown("---")
    doc_eleve = st.file_uploader("📂 Document à joindre (PDF)", type="pdf")

besoin = st.text_area("Sur quoi veux-tu te concentrer aujourd'hui, Anna ?", height=120)

if st.button("🚀 Commencer ma séance"):
    if not besoin and not doc_eleve:
        st.info("Dis-moi juste un petit mot sur ce que tu veux faire !")
    else:
        with st.spinner("Je prépare ton parcours sur mesure..."):
            contexte_bib = load_all_contexts("bibliotheque", choix_matieres)
            contexte_exo = extract_pdf_text(doc_eleve) if doc_eleve else ""

            prompt = f"""
            Tu es Joris, le tuteur d'Anna (14 ans). Ton ton est calme, encourageant et structuré.
            Anna a accès à Lumni et YouTube Premium. 
            
            SÉANCE : {duree} | MATIÈRES : {', '.join(choix_matieres)} | SUPPORTS : {', '.join(supports)}
            
            CONSIGNES :
            1. Si 'Vidéo' ou 'Mixte' : 60% du temps est dédié à 1 ou 2 vidéos spécifiques (donne les titres exacts pour Lumni/Youtube).
            2. Utilise les PDF officiels pour le contenu : {contexte_bib}
            3. Organise la séance pour qu'elle respecte les {duree}.
            4. FINIS PAR : '### 📝 Ton petit défi' (3 questions rapides).
            """

            response = model.generate_content(prompt)
            st.session_state['last_resp'] = response.text
            st.session_state['q_query'] = besoin

# --- 4. SUIVI DE PROGRESSION ---

if 'last_resp' in st.session_state:
    st.markdown("---")
    st.subheader("📊 Ta progression")
    
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1: c1 = st.checkbox("Vidéo trouvée 📺")
    with col_c2: c2 = st.checkbox("Cours compris 📖")
    with col_c3: c3 = st.checkbox("Défi terminé ✅")
    
    score = sum([c1, c2, c3])
    st.progress(score / 3)
    
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
