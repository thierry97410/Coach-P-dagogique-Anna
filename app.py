import streamlit as st
import google.generativeai as genai
import pypdf
import os
import pandas as pd # L'outil magique pour lire ton fichier CSV

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Le Labo d'Anna", page_icon="🇷🇪", layout="wide")

# Récupération de la clé API
api_key = st.secrets.get("GOOGLE_API_KEY")
if not api_key:
    st.error("Clé API manquante. Vérifie les 'Secrets' dans Streamlit.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-pro')

# --- 2. FONCTIONS TECHNIQUES ---

def extract_pdf_text(file_path_or_buffer):
    """Lit le texte d'un PDF"""
    try:
        pdf_reader = pypdf.PdfReader(file_path_or_buffer)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except: return ""

def load_bibliotheque_content(folder_name):
    """Lit tous les PDF du dossier bibliothèque pour la culture générale"""
    content = ""
    if os.path.exists(folder_name):
        for filename in os.listdir(folder_name):
            if filename.lower().endswith(".pdf"):
                path = os.path.join(folder_name, filename)
                with open(path, "rb") as f:
                    text = extract_pdf_text(f)
                    if text: content += f"\nSOURCE DE SAVOIR ({filename}): {text[:15000]}"
    return content

def load_programme_csv(folder_name):
    """Charge la liste des chapitres depuis le fichier CSV"""
    path = os.path.join(folder_name, "programme.csv")
    if os.path.exists(path):
        try:
            # On lit le fichier avec détection auto du séparateur
            df = pd.read_csv(path, sep=None, engine='python')
            return df
        except Exception as e:
            st.error(f"Erreur de lecture du CSV : {e}")
            return None
    return None

def create_download_link(content):
    """Crée le fichier HTML à télécharger"""
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Helvetica', sans-serif; max-width: 800px; margin: auto; padding: 20px; line-height: 1.6; color: #333; }}
            h1 {{ color: #2c3e50; text-align: center; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            h2 {{ color: #2980b9; margin-top: 30px; }}
            h3 {{ color: #16a085; }}
            .box {{ background-color: #f9f9f9; border-left: 5px solid #3498db; padding: 15px; margin: 20px 0; }}
            a {{ color: #e74c3c; text-decoration: none; font-weight: bold; }}
            a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <h1>Séance du Labo d'Anna 🇷🇪</h1>
        {content.replace(chr(10), '<br>').replace('**', '<b>').replace('## ', '<h2>').replace('### ', '<h3>').replace('- ', '• ')}
    </body>
    </html>
    """
    return html.encode('utf-8')

# --- 3. CHARGEMENT DES DONNÉES ---
biblio_text = load_bibliotheque_content("bibliotheque")
df_programme = load_programme_csv("bibliotheque")

# --- 4. INTERFACE GRAPHIQUE ---
st.title("🇷🇪 Le Labo d'Anna")
st.caption("Coach Pédago Bienveillant - Programme Officiel 3ème")

col_gauche, col_droite = st.columns([1, 2])

# --- COLONNE GAUCHE : SUIVI PROGRESSION ---
progression_context = ""

with col_gauche:
    st.markdown("### 📍 Où en est-on ?")
    st.info("Indique le DERNIER chapitre terminé pour chaque matière.")
    
    if df_programme is not None and not df_programme.empty:
        # Liste des matières uniques
        matieres = df_programme['Matiere'].unique()
        
        for matiere in matieres:
            # On récupère les chapitres de cette matière
            chapitres = df_programme[df_programme['Matiere'] == matiere]['Chapitre'].tolist()
            # Ajout de l'option "Rien fait"
            options = ["(Rien commencé)"] + chapitres
            
            # Le Menu Déroulant
            choix = st.selectbox(f"{matiere}", options, key=matiere)
            
            if choix != "(Rien commencé)":
                progression_context += f"- {matiere} : Le chapitre '{choix}' est VALIDÉ/ACQUIS.\n"
            else:
                progression_context += f"- {matiere} : Aucun chapitre validé.\n"
    else:
        st.warning("⚠️ Fichier 'programme.csv' introuvable ou vide dans le dossier 'bibliotheque'.")

# --- COLONNE DROITE : GÉNÉRATEUR ---
with col_droite:
    st.markdown("### ✨ Créer ma séance")
    
    # Zone Upload Devoir
    with st.expander("📂 J'ai un devoir ou un document PDF spécifique pour aujourd'hui"):
        user_pdf = st.file_uploader("Glisse ton fichier ici", type=["pdf"])
        user_pdf_content = extract_pdf_text(user_pdf) if user_pdf else ""

    # Paramètres de séance
    c1, c2 = st.columns(2)
    with c1:
        sujet = st.text_input("Sujet du jour ?", placeholder="Tape un sujet... OU tape 'SUITE'")
        if sujet.upper().strip() == "SUITE":
            st.success("✅ Mode 'Pilote Automatique' activé !")
            st.caption("Je vais regarder ta progression à gauche et proposer la suite logique.")
    with c2:
        humeur = st.selectbox("Ton énergie ?", ["😴 Chill (Écoute)", "🧐 Curieuse (Jeu/Vidéo)", "🚀 Focus (Sérieux)"])

    outil_pref = st.radio("Outil préféré ?", ["🎲 Mix Surprise", "📺 Vidéo (YouTube/Lumni)", "📱 iPad (Apps Créatives)"], horizontal=True)

    # --- 5. LE PROMPT ---
    system_prompt = f"""
    Tu es le Coach Personnel d'Anna (14 ans, 3ème, Réunion).
    Tu t'adresses DIRECTEMENT à elle (tu la tutoies).
    
    TES DONNÉES DE NAVIGATION :
    1. PROGRESSION ACTUELLE (Ce qui est fait) :
    {progression_context}
    
    2. SAVOIRS & MANUELS (Bibliothèque) :
    {biblio_text[:20000]}
    
    3. DOCUMENT DU JOUR (Si fourni) :
    {user_pdf_content}
    
    RÈGLES DU JEU :
    - Si le sujet est "SUITE" : Analyse la progression. Trouve le chapitre qui vient juste APRES celui validé dans une des matières principales (Maths, Français, Histoire ou SVT). Propose ce nouveau chapitre.
    - Si le sujet est libre : Vérifie si Anna a les bases (progression).
    - INTERDIT : Mots "Brevet", "Notes", "Examen", "Lycée".
    - TON : Encourangeant, complice, lien avec la Réunion.
    - LIENS : Si vidéo proposée -> URL cliquable OBLIGATOIRE.
    
    STRUCTURE DE TA RÉPONSE :
    1. 👋 Le Check-Up : "Salut Anna ! J'ai vu que tu avais validé [Chapitre d'avant]..."
    2. 🥑 L'Accroche Fun (Teaser).
    3. ⏱️ La Mission (Activités concrètes avec liens).
    4. ✨ Le Défi Créatif (iPad/Vocal/Dessin).
    """

    # Bouton Lancement
    if st.button("🚀 Lancer la séance", type="primary"):
        if not sujet and not user_pdf:
            st.warning("Il me faut un sujet (ou tape 'SUITE') !")
        else:
            with st.spinner("Analyse de ta progression et recherche des meilleures ressources..."):
                try:
                    # Appel à Gemini
                    requete = f"Sujet: {sujet}. Mood: {humeur}. Outil: {outil_pref}. Instructions: {system_prompt}"
                    response = model.generate_content(requete)
                    
                    # Affichage
                    st.markdown("---")
                    st.markdown(response.text)
                    
                    # Téléchargement
                    html_data = create_download_link(response.text)
                    st.download_button(
                        label="📥 Télécharger cette séance (Fiche HTML)",
                        data=html_data,
                        file_name=f"Seance_Anna.html",
                        mime="text/html"
                    )
                    
                except Exception as e:
                    st.error(f"Une erreur est survenue : {e}")

st.markdown("---")
