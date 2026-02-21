import streamlit as st
import pandas as pd
import os
import io
import re
from PyPDF2 import PdfReader
import google.generativeai as genai
from fpdf import FPDF

# --- 1. CONFIGURATION & SESSION STATE ---
st.set_page_config(page_title="L'Espace d'Anna", layout="wide")

# Initialisation des variables de navigation
if 'current_mat' not in st.session_state:
    st.session_state.current_mat = None
if 'current_chap' not in st.session_state:
    st.session_state.current_chap = None
if 'session_complete' not in st.session_state:
    st.session_state.session_complete = False

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Clé API manquante.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

# --- 2. FONCTIONS TECHNIQUES ---

def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    clean_text = text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 10, txt=clean_text)
    return bytes(pdf.output())

def extract_pdf_text(file):
    try:
        reader = PdfReader(file)
        return "".join([p.extract_text() for p in reader.pages if p.extract_text()])
    except: return ""

def load_all_contexts(folder, matiere):
    combined_text = ""
    sources_utilisees = []
    if not os.path.exists(folder): return "", []
    prefix = matiere[:4].upper()
    files = [f for f in os.listdir(folder) if f.upper().startswith(prefix) and f.lower().endswith(".pdf")]
    for filename in files:
        with open(os.path.join(folder, filename), "rb") as f:
            combined_text += f"\n--- SOURCE : {filename} ---\n"
            combined_text += extract_pdf_text(f)
            sources_utilisees.append(filename)
    return combined_text[:150000], sources_utilisees

# --- 3. INTERFACE DE PILOTAGE ---

st.title("🎓 L'Espace d'Exploration d'Anna")

CSV_PATH = "bibliotheque/programme.csv"
if os.path.exists(CSV_PATH):
    df = pd.read_csv(CSV_PATH, sep=",")
    df.columns = df.columns.str.strip()
else:
    st.error("Programme CSV manquant.")
    st.stop()

# Synchronisation de la navigation
if st.session_state.current_mat is None:
    st.session_state.current_mat = df["Matiere"].unique()[0]
if st.session_state.current_chap is None:
    st.session_state.current_chap = df[df["Matiere"] == st.session_state.current_mat]["Chapitre"].tolist()[0]

with st.sidebar:
    st.header("⚙️ Pilotage")
    choix_mat = st.selectbox("Matière :", df["Matiere"].unique(), 
                             index=list(df["Matiere"].unique()).index(st.session_state.current_mat),
                             key="mat_nav")
    
    chapitres = df[df["Matiere"] == choix_mat]["Chapitre"].tolist()
    choix_chap = st.radio("Chapitre :", chapitres, 
                          index=chapitres.index(st.session_state.current_chap) if st.session_state.current_chap in chapitres else 0,
                          key="chap_nav")
    
    st.session_state.current_mat = choix_mat
    st.session_state.current_chap = choix_chap

    st.divider()
    st.write("**Préférences d'Anna :**")
    format_synthese = st.selectbox("Format de synthèse :", ["Carte Mentale", "Tableau de synthèse"])
    angle = st.selectbox("Angle d'attaque :", ["📜 Histoire", "🧠 Logique", "🛠 Application"])
    duree = st.select_slider("Densité :", options=["15 min", "30 min", "1h", "1h30"], value="30 min")
    doc_eleve = st.file_uploader("📂 Document support (PDF)", type="pdf")

# --- 4. L'ESPACE D'ANNA ---

st.subheader(f"📍 Séance : {st.session_state.current_chap}")
besoin_anna = st.text_area("Message pour Joris :", placeholder="Une question ? Une envie ? Dis-moi tout...", height=80)

col_actions = st.columns([1, 1, 3])
with col_actions[0]: lancer = st.button("🚀 Lancer l'exploration")
with col_actions[1]: pause_zen = st.button("🧘 Pause Zen")

if lancer:
    st.session_state.session_complete = False # Reset au lancement
    with st.spinner("Joris tisse les liens de ta séance..."):
        contexte_bib, liste_sources = load_all_contexts("bibliotheque", st.session_state.current_mat)
        contexte_exo = extract_pdf_text(doc_eleve) if doc_eleve else ""

        prompt = f"""
        Tu es Joris, l'allié d'Anna (14 ans, HPI). Tu es un psycho-pédagogue curateur respectueux des créateurs humains.
        MESSAGE D'ANNA : "{besoin_anna}"
        SÉANCE : {st.session_state.current_chap} ({st.session_state.current_mat}) | ANGLE : {angle}.
        
        STRUCTURE DENSE :
        1. **Accueil & Sens** : Réponds à son message et explique l'utilité du sujet.
        2. **Approfondissement (Le Cours)** : Analyse complexe (sources : {contexte_bib}).
        3. **Le Lexique des Curieux** : Glossaire des termes techniques difficiles rencontrés.
        4. **Interconnexions** : Un lien fort avec une autre discipline.
        5. **Support Humain (Vidéo)** : Titre Lumni/YouTube précis.
        6. **L'Enquête de l'Esprit** : Défi d'analyse ou de logique.
        7. **### 📝 Synthèse : {format_synthese}** : Schéma textuel détaillé.
        8. **Sources & Crédits** : Fichiers {', '.join(liste_sources)} et auteurs.
        9. **La Suite Logique** : Suggère un chapitre d'une AUTRE matière lié logiquement.
           FORMAT RECOMMANDATION : "RECO:[NOM_MATIERE]|[NOM_CHAPITRE]"
        """
        try:
            response = model.generate_content(prompt)
            st.session_state['resp'] = response.text
            reco_match = re.search(r"RECO:(.*?)\|(.*)", response.text)
            if reco_match:
                st.session_state['reco_data'] = (reco_match.group(1).strip(), reco_match.group(2).strip())
        except Exception as e:
            st.error(f"Erreur : {e}")

# --- 5. RÉSULTATS & NAVIGATION FLUIDE ---

if 'resp' in st.session_state:
    st.divider()
    st.markdown(st.session_state['resp'])
    
    st.divider()
    st.subheader("🏁 Clap de fin")
    if not st.session_state.session_complete:
        if st.button("✨ J'ai terminé mon exploration"):
            st.session_state.session_complete = True
            st.rerun()
    else:
        st.success("Bravo Anna ! Tu as musclé tes connaissances aujourd'hui.")
        if 'reco_data' in st.session_state:
            mat_suivante, chap_suivant = st.session_state.reco_data
            if st.button(f"➡️ Suivre le fil vers : {chap_suivant} ({mat_suivante})"):
                st.session_state.current_mat = mat_suivante
                st.session_state.current_chap = chap_suivant
                st.session_state.session_complete = False
                st.rerun()

    col_dl = st.columns(2)
    with col_dl[0]:
        st.link_button("🔍 Chercher la vidéo", f"https://www.youtube.com/results?search_query=3eme {st.session_state.current_mat} {st.session_state.current_chap}")
    with col_dl[1]:
        pdf_bytes = create_pdf(st.session_state['resp'])
        st.download_button("📥 Enregistrer ma fiche", data=pdf_bytes, file_name=f"Anna_{st.session_state.current_mat}.pdf")
