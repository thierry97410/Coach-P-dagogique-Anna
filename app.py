import streamlit as st
import google.generativeai as genai
import pypdf
import os
import pandas as pd

# --- 1. CONFIGURATION & DESIGN ---
st.set_page_config(page_title="Le Labo d'Anna", page_icon="🌿", layout="wide")

# CSS : Couleurs Pastel & Design Doux
st.markdown("""
<style>
    .stApp { background-color: #e8f4f8; }
    h1, h2, h3 { color: #34495e; font-family: 'Helvetica', sans-serif; }
    div.stButton > button {
        background-color: #a8e6cf; color: #2c3e50; border: none; border-radius: 12px;
        padding: 10px 25px; font-weight: bold; transition: all 0.3s ease;
    }
    div.stButton > button:hover { background-color: #88d8b0; color: white; transform: scale(1.02); }
    .stAlert { background-color: #d6eaf8; color: #2c3e50; border: 1px solid #aed6f1; border-radius: 10px; }
    .streamlit-expanderHeader { background-color: white; border-radius: 5px; color: #2c3e50; }
    .stTextInput > div > div > input { border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# API Key
api_key = st.secrets.get("GOOGLE_API_KEY")
if not api_key:
    st.error("Clé API manquante.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('models/gemini-2.5-flash')

# --- 2. FONCTIONS ---
def extract_pdf_text(file_path_or_buffer):
    try:
        pdf_reader = pypdf.PdfReader(file_path_or_buffer)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except: return ""

def load_bibliotheque_content(folder_name):
    content = ""
    if os.path.exists(folder_name):
        for filename in os.listdir(folder_name):
            if filename.lower().endswith(".pdf"):
                path = os.path.join(folder_name, filename)
                with open(path, "rb") as f:
                    text = extract_pdf_text(f)
                    if text: content += f"\nSOURCE ({filename}): {text[:30000]}"
    return content

def load_programme_csv(folder_name):
    path = os.path.join(folder_name, "programme.csv")
    if os.path.exists(path):
        try:
            return pd.read_csv(path, sep=None, engine='python')
        except: return None
    return None

def create_download_link(content):
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Helvetica', sans-serif; background-color: #fdfefe; padding: 40px; color: #444; line-height: 1.6; }}
            .container {{ background-color: white; padding: 40px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); max-width: 800px; margin: auto; }}
            h1 {{ color: #2980b9; text-align: center; border-bottom: 4px solid #a8e6cf; padding-bottom: 20px; }}
            h2 {{ color: #16a085; margin-top: 35px; border-left: 5px solid #a8e6cf; padding-left: 10px; }}
            h3 {{ color: #2c3e50; margin-top: 25px; }}
            a {{ color: #e74c3c; font-weight: bold; text-decoration: none; border-bottom: 2px solid #fadbd8; transition: all 0.2s; }}
            a:hover {{ background-color: #fadbd8; color: #c0392b; }}
            li {{ margin-bottom: 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Séance du Labo d'Anna 🇷🇪</h1>
            {content.replace(chr(10), '<br>').replace('**', '<b>').replace('## ', '<h2>').replace('### ', '<h3>').replace('- ', '• ')}
        </div>
    </body>
    </html>
    """
    return html.encode('utf-8')

# --- 3. DONNÉES ---
biblio_text = load_bibliotheque_content("bibliotheque")
df_programme = load_programme_csv("bibliotheque")

# --- 4. INTERFACE ---
st.title("🇷🇪 Le Labo d'Anna")
st.caption("Coach Pédagogique - Propulsé par Gemini 2.5")

col_gauche, col_droite = st.columns([1, 2])

with col_gauche:
    st.info("### 📍 Progression")
    if df_programme is not None and not df_programme.empty:
        matieres = df_programme['Matiere'].unique()
        progression_context = ""
        for matiere in matieres:
            chapitres = df_programme[df_programme['Matiere'] == matiere]['Chapitre'].tolist()
            options = ["(Rien commencé)"] + chapitres
            choix = st.selectbox(f"{matiere}", options, key=matiere)
            if choix != "(Rien commencé)":
                progression_context += f"- {matiere} : '{choix}' est ACQUIS.\n"
            else:
                progression_context += f"- {matiere} : Débutant.\n"
    else:
        st.warning("⚠️ Fichier 'programme.csv' introuvable.")

with col_droite:
    st.markdown("### ✨ Préparer la séance")
    
    with st.expander("📂 Document du jour (Devoir PDF)"):
        user_pdf = st.file_uploader("Glisse le fichier ici", type=["pdf"])
        user_pdf_content = extract_pdf_text(user_pdf) if user_pdf else ""

    c1, c2 = st.columns(2)
    with c1:
        sujet = st.text_input("Sujet ?", placeholder="Tape un sujet... OU tape 'SUITE'")
        if sujet.upper().strip() == "SUITE":
            st.success("✅ Mode Pilote Auto")
    with c2:
        humeur = st.selectbox("Énergie ?", ["😴 Chill (Écoute)", "🧐 Curieuse (Jeu/Vidéo)", "🚀 Focus (Sérieux)"])

    outil_pref = st.radio("Outil ?", ["🎲 Surprise", "📺 Vidéo", "📱 iPad"], horizontal=True)

    # --- 5. PROMPT CORRIGÉ (MODE SENS UNIQUE) ---
    system_prompt = f"""
    Tu es le Coach Pédagogique d'Anna (14 ans, 3ème, Réunion).
    
    CONTEXTE TECHNIQUE (TRÈS IMPORTANT) :
    - Tu génères une "Fiche de séance" statique que Anna va lire.
    - **ELLE NE PEUT PAS TE RÉPONDRE.** L'interface ne permet pas d'écrire de réponse.
    - **INTERDICTION** de poser des questions directes attendant une réponse ("Dis-moi ce que tu penses", "Quelle est la réponse ?").
    - **REMPLACE PAR** des consignes d'action autonomes : "Réfléchis à...", "Note sur ton iPad...", "Dis à voix haute...", "Essaie de deviner avant de lire la suite".

    DONNÉES :
    1. PROGRESSION : {progression_context}
    2. BIBLIOTHÈQUE : {biblio_text}
    3. DOCUMENT DU JOUR : {user_pdf_content}
    
    RÈGLES PÉDAGO :
    - Si "SUITE" : Trouve le chapitre suivant logique.
    - ZÉRO PRESSION : Mots bannis (Brevet, Notes, Examen).
    - TON : Encourangeant, calme, liens avec la Réunion.
    - LIENS : URL Vidéos cliquables OBLIGATOIRES (YouTube/Lumni).
    
    STRUCTURE DE LA FICHE :
    1. 👋 Check-Up ("On avance bien sur...")
    2. 🥑 Accroche Fun (Sans question directe).
    3. ⏱️ Mission (Activités à faire sur l'iPad ou regarder).
    4. ✨ Défi Créatif (Une production à faire sur son iPad de son côté).
    """

    if st.button("🚀 Lancer la séance", type="primary"):
        if not sujet and not user_pdf:
            st.warning("Il me faut un sujet (ou tape 'SUITE') !")
        else:
            with st.spinner("Gemini 2.5 prépare la feuille de route..."):
                try:
                    requete = f"Sujet: {sujet}. Mood: {humeur}. Outil: {outil_pref}. Instructions: {system_prompt}"
                    response = model.generate_content(requete)
                    
                    st.markdown("---")
                    st.markdown(response.text)
                    
                    html_data = create_download_link(response.text)
                    st.download_button("📥 Télécharger la fiche", html_data, "Seance_Anna.html", "text/html")
                    
                except Exception as e:
                    st.error(f"Erreur : {e}")

st.markdown("<br>", unsafe_allow_html=True)
