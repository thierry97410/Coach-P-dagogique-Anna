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

if 'current_mat' not in st.session_state: st.session_state.current_mat = None
if 'current_chap' not in st.session_state: st.session_state.current_chap = None
if 'session_complete' not in st.session_state: st.session_state.session_complete = False
if 'last_mermaid_error' not in st.session_state: st.session_state.last_mermaid_error = None

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Clé API manquante.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

# --- 2. FONCTIONS TECHNIQUES ---

def v_mermaid_advanced(code, theme="neutral"):
    """Affiche Mermaid avec un parseur JS qui détecte les erreurs."""
    html_code = f"""
    <div id="mermaid-container" class="mermaid">
    {code}
    </div>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        const container = document.getElementById('mermaid-container');
        try {{
            mermaid.initialize({{ startOnLoad: true, theme: '{theme}', securityLevel: 'loose' }});
            mermaid.parse('{code.replace("'", "\\'").replace("\\n", " ")}');
        }} catch (e) {{
            container.innerHTML = '<div style="color: #ef4444; padding: 10px; border: 1px solid #fca5a5; border-radius: 8px; font-family: sans-serif;"><b>Oups ! Joris a fait une petite erreur de dessin.</b><br><small>' + e.message + '</small></div>';
        }}
    </script>
    """
    components.html(html_code, height=450, scrolling=True)

def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)
    # Nettoyage Markdown pour le PDF
    clean_text = re.sub(r'#+', '', text).replace('**', '').replace('`', '')
    clean_text = clean_text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 8, txt=clean_text)
    return bytes(pdf.output())

def load_all_contexts(folder, matiere):
    combined_text = ""
    sources = []
    if not os.path.exists(folder): return "", []
    prefix = matiere[:4].upper()
    files = [f for f in os.listdir(folder) if f.upper().startswith(prefix) and f.lower().endswith(".pdf")]
    for filename in files:
        with open(os.path.join(folder, filename), "rb") as f:
            combined_text += f"\n--- SOURCE : {filename} ---\n"
            reader = PdfReader(f)
            combined_text += "".join([p.extract_text() for p in reader.pages if p.extract_text()])
            sources.append(filename)
    return combined_text[:150000], sources

# --- 3. INTERFACE ---

st.title("🎓 L'Espace d'Exploration d'Anna")

CSV_PATH = "bibliotheque/programme.csv"
if os.path.exists(CSV_PATH):
    df = pd.read_csv(CSV_PATH, sep=",")
    df.columns = df.columns.str.strip()
else: st.stop()

if st.session_state.current_mat is None: st.session_state.current_mat = df["Matiere"].unique()[0]
if st.session_state.current_chap is None: st.session_state.current_chap = df[df["Matiere"] == st.session_state.current_mat]["Chapitre"].tolist()[0]

with st.sidebar:
    st.header("⚙️ Pilotage")
    choix_mat = st.selectbox("Matière :", df["Matiere"].unique(), index=list(df["Matiere"].unique()).index(st.session_state.current_mat))
    chapitres = df[df["Matiere"] == choix_mat]["Chapitre"].tolist()
    choix_chap = st.radio("Chapitre :", chapitres, index=chapitres.index(st.session_state.current_chap) if st.session_state.current_chap in chapitres else 0)
    st.session_state.current_mat, st.session_state.current_chap = choix_mat, choix_chap

    st.divider()
    theme_mermaid = st.selectbox("Style visuel :", ["neutral", "forest", "dark", "base"])
    angle = st.selectbox("Angle d'attaque :", ["📜 Histoire", "🧠 Logique", "🛠 Application"])
    duree = st.select_slider("Densité :", options=["15 min", "30 min", "1h"], value="30 min")

# --- 4. SÉANCE INTERACTIVE ---

st.subheader(f"📍 Séance : {st.session_state.current_chap}")
besoin_anna = st.text_area("Dis à Joris ce que tu as en tête :", height=80)

col_actions = st.columns([1, 1, 3])
with col_actions[0]: lancer = st.button("🚀 Lancer la séance")
with col_actions[1]: pause_zen = st.button("🧘 Pause Zen")

if lancer:
    st.session_state.session_complete = False
    with st.spinner("Joris tisse les liens..."):
        contexte_bib, liste_sources = load_all_contexts("bibliotheque", st.session_state.current_mat)
        
        prompt = f"""
        Tu es Joris, l'allié d'Anna (14 ans, HPI). Tu es un curateur de savoirs humains.
        MESSAGE D'ANNA : "{besoin_anna}"
        SÉANCE : {st.session_state.current_chap} ({st.session_state.current_mat}) | ANGLE : {angle}.
        
        STRUCTURE :
        1. # Accueil & Sens
        2. # Exploration Approfondie (Sources : {contexte_bib})
        3. ## 📖 Le Lexique des Curieux (Format [MOT]: [DÉFINITION])
        4. ## Interconnexions interdisciplinaires
        5. ## Support Humain (Vidéo YouTube/Lumni)
        6. ## L'Enquête de l'Esprit (Analyse critique)
        7. # 🧠 Analyse Logique (```mermaid mindmap ... ```)
        8. # ⏳ Analyse Chronologique (```mermaid graph LR ... ```)
        9. ## RECO:[NOM_MATIERE]|[NOM_CHAPITRE]
        10. ### Sources & Crédits ({', '.join(liste_sources)})
        """
        try:
            response = model.generate_content(prompt)
            st.session_state['resp'] = response.text
            reco_match = re.search(r"RECO:(.*?)\|(.*)", response.text)
            if reco_match: st.session_state['reco_data'] = (reco_match.group(1).strip(), reco_match.group(2).strip())
        except Exception as e: st.error(f"Erreur : {e}")

# --- 5. AFFICHAGE DES RÉSULTATS ---

if 'resp' in st.session_state:
    st.divider()
    
    # Traitement spécifique pour le Glossaire et Mermaid
    parts = re.split(r'(```mermaid.*?```|## 📖 Le Lexique des Curieux.*?\n\n)', st.session_state['resp'], flags=re.DOTALL)
    
    for part in parts:
        if part.startswith('```mermaid'):
            m_code = part.replace('```mermaid', '').replace('```', '').strip()
            with st.expander("🔍 Voir l'infographie structurelle", expanded=True):
                v_mermaid_advanced(m_code, theme=theme_mermaid)
        
        elif "Le Lexique des Curieux" in part:
            st.subheader("📖 Le Lexique des Curieux")
            for line in part.split('\n'):
                if ':' in line and '[' in line:
                    term, definition = line.split(':', 1)
                    with st.expander(f"🔹 {term.strip(' []')}"):
                        st.write(definition.strip())
        else:
            st.markdown(re.sub(r'RECO:.*?\|.*', '', part))

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
