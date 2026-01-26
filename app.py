import streamlit as st
import google.generativeai as genai
import pypdf
import os

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Le Labo d'Anna", page_icon="🇷🇪", layout="centered")

api_key = st.secrets.get("GOOGLE_API_KEY")
if not api_key:
    st.error("Clé API manquante.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-pro')

# --- 2. FONCTIONS ---
def extract_pdf_text(file_path_or_buffer):
    try:
        pdf_reader = pypdf.PdfReader(file_path_or_buffer)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except: return ""

def load_bibliotheque(folder_name):
    combined_text = ""
    suivi_text = ""  # Variable pour stocker le suivi
    
    if os.path.exists(folder_name):
        files = os.listdir(folder_name)
        for filename in files:
            path = os.path.join(folder_name, filename)
            
            # Si c'est le fichier de SUIVI (txt)
            if filename == "suivi.txt":
                with open(path, "r", encoding="utf-8") as f:
                    suivi_text = f.read()
            
            # Si c'est un PDF (Programme, manuels...)
            elif filename.lower().endswith(".pdf"):
                with open(path, "rb") as f:
                    text = extract_pdf_text(f)
                    if text:
                        combined_text += f"\n--- SOURCE : {filename} ---\n{text}"
                        
    return combined_text, suivi_text

def create_download_link(content):
    html = f"""<html><body>{content.replace(chr(10), '<br>').replace('**', '<b>').replace('## ', '<h2>')}</body></html>"""
    return html.encode('utf-8')

# --- 3. CHARGEMENT MÉMOIRE ---
biblio_text, suivi_text = load_bibliotheque("bibliotheque")

# --- 4. INTERFACE ---
st.title("🇷🇪 Le Labo d'Anna")

# Affichage de la progression (Pour info)
if suivi_text:
    with st.expander("📈 Voir ma progression actuelle"):
        st.info(suivi_text)
else:
    st.caption("Astuce : Crée un fichier 'suivi.txt' dans la bibliothèque pour que je suive ta progression.")

# Zone Document du Jour
with st.expander("📂 Document spécifique (Devoir du jour)"):
    user_pdf = st.file_uploader("Dépose ton fichier ici", type=["pdf"])
    user_pdf_content = extract_pdf_text(user_pdf) if user_pdf else ""

st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    # On ajoute une option "La suite logique"
    sujet = st.text_input("1. Sujet ?", placeholder="Ex: Guerre Froide... ou tape 'SUITE'")
    st.caption("Tape 'SUITE' pour que je te propose le prochain chapitre logique.")
with col2:
    humeur = st.selectbox("2. Mood ?", ["😴 Chill", "🧐 Curieuse", "🚀 Focus"])

outil_pref = st.radio("3. Outils ?", ["🎲 Mix Surprise", "📺 Vidéo (YouTube/Lumni)", "📱 iPad (Apps)"], horizontal=True)

# --- 5. PROMPT AVEC MÉMOIRE ---
system_prompt = f"""
Tu es le Coach d'Anna (14 ans, 3ème, Réunion).

TES DONNÉES :
1. **HISTORIQUE DE PROGRESSION (CE QUI EST FAIT)** :
   {suivi_text if suivi_text else "Pas d'historique disponible."}
   
2. **BIBLIOTHÈQUE (PROGRAMMES & MANUELS)** :
   {biblio_text[:20000]}

RÈGLES DE PROGRESSION :
- Regarde l'HISTORIQUE ci-dessus.
- Si le sujet demandé est "SUITE", analyse le programme officiel (dans la bibliothèque) et propose le chapitre qui vient juste APRES ceux marqués comme "FAIT" ou "ACQUIS".
- Si Anna demande un sujet précis, vérifie dans l'historique s'il est déjà acquis. Si oui, propose une séance d'approfondissement ou de révision ludique, pas de découverte.

RÈGLES D'OR :
- Vidéos = Liens cliquables obligatoires.
- Zéro pression (Mots bannis : Brevet, Notes).
- Format Markdown clair.

STRUCTURE DE RÉPONSE :
1. **Le Check-Up** : "J'ai vu que tu avais déjà fait [Dernier truc fait]. Aujourd'hui on attaque..."
2. **L'Accroche Fun**.
3. **Le Programme**.
4. **Le Défi**.

---
DEMANDE D'ANNA :
Sujet : {sujet}
Document du jour : {user_pdf_content}
---
"""

# --- 6. GÉNÉRATION ---
if st.button("✨ Lancer ma séance", type="primary"):
    if not sujet and not user_pdf:
        st.warning("Il me faut un sujet (ou tape 'SUITE') !")
    else:
        with st.spinner("Vérification de ta progression et génération..."):
            try:
                requete = f"Sujet: {sujet}. Mood: {humeur}. Outil: {outil_pref}. Instructions: {system_prompt}"
                response = model.generate_content(requete)
                st.markdown(response.text)
                html_data = create_download_link(response.text)
                st.download_button("📥 Télécharger la fiche", html_data, f"Seance_{sujet}.html", "text/html")
            except Exception as e:
                st.error(f"Erreur : {e}")
