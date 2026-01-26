import streamlit as st
import google.generativeai as genai
import pypdf
import os
import pandas as pd
import re # Pour gérer la numérotation intelligente

# --- 1. CONFIGURATION & DESIGN ---
st.set_page_config(page_title="Le Labo d'Anna", page_icon="🌿", layout="wide")

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
    /* Style pour le multiselect */
    .stMultiSelect span { background-color: #a8e6cf; color: #2c3e50; }
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
    """Ajoute un numéro propre (1. 2. 3.) devant le chapitre"""
    # Si le chapitre commence déjà par un chiffre, on le garde tel quel
    if re.match(r'^\d', str(name)):
        return str(name)
    # Sinon on ajoute le numéro d'index
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
st.title("🇷🇪 Le Labo d'Anna")
st.caption("Coach Pédagogique - Propulsé par Gemini 2.5")

col_gauche, col_droite = st.columns([1, 2])

# --- GAUCHE : SÉLECTION & PROGRESSION ---
progression_context = ""

with col_gauche:
    st.info("### 1️⃣ Matières & Progression")
    
    if df_programme is not None and not df_programme.empty:
        # A. SÉLECTION DES MATIÈRES (Le filtre)
        toutes_matieres = df_programme['Matiere'].unique().tolist()
        matieres_selectionnees = st.multiselect(
            "Quelles matières veux-tu voir aujourd'hui ?",
            toutes_matieres,
            placeholder="Choisis une ou plusieurs matières..."
        )
        
        # B. AFFICHAGE DYNAMIQUE (Uniquement ce qui est coché)
        if matieres_selectionnees:
            st.markdown("---")
            st.caption("Indique le **dernier chapitre terminé** :")
            
            for matiere in matieres_selectionnees:
                # Récupération des chapitres
                chapitres_bruts = df_programme[df_programme['Matiere'] == matiere]['Chapitre'].tolist()
                
                # Numérotation automatique (1. X, 2. Y...)
                chapitres_propres = [clean_chapter_name(i, c) for i, c in enumerate(chapitres_bruts)]
                
                options = ["(Rien commencé)"] + chapitres_propres
                
                # Le Menu Déroulant
                choix = st.selectbox(f"Progression {matiere}", options, key=matiere)
                
                if choix != "(Rien commencé)":
                    progression_context += f"- {matiere} : Le chapitre '{choix}' est ACQUIS.\n"
                else:
                    progression_context += f"- {matiere} : Niveau débutant (aucun chapitre validé).\n"
        else:
            st.caption("👈 Commence par sélectionner une matière ci-dessus.")
            
    else:
        st.warning("⚠️ Fichier 'programme.csv' introuvable.")

# --- DROITE : ACTION ---
with col_droite:
    st.markdown("### 2️⃣ Préparer la séance")
    
    # Zone Document
    with st.expander("📂 Document du jour (Devoir PDF)"):
        user_pdf = st.file_uploader("Glisse le fichier ici", type=["pdf"])
        user_pdf_content = extract_pdf_text(user_pdf) if user_pdf else ""

    c1, c2 = st.columns(2)
    with c1:
        sujet = st.text_input("Sujet ?", placeholder="Tape un sujet... OU tape 'SUITE'")
        if sujet.upper().strip() == "SUITE":
            st.success("✅ Mode Pilote Auto")
            if not matieres_selectionnees:
                st.warning("⚠️ Attention : Sélectionne d'abord une matière à gauche pour que je sache quoi proposer !")
    with c2:
        humeur = st.selectbox("Énergie ?", ["😴 Chill (Écoute)", "🧐 Curieuse (Jeu/Vidéo)", "🚀 Focus (Sérieux)"])

    outil_pref = st.radio("Outil ?", ["🎲 Surprise", "📺 Vidéo", "📱 iPad"], horizontal=True)

    # --- 5. PROMPT ---
    system_prompt = f"""
    Tu es le Coach Pédagogique d'Anna (14 ans, 3ème, Réunion).
    
    CONTEXTE TECHNIQUE (RAPPEL) :
    - Tu génères une "Fiche de séance" statique.
    - **ELLE NE PEUT PAS TE RÉPONDRE.**
    - **INTERDICTION** de poser des questions directes ("Dis-moi...").
    - **REMPLACE PAR** des consignes d'action ("Réfléchis à...", "Note sur ton iPad...").

    DONNÉES :
    1. PROGRESSION SUR LES MATIÈRES SÉLECTIONNÉES : 
    {progression_context if progression_context else "Aucune matière sélectionnée ou progression indiquée."}
    
    2. BIBLIOTHÈQUE : {biblio_text}
    3. DOCUMENT DU JOUR : {user_pdf_content}
    
    RÈGLES :
    - Si "SUITE" : Regarde la progression fournie. Trouve le chapitre NUMÉROTÉ suivant dans la liste. Propose ce cours.
    - ZÉRO PRESSION : Mots bannis (Brevet, Notes, Examen).
    - TON : Encourangeant, calme, liens avec la Réunion.
    - LIENS : URL Vidéos cliquables OBLIGATOIRES.
    
    STRUCTURE :
    1. 👋 Check-Up ("On avance bien sur...")
    2. 🥑 Accroche Fun.
    3. ⏱️ Mission (Activités).
    4. ✨ Défi Créatif.
    """

    if st.button("🚀 Lancer la séance", type="primary"):
        # Vérification qu'on a bien de quoi travailler
        if not sujet and not user_pdf:
            st.warning("Il me faut un sujet (ou tape 'SUITE') !")
        elif sujet.upper().strip() == "SUITE" and not progression_context:
            st.error("Pour faire 'SUITE', tu dois cocher une matière à gauche et dire où tu en es !")
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
