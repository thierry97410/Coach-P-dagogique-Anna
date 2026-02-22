import streamlit as st
import pandas as pd
import os
import io
import re
from PyPDF2 import PdfReader
import google.generativeai as genai
from fpdf import FPDF
import streamlit.components.v1 as components

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="L'Espace d'Anna", layout="wide")

if 'resp' not in st.session_state: st.session_state.resp = None
if 'current_mat' not in st.session_state: st.session_state.current_mat = None
if 'current_chap' not in st.session_state: st.session_state.current_chap = None

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Clé API manquante dans les secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

# --- 2. FONCTIONS TECHNIQUES ---

def render_mermaid(code, theme="neutral"):
    """Rendu Mermaid via HTML/JS pour une robustesse maximale."""
    html = f"""
    <div class="mermaid" style="background-color: white; padding: 20px; border-radius: 10px;">
        {code}
    </div>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ startOnLoad: true, theme: '{theme}', securityLevel: 'loose' }});
    </script>
    """
    components.html(html, height=500, scrolling=True)

def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)
    # Nettoyage Markdown pour le PDF
    clean_text = re.sub(r'#+', '', text).replace('**', '').replace('`', '')
    clean_text = clean_text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 8, txt=clean_text)
    return bytes(pdf.output())

def load_context(folder, matiere):
    text = ""
    if not os.path.exists(folder): return ""
    prefix = matiere[:4].upper()
    files = [f for f in os.listdir(folder) if f.upper().startswith(prefix) and f.lower().endswith(".pdf")]
    for f_name in files:
        with open(os.path.join(folder, f_name), "rb") as f:
            reader = PdfReader(f)
            text += "".join([p.extract_text() for p in reader.pages if p.extract_text()])
    return text[:150000]

# --- 3. INTERFACE ---

st.title("🎓 L'Espace d'Exploration d'Anna")

CSV_PATH = "bibliotheque/programme.csv"
if os.path.exists(CSV_PATH):
    df = pd.read_csv(CSV_PATH, sep=",")
    df.columns = df.columns.str.strip()
else: st.stop()

if st.session_state.current_mat is None: st.session_state.current_mat = df["Matiere"].unique()[0]

with st.sidebar:
    st.header("⚙️ Pilotage")
    choix_mat = st.selectbox("Matière :", df["Matiere"].unique(), index=list(df["Matiere"].unique()).index(st.session_state.current_mat))
    chapitres = df[df["Matiere"] == choix_mat]["Chapitre"].tolist()
    choix_chap = st.radio("Chapitre :", chapitres)
    st.session_state.current_mat, st.session_state.current_chap = choix_mat, choix_chap

    st.divider()
    theme_m = st.selectbox("Style Visuel :", ["neutral", "forest", "base", "dark"])
    angle = st.selectbox("Angle d'attaque :", ["📜 Histoire", "🧠 Logique", "🛠 Application"])
    duree = st.select_slider("Densité :", options=["30 min", "1h", "1h30"], value="30 min")

# --- 4. LA SÉANCE ---

st.subheader(f"📍 Sujet : {choix_chap}")
besoin_anna = st.text_area("Anna, dis à Joris tes questions ou ton humeur du moment :", height=80)

col_btns = st.columns([1, 1, 3])
with col_btns[0]: lancer = st.button("🚀 Lancer la séance")
with col_btns[1]: pause = st.button("🧘 Pause Zen")

if lancer:
    with st.spinner("Joris prépare ton exploration..."):
        contexte = load_context("bibliotheque", choix_mat)
        
        prompt = f"""
        Tu es Joris, l'allié intellectuel d'Anna (14 ans, HPI). 
        MESSAGE D'ANNA : "{besoin_anna}"
        SÉANCE : {choix_chap} ({choix_mat}) | ANGLE : {angle}.
        
        STRUCTURE DE LA RÉPONSE (MISE EN FORME RICHE AVEC TITRES ET GRAS) :
        1. # Accueil & Sens (Donne de la profondeur au sujet)
        2. # Exploration Approfondie (Analyse dense basée sur : {contexte})
        3. ## 📖 Le Lexique des Curieux (Format [MOT]: [DÉFINITION])
        4. ## 🎥 Support Humain (Vidéo YouTube/Lumni précise)
        5. # 🖋️ L'Atelier de Réflexion (Questions ouvertes)
           Propose 2 questions complexes demandant une réponse argumentée pour développer ses compétences rédactionnelles.
        6. # 🧠 Architecture de Pensée (Infographie Mermaid graph TD ou mindmap)
        7. # ⏳ Chronologie (Infographie Mermaid graph LR ou timeline)
        8. # 📝 Le Quiz Flash (3 questions à choix multiples pour vérifier l'acquisition)
        9. RECO:[NOM_MATIERE]|[NOM_CHAPITRE] (Suggère la suite logique)
        """
        try:
            res = model.generate_content(prompt)
            st.session_state.resp = res.text
        except Exception as e: st.error(f"Erreur : {e}")

# --- 5. AFFICHAGE DES RÉSULTATS ---

if st.session_state.resp:
    st.divider()
    
    # Séparation intelligente pour Mermaid et Lexique
    parts = re.split(r'(```mermaid.*?```|## 📖 Le Lexique des Curieux.*?\n\n)', st.session_state.resp, flags=re.DOTALL)
    
    for part in parts:
        if part.startswith('```mermaid'):
            m_code = part.replace('```mermaid', '').replace('```', '').strip()
            with st.expander("🔍 Voir l'architecture visuelle", expanded=True):
                render_mermaid(m_code, theme=theme_m)
        elif "Le Lexique des Curieux" in part:
            st.subheader("📖 Le Lexique des Curieux")
            for line in part.split('\n'):
                if ':' in line and '[' in line:
                    t, d = line.split(':', 1)
                    with st.expander(f"🔹 {t.strip(' []')}"): st.write(d.strip())
        else:
            # On retire l'affichage brut de la reco
            clean_part = re.sub(r'RECO:.*?\|.*', '', part)
            st.markdown(clean_part)

    # Bouton de recommandation croisée (la navigation reste, le texte disparaît)
    reco = re.search(r"RECO:(.*?)\|(.*)", st.session_state.resp)
    if reco:
        m, c = reco.group(1).strip(), reco.group(2).strip()
        st.divider()
        if st.button(f"➡️ Suivre le fil vers : {c} ({m})"):
            st.session_state.current_mat, st.session_state.current_chap = m, c
            st.session_state.resp = None
            st.rerun()

    pdf_bytes = create_pdf(st.session_state.resp)
    st.download_button("📥 Télécharger la fiche de séance (PDF)", data=pdf_bytes, file_name=f"Anna_{choix_mat}.pdf")
