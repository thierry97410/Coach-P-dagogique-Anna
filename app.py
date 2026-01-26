import streamlit as st
import google.generativeai as genai
import pypdf
import os
import pandas as pd
import re

# --- 1. CONFIGURATION & DESIGN ---
st.set_page_config(page_title="Le Labo d'Anna", page_icon="🌿", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #e8f4f8; }
    h1, h2, h3 { color: #34495e; font-family: 'Helvetica', sans-serif; }
    
    /* Boutons standards (Vert) */
    div.stButton > button {
        background-color: #a8e6cf; color: #2c3e50; border: none; border-radius: 12px;
        padding: 10px 25px; font-weight: bold; transition: all 0.3s ease;
    }
    div.stButton > button:hover { background-color: #88d8b0; color: white; transform: scale(1.02); }
    
    /* Bouton Réinitialiser (Rouge doux pour le distinguer) */
    button[kind="secondary"] {
        background-color: #fadbd8; color: #c0392b; border: 1px solid #e6b0aa;
    }
    
    .stAlert { background-color: #d6eaf8; color: #2c3e50; border: 1px solid #aed6f1; border-radius: 10px; }
    .streamlit-expanderHeader { background-color: white; border-radius: 5px; color: #2c3e50; }
    .stTextInput > div > div > input { border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

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

def clean_chapter_name(index, name):
    if re.match(r'^\d', str(name)): return str(name)
    return f"{index + 1}. {name}"

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
col_header_1, col_header_2 = st.columns([3, 1])
with col_header_1:
    st.title("🇷🇪 Le Labo d'Anna")
    st.caption("Coach Pédagogique - Propulsé par Gemini 2.5")
with col_header_2:
    # BOUTON RÉINITIALISER (En haut à droite)
    if st.button("🔄 Nouvelle Fiche", type="secondary"):
        st.rerun()

col_gauche, col_droite = st.columns([1, 2])

# --- GAUCHE ---
progression_context = ""
with col_gauche:
    st.info("### 1️⃣ Matières & Progression")
    if df_programme is not None and not df_programme.empty:
        toutes_matieres = df_programme['Matiere'].unique().tolist()
        matieres_selectionnees = st.multiselect("Quelles matières aujourd'hui ?", toutes_matieres)
        
        if matieres_selectionnees:
            st.markdown("---")
            st.caption("Dernier chapitre terminé :")
            for matiere in matieres_selectionnees:
                chapitres_bruts = df_programme[df_programme['Matiere'] == matiere]['Chapitre'].tolist()
                chapitres_propres = [clean_chapter_name(i, c) for i, c in enumerate(chapitres_bruts)]
                options = ["(Rien commencé)"] + chapitres_propres
                choix = st.selectbox(f"{matiere}", options, key=matiere)
                
                if choix != "(Rien commencé)":
                    progression_context += f"- {matiere} : Le chapitre '{choix}' est ACQUIS.\n"
                else:
                    progression_context += f"- {matiere} : Débutant.\n"
        else:
            st.caption("👈 Choisis une matière.")
    else:
        st.warning("⚠️ Fichier 'programme.csv' introuvable.")

# --- DROITE ---
with col_droite:
    st.markdown("### 2️⃣ Paramètres de la séance")
    
    with st.expander("📂 Document du jour (Devoir PDF)"):
        user_pdf = st.file_uploader("Glisse le fichier ici", type=["pdf"])
        user_pdf_content = extract_pdf_text(user_pdf) if user_pdf else ""

    c1, c2 = st.columns(2)
    with c1:
        sujet = st.text_input("Sujet ?", placeholder="Tape un sujet... OU tape 'SUITE'")
        if sujet.upper().strip() == "SUITE":
            st.success("✅ Mode Pilote Auto")
            if not matieres_selectionnees:
                st.warning("⚠️ Sélectionne une matière à gauche !")
    with c2:
        humeur = st.selectbox("Énergie ?", ["😴 Chill (Écoute)", "🧐 Curieuse (Jeu/Vidéo)", "🚀 Focus (Sérieux)"])

    # SELECTEUR D'OUTILS (Modifié)
    outil_pref = st.radio(
        "Outils ?", 
        ["🚀 Mix (Tous les outils)", "📺 Vidéo", "📱 iPad", "📝 Papier/Crayon"], 
        horizontal=True
    )

    # --- 5. PROMPT ---
    system_prompt = f"""
    Tu es le Coach Pédagogique d'Anna (14 ans, 3ème, Réunion).
    
    CONTEXTE TECHNIQUE :
    - Fiche de séance statique (PAS DE CONVERSATION).
    - **INTERDICTION** de poser des questions ("Dis-moi...").
    - **CONSIGNES D'ACTION** uniquement ("Note...", "Réfléchis...", "Dessine...").

    DONNÉES :
    1. PROGRESSION : {progression_context if progression_context else "Non spécifiée"}
    2. BIBLIOTHÈQUE : {biblio_text}
    3. DOCUMENT DU JOUR : {user_pdf_content}
    
    RÈGLES OUTILS :
    - Outil choisi : {outil_pref}
    - Si "Mix" : Utilise tout (Vidéo + iPad + Écrit).
    - Si "Papier/Crayon" : Pas d'écran ! Propose schémas, cartes mentales, écriture.
    - Si "Vidéo" : Lien URL cliquable OBLIGATOIRE.
    
    RÈGLES PÉDAGO :
    - Si "SUITE" : Chapitre suivant logique.
    - ZÉRO PRESSION : Mots bannis (Brevet, Notes, Examen).
    - TON : Encourangeant, calme, liens avec la Réunion.
    
    STRUCTURE :
    1. 👋 Check-Up.
    2. 🥑 Accroche Fun.
    3. ⏱️ Mission (Adaptée à l'outil {outil_pref}).
    4. ✨ Défi Créatif.
    """

    if st.button("🚀 Lancer la séance", type="primary"):
        if not sujet and not user_pdf:
            st.warning("Il me faut un sujet (ou tape 'SUITE') !")
        elif sujet.upper().strip() == "SUITE" and not progression_context:
            st.error("Coche une matière à gauche !")
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
