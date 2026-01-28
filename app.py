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
    
    div.stButton > button {
        background-color: #a8e6cf; color: #2c3e50; border: none; border-radius: 12px;
        padding: 10px 25px; font-weight: bold; transition: all 0.3s ease;
    }
    div.stButton > button:hover { background-color: #88d8b0; color: white; transform: scale(1.02); }
    
    button[kind="secondary"] {
        background-color: #fadbd8; color: #c0392b; border: 1px solid #e6b0aa;
    }
    
    .stAlert { background-color: #d6eaf8; color: #2c3e50; border: 1px solid #aed6f1; border-radius: 10px; }
    .streamlit-expanderHeader { background-color: white; border-radius: 5px; color: #2c3e50; }
    .stTextInput > div > div > input { border-radius: 10px; }
    .stMultiSelect span { background-color: #a8e6cf; color: #2c3e50; border-radius: 5px; }
    
    details {
        background-color: #fff; border: 1px solid #ccc; border-radius: 5px; padding: 10px; margin-top: 20px;
    }
    summary {
        font-weight: bold; cursor: pointer; color: #2980b9;
    }
    
    /* Style pour la Brevet Box */
    .brevet-box {
        border: 2px dashed #e74c3c; padding: 15px; background-color: #fdedec; border-radius: 10px; margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

api_key = st.secrets.get("GOOGLE_API_KEY")
if not api_key:
    st.error("Clé API manquante.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('models/gemini-2.5-flash')

# --- 2. FONCTIONS (CACHE ACTIVÉ) ---

def extract_pdf_text(file_path_or_buffer):
    try:
        pdf_reader = pypdf.PdfReader(file_path_or_buffer)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except: return ""

@st.cache_data 
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

@st.cache_data
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
            
            details {{ background-color: #e8f8f5; border: 2px solid #a2d9ce; border-radius: 10px; padding: 15px; margin-top: 30px; }}
            summary {{ font-weight: bold; color: #16a085; cursor: pointer; font-size: 1.1em; }}
            summary:hover {{ color: #1abc9c; }}
            
            .brevet-box {{ border: 2px dashed #e74c3c; padding: 20px; background-color: #fff5f5; border-radius: 15px; margin: 30px 0; }}
            
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

# --- 3. CHARGEMENT DONNÉES ---
biblio_text = load_bibliotheque_content("bibliotheque")
df_programme = load_programme_csv("bibliotheque")

# --- 4. INTERFACE ---
col_header_1, col_header_2 = st.columns([3, 1])
with col_header_1:
    st.title("🇷🇪 Le Labo d'Anna")
    st.caption("Coach Pédagogique - Propulsé par Gemini 2.5")
with col_header_2:
    if st.button("🔄 Nouvelle Fiche", type="secondary"):
        st.session_state.clear()
        st.rerun()

col_gauche, col_droite = st.columns([1, 2])

# --- GAUCHE : DASHBOARD & PROGRESSION ---
progression_context = ""
with col_gauche:
    st.info("### 1️⃣ Tableau de Bord")
    
    if df_programme is not None and not df_programme.empty:
        # A. CALCUL ET AFFICHAGE DES BARRES DE PROGRESSION
        # On stocke les choix dans session_state pour qu'ils persistent
        if 'progress_data' not in st.session_state:
            st.session_state.progress_data = {}

        toutes_matieres = df_programme['Matiere'].unique().tolist()
        
        # Sélection des matières
        matieres_selectionnees = st.multiselect("Quelles matières travailler ?", toutes_matieres)
        
        if matieres_selectionnees:
            st.markdown("---")
            st.caption("📍 Où en est-on ?")
            
            for matiere in matieres_selectionnees:
                chapitres_bruts = df_programme[df_programme['Matiere'] == matiere]['Chapitre'].tolist()
                total_chapitres = len(chapitres_bruts)
                
                # Récupération de l'index du choix actuel
                current_choice = st.session_state.get(f"choix_{matiere}", "(Rien commencé)")
                
                # Calcul pourcentage
                if current_choice == "(Rien commencé)":
                    progress_val = 0
                else:
                    # On nettoie le nom pour trouver l'index (car le selectbox a ajouté "1. ", "2. ")
                    # Astuce : on utilise l'index dans la liste des options
                    try:
                        # On reconstruit la liste des options comme dans le selectbox
                        options_clean = [clean_chapter_name(i, c) for i, c in enumerate(chapitres_bruts)]
                        idx = options_clean.index(current_choice)
                        progress_val = (idx + 1) / total_chapitres
                    except:
                        progress_val = 0
                
                # Affichage Barre + Menu
                st.markdown(f"**{matiere}** ({int(progress_val*100)}%)")
                st.progress(progress_val)
                
                options = ["(Rien commencé)"] + [clean_chapter_name(i, c) for i, c in enumerate(chapitres_bruts)]
                
                # Le Selectbox met à jour la variable choix_{matiere}
                choix = st.selectbox(
                    f"Chapitre terminé en {matiere}", 
                    options, 
                    key=f"choix_{matiere}",
                    label_visibility="collapsed"
                )
                
                if choix != "(Rien commencé)":
                    progression_context += f"- {matiere} : '{choix}' ACQUIS.\n"
                else:
                    progression_context += f"- {matiere} : Débutant.\n"
        else:
            st.caption("👈 Sélectionne une matière pour voir tes jauges !")
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
        sujet = st.text_input("Sujet ?", placeholder="Laisse vide pour la SUITE logique...")
    with c2:
        humeur = st.selectbox("Énergie ?", ["😴 Chill (Écoute)", "🧐 Curieuse (Jeu/Vidéo)", "🚀 Focus (Sérieux)"])

    duree_seance = st.slider("⏳ Durée de la séance (minutes) :", min_value=30, max_value=180, value=45, step=15)

    liste_options_outils = [
        "🚀 Mix Tout (Vidéo + iPad + Papier + Jeu)",
        "📺 Vidéo (YouTube/Lumni)", 
        "📱 iPad (Apps Créatives)", 
        "📝 Papier/Crayon (Cartes mentales/Schémas)", 
        "🎲 Jeu/Manip"
    ]
    
    outils_choisis = st.multiselect(
        "Boîte à outils :",
        liste_options_outils,
        default=["🚀 Mix Tout (Vidéo + iPad + Papier + Jeu)"], 
        placeholder="Ajoute des outils..."
    )

    final_subject = sujet
    mode_auto = False
    if not final_subject and not user_pdf:
        if progression_context:
            final_subject = "SUITE"
            mode_auto = True

    instruction_outils = ""
    if any("Mix Tout" in outil for outil in outils_choisis):
        instruction_outils = "UTILISE TOUS LES OUTILS DISPONIBLES."
    else:
        instruction_outils = f"Outils imposés : {', '.join(outils_choisis)}"

    # --- 6. LE SYSTEM PROMPT (AVEC DASHBOARD & BREVET BOX) ---
    system_prompt = f"""
    ROLE : Coach Pédagogique personnel d'Anna (14 ans, 3ème, Réunion).
    IDENTITÉ : Enseignant expérimenté + Expert Neuro-éducation.
    
    RÈGLES DE TON :
    - **TUTOIEMENT OBLIGATOIRE** ("Salut Anna !").
    - Ton chaleureux, allié, mais sérieux sur le fond.
    
    PARAMÈTRE TEMPS : {duree_seance} MINUTES.
    
    SÉCURITÉ : Liens YouTube RECHERCHE uniquement (Yvan Monka, Lumni...).
    
    DONNÉES :
    - Progression : {progression_context if progression_context else "Non spécifiée"}
    - Bibliothèque : {biblio_text}
    - Document : {user_pdf_content}
    - Outils : {instruction_outils}
    
    STRUCTURE DE LA FICHE :
    1. 👋 **Check-Up**.
    
    2. 🥑 **[TITRE ACCROCHEUR SUR LE SUJET]** (Pas de "Accroche Fun").
    
    3. ⏱️ **La Mission** (Activités calibrées).
    
    4. 🧠 **LA MEMO-BREVET (NOUVEAU)** :
       - Crée un petit tableau synthétique intitulé "À COPIER SUR TA FICHE BRISTOL".
       - Mets-y : 3 mots-clés, 1 date/formule clé, 1 piège à éviter.
       - C'est ce qu'elle doit apprendre par cœur.
    
    5. 🥚 **Le Saviez-vous ?** : Une anecdote culturelle courte, surprenante ou drôle liée au sujet (pour briller en société).
    
    6. ✨ **Défi Créatif**.
    
    7. ❓ **LE QUIZ FINAL** (Réponses cachées dans <details>).
    """

    if st.button("🚀 Lancer la séance", type="primary"):
        if not final_subject and not user_pdf:
            st.warning("⚠️ Indique un sujet, ou sélectionne une matière à gauche !")
        else:
            if mode_auto:
                st.success("✅ Sujet non renseigné : Je lance la SUITE logique du programme !")
            
            with st.spinner(f"Préparation d'une séance de {duree_seance} minutes pour Anna..."):
                try:
                    requete = f"Sujet: {final_subject}. Mood: {humeur}. Outils: {instruction_outils}. Instructions: {system_prompt}"
                    response = model.generate_content(requete)
                    
                    st.balloons()
                    
                    st.markdown("---")
                    st.markdown(response.text, unsafe_allow_html=True)
                    
                    html_data = create_download_link(response.text)
                    st.download_button("📥 Télécharger la fiche", html_data, "Seance_Anna.html", "text/html")
                    
                except Exception as e:
                    st.error(f"Erreur : {e}")

st.markdown("<br>", unsafe_allow_html=True)
