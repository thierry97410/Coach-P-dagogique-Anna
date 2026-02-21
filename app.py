import streamlit as st
import pandas as pd
import os
import io
from PyPDF2 import PdfReader
import google.generativeai as genai
from fpdf import FPDF

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="L'Espace d'Anna", layout="wide")

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
    st.stop()

with st.sidebar:
    st.header("⚙️ Pilotage (Papa)")
    matieres = df["Matiere"].unique()
    choix_mat = st.selectbox("Matière :", matieres)
    chapitres = df[df["Matiere"] == choix_mat]["Chapitre"].tolist()
    choix_chap = st.radio("Chapitre ciblé :", chapitres)
    st.divider()
    duree = st.select_slider("Densité de la séance :", options=["15 min", "30 min", "1h", "1h30"], value="30 min")
    doc_eleve = st.file_uploader("📂 Support externe (PDF)", type="pdf")

# --- 4. L'ESPACE D'ANNA ---

st.subheader(f"📍 Sujet : {choix_chap}")
st.write("🗨️ **Anna**, c'est ton moment. Pose tes questions, exprime tes doutes ou tes envies ici :")
besoin_anna = st.text_area("Ton message pour Joris :", height=100)

col_actions = st.columns([1, 1, 3])
with col_actions[0]: lancer = st.button("🚀 Lancer l'exploration")
with col_actions[1]: pause_zen = st.button("🧘 Pause Zen")

if pause_zen:
    with st.spinner("Joris te propose une déconnexion intelligente..."):
        prompt_zen = "Tu es Joris. Anna a besoin d'une pause. Propose une anecdote complexe et fascinante sur l'histoire des idées, de la science ou des civilisations. Pas de création, juste de la découverte pure."
        try:
            res_zen = model.generate_content(prompt_zen)
            st.session_state['resp_zen'] = res_zen.text
            if 'resp' in st.session_state: del st.session_state['resp']
        except: st.error("Erreur.")

if lancer:
    with st.spinner("Joris prépare une séance à haute densité intellectuelle..."):
        contexte_bib, liste_sources = load_all_contexts("bibliotheque", choix_mat)
        contexte_exo = extract_pdf_text(doc_eleve) if doc_eleve else ""

        # PROMPT RECENTRÉ SUR LA COMPLEXITÉ ET L'ANALYSE
        prompt = f"""
        Tu es Joris, l'allié intellectuel d'Anna (14 ans, 3ème, profil HPI). 
        Anna est une artiste, mais elle n'a PAS besoin que tu lui demandes de créer des oeuvres. 
        Elle a besoin que tu la stimules par la complexité, la logique et les liens entre les savoirs.
        
        MESSAGE D'ANNA : "{besoin_anna}"
        SÉANCE : {choix_chap} ({choix_mat}) | DURÉE : {duree}.
        
        STRUCTURE DE LA RÉPONSE (DENSE ET RICHE) :
        1. **L'Origine et le Sens** : Pourquoi ce concept a-t-il été inventé ? Quel problème humain ou scientifique résout-il ? Fais des ponts avec d'autres matières.
        2. **Analyse Approfondie (Le Cours)** : Développe les notions clés avec précision. Utilise les documents : {contexte_bib}. Ne simplifie pas les termes techniques.
        3. **Ressource Humaine (Vidéo)** : Propose un documentaire, une conférence ou une expérience filmée (Lumni/YouTube). Donne le titre exact.
        4. **L'Enquête de l'Esprit** : Propose un défi de réflexion pure ou d'analyse critique. (ex: "Compare deux théories", "Trouve l'erreur logique dans...", "Déduis la suite de ce raisonnement..."). Pas de dessin, pas de création.
        5. **Le Point de Controverse** : Un fait historique ou scientifique méconnu, complexe, qui demande de l'esprit critique.
        6. **### 📝 Quiz de Haute Fidélité** : 3 questions complexes qui vérifient la compréhension des mécanismes, pas juste le stockage d'infos.
        7. **Sources & Crédits** : Liste les PDF utilisés ({', '.join(liste_sources)}) et les auteurs des ressources citées.

        TON : Brillant, complice, tutoiement respectueux. Traite-la comme une adulte en devenir.
        """
        try:
            response = model.generate_content(prompt)
            st.session_state['resp'] = response.text
            if 'resp_zen' in st.session_state: del st.session_state['resp_zen']
        except Exception as e:
            st.error(f"Erreur : {e}")

# --- 5. AFFICHAGE ---

if 'resp_zen' in st.session_state:
    st.info(st.session_state['resp_zen'])
    if st.button("✨ Reprendre"):
        del st.session_state['resp_zen']
        st.rerun()

if 'resp' in st.session_state:
    st.divider()
    st.subheader("✅ Suivi de ta séance")
    c1, c2, c3 = st.columns(3)
    with c1: st.checkbox("Concept maîtrisé 🧭")
    with c2: st.checkbox("Enquête résolue 🧠")
    with c3: st.checkbox("Quiz validé ✨")
    
    col_links = st.columns(2)
    with col_links[0]:
        st.link_button("🔍 Explorer les sources humaines", f"https://www.youtube.com/results?search_query=3eme {choix_mat} {choix_chap}")
    with col_links[1]:
        try:
            pdf_bytes = create_pdf(st.session_state['resp'])
            st.download_button("📥 Télécharger la fiche d'approfondissement (PDF)", data=pdf_bytes, file_name=f"Anna_{choix_mat}.pdf")
        except: st.warning("PDF indisponible.")

    st.markdown("---")
    st.markdown(st.session_state['resp'])
