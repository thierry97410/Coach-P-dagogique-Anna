import streamlit as st
import pandas as pd
import os
from PyPDF2 import PdfReader
import google.generativeai as genai

# --- 1. CONFIGURATION VISUELLE ET TECHNIQUE ---
st.set_page_config(page_title="Le Salon d'Anna", layout="wide")

# Injection de style pour adoucir l'interface (Anna-friendly)
st.markdown("""
    <style>
    .stApp { background-color: #F0F4F8; }
    .stButton>button { background-color: #4A90E2; color: white; border-radius: 20px; border: none; }
    .stTextInput>div>div>input { border-radius: 15px; }
    h1 { color: #2C3E50; font-family: 'Helvetica Neue', sans-serif; }
    .stAlert { border-radius: 15px; border: none; }
    </style>
    """, unsafe_allow_html=True)

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Clé API manquante. Demande à Thierry de vérifier les Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-pro')

# --- 2. LOGIQUE DE LECTURE ---

def extract_pdf_text(file):
    try:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content: text += content + "\n"
        return text
    except: return ""

def get_subject_content(folder, matiere):
    """Charge les sources. Si erreur, affiche un message doux mais bloque."""
    prefix = matiere[:4].upper()
    if not os.path.exists(folder):
        st.info(f"✨ Oh ! Le dossier '{folder}' n'est pas encore prêt. Thierry doit le créer.")
        st.stop()
    
    files = [f for f in os.listdir(folder) if f.upper().startswith(prefix) and f.lower().endswith(".pdf")]
    
    if not files:
        # Erreur stylisée, moins agressive que le rouge 'crash'
        st.warning(f"🍃 **Petit contretemps** : Je n'ai pas trouvé le cours de '{matiere}' dans ma bibliothèque. Thierry doit vérifier le nom des fichiers (préfixe {prefix}_).")
        st.stop()
    
    full_text = ""
    for filename in files:
        with open(os.path.join(folder, filename), "rb") as f:
            full_text += extract_pdf_text(f)
    return full_text[:100000]

# --- 3. INTERFACE ---

st.title("🌟 Le Salon d'apprentissage d'Anna")
st.write(f"Bonjour Anna ! Prête pour une petite séance ? Choisis ta matière et posons-nous.")

CSV_PATH = "bibliotheque/programme.csv"
if os.path.exists(CSV_PATH):
    df_prog = pd.read_csv(CSV_PATH, sep=",")
    df_prog.columns = df_prog.columns.str.strip()
else:
    st.error("Le fichier programme.csv est introuvable.")
    st.stop()

with st.sidebar:
    st.header("📍 Ton parcours")
    matieres = df_prog["Matiere"].unique()
    choix_mat = st.selectbox("On travaille quoi ?", matieres)
    
    chaps = df_prog[df_prog["Matiere"] == choix_mat]["Chapitre"].tolist()
    choix_chap = st.selectbox("Quel chapitre précisément ?", chaps)
    
    st.divider()
    doc_eleve = st.file_uploader("Un document à me montrer ? (PDF)", type="pdf")

# Zone de texte principale
question_anna = st.text_area("Dis-moi ce que tu veux comprendre aujourd'hui ou ce qui te pose problème :", 
                             placeholder="Ex: Je ne comprends pas bien comment calculer une aire...", height=100)

if st.button("✨ Commencer la séance"):
    if not question_anna and not doc_eleve:
        st.info("Dis-moi juste un petit mot sur ce que tu veux faire pour que je puisse t'aider !")
    else:
        with st.spinner("Je prépare tes explications..."):
            contexte_bib = get_subject_content("bibliotheque", choix_mat)
            contexte_exo = extract_pdf_text(doc_eleve) if doc_eleve else ""

            prompt = f"""
            Tu es Joris, le tuteur bienveillant d'Anna (14 ans, 3ème). 
            Elle travaille seule à la maison. Ton ton est amical, encourageant, clair, mais tu gardes la rigueur nécessaire.
            
            MATIÈRE : {choix_mat} | CHAPITRE : {choix_chap}
            SOURCES : {contexte_bib}
            TRAVAIL D'ANNA : {question_anna} | {contexte_exo}

            MISSION :
            1. Explique simplement la notion en utilisant les documents officiels.
            2. Aide-la pas à pas sans donner la solution.
            3. Utilise des emojis pour rendre le texte vivant.
            4. FINIS PAR : '### 💡 Le petit défi pour voir si tu as compris' (3 questions rapides).
            """

            try:
                response = model.generate_content(prompt)
                st.markdown("---")
                st.markdown(response.text)
            except Exception as e:
                st.error("L'IA se repose un instant. Réessaie dans une minute !")

# --- FIN ---
st.caption("Fait avec soin pour Anna.")
