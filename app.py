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

if 'current_mat' not in st.session_state: st.session_state.current_mat = None
if 'current_chap' not in st.session_state: st.session_state.current_chap = None
if 'session_complete' not in st.session_state: st.session_state.session_complete = False

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Clé API manquante dans les secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

# --- 2. FONCTIONS TECHNIQUES ---

def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)
    clean_text = text.replace('**', '').replace('#', '').replace('`', '')
    clean_text = clean_text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 8, txt=clean_text)
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
    st.error("Fichier programme.csv manquant.")
    st.stop()

# Synchronisation navigation
if st.session_state.current_mat is None: st.session_state.current_mat = df["Matiere"].unique()[0]
if st.session_state.current_chap is None: st.session_state.current_chap = df[df["Matiere"] == st.session_state.current_mat]["Chapitre"].tolist()[0]

with st.sidebar:
    st.header("⚙️ Pilotage")
    choix_mat = st.selectbox("Matière :", df["Matiere"].unique(), 
                             index=list(df["Matiere"].unique()).index(st.session_state.current_mat), key="mat_nav")
    chapitres = df[df["Matiere"] == choix_mat]["Chapitre"].tolist()
    choix_chap = st.radio("Chapitre :", chapitres, 
                          index=chapitres.index(st.session_state.current_chap) if st.session_state.current_chap in chapitres else 0, key="chap_nav")
    
    st.session_state.current_mat = choix_mat
    st.session_state.current_chap = choix_chap

    st.divider()
    st.write("**Esthétique & Analyse :**")
    theme_mermaid = st.selectbox("Style des infographies :", ["default", "forest", "dark", "neutral"])
    angle = st.selectbox("Angle d'attaque :", ["📜 Par l'Histoire", "🧠 Par la Logique", "🛠 Par l'Application"])
    
    st.divider()
    duree = st.select_slider("Densité :", options=["15 min", "30 min", "1h", "1h30"], value="30 min")
    doc_eleve = st.file_uploader("📂 Support PDF", type="pdf")

# --- 4. L'ESPACE D'ANNA ---

st.subheader(f"📍 Séance : {st.session_state.current_chap}")
besoin_anna = st.text_area("Anna, dis à Joris ce que tu as sur le cœur ou tes questions :", height=80)

col_actions = st.columns([1, 1, 3])
with col_actions[0]: lancer = st.button("🚀 Lancer l'exploration")
with col_actions[1]: pause_zen = st.button("🧘 Pause Zen")

if lancer:
    st.session_state.session_complete = False
    with st.spinner("Joris tisse les liens et dessine tes structures..."):
        contexte_bib, liste_sources = load_all_contexts("bibliotheque", st.session_state.current_mat)
        contexte_exo = extract_pdf_text(doc_eleve) if doc_eleve else ""

        prompt = f"""
        Tu es Joris, l'allié d'Anna (14 ans, HPI). 
        Anna a besoin de complexité, de sens et d'intégrité intellectuelle.
        
        MESSAGE D'ANNA : "{besoin_anna}"
        SÉANCE : {st.session_state.current_chap} ({st.session_state.current_mat}) | ANGLE : {angle}.
        
        INSTRUCTIONS DE MISE EN FORME :
        - Utilise des titres de tailles variées (# , ## , ###).
        - Mets en **gras** les concepts essentiels.
        - Génère DEUX infographies Mermaid (```mermaid ... ```) : 
            1. Une pour la STRUCTURE LOGIQUE (mindmap ou graph TD).
            2. Une pour la CHRONOLOGIE HISTORIQUE (timeline ou graph LR).
        
        STRUCTURE DE LA RÉPONSE :
        1. # Accueil & Sens : Pourquoi ce sujet est fondamental.
        2. # Exploration Approfondie : Analyse dense basée sur {contexte_bib}.
        3. ## 📖 Le Lexique des Curieux : Glossaire précis des termes complexes.
        4. ## Interconnexions : Pont avec une autre discipline.
        5. ## Support Humain (Vidéo) : Titre précis.
        6. ## L'Enquête de l'Esprit : Défi d'analyse critique.
        7. # 🧠 Analyse Logique (Infographie) : Bloc Mermaid 1.
        8. # ⏳ Analyse Chronologique (Infographie) : Bloc Mermaid 2.
        9. ## RECO:[NOM_MATIERE]|[NOM_CHAPITRE] (Pour la suite).
        10. ### Sources & Crédits : Fichiers {', '.join(liste_sources)} et auteurs.
        """
        try:
            response = model.generate_content(prompt)
            st.session_state['resp'] = response.text
            reco_match = re.search(r"RECO:(.*?)\|(.*)", response.text)
            if reco_match:
                st.session_state['reco_data'] = (reco_match.group(1).strip(), reco_match.group(2).strip())
        except Exception as e:
            st.error(f"Erreur : {e}")

# --- 5. AFFICHAGE ---

if 'resp' in st.session_state:
    st.divider()
    
    # Parsing des blocs Mermaid pour injecter le thème choisi
    full_text = st.session_state['resp']
    parts = re.split(r'(```mermaid.*?```)', full_text, flags=re.DOTALL)
    
    for part in parts:
        if part.startswith('```mermaid'):
            mermaid_code = part.replace('```mermaid', '').replace('```', '').strip()
            # Injection du thème
            theme_config = f"%%{{init: {{'theme': '{theme_mermaid}'}}}}%%\n"
            final_mermaid = theme_config + mermaid_code
            
            with st.expander("🔍 Agrandir l'infographie (Plein écran)", expanded=True):
                st.mermaid(final_mermaid)
        else:
            # Nettoyage de la recommandation pour ne pas l'afficher deux fois
            clean_part = re.sub(r'RECO:.*?\|.*', '', part)
            st.markdown(clean_part)
    
    st.divider()
    if not st.session_state.session_complete:
        if st.button("✨ J'ai terminé cette exploration"):
            st.session_state.session_complete = True
            st.rerun()
    else:
        if 'reco_data' in st.session_state:
            m, c = st.session_state.reco_data
            if st.button(f"➡️ Suivre le fil vers : {c} ({m})"):
                st.session_state.current_mat, st.session_state.current_chap = m, c
                st.session_state.session_complete = False
                st.rerun()

    col_f = st.columns(2)
    with col_f[0]:
        st.link_button("🎥 Voir la vidéo humaine", f"[https://www.youtube.com/results?search_query=3eme](https://www.youtube.com/results?search_query=3eme) {st.session_state.current_mat} {st.session_state.current_chap}")
    with col_f[1]:
        pdf_bytes = create_pdf(st.session_state['resp'])
        st.download_button("📥 Fiche PDF", data=pdf_bytes, file_name=f"Anna_{st.session_state.current_mat}.pdf")
