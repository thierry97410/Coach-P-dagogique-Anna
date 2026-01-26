import streamlit as st
import google.generativeai as genai
import pypdf
import os

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Le Labo d'Anna", page_icon="🇷🇪", layout="centered")

# Clé API
api_key = st.secrets.get("GOOGLE_API_KEY")
if not api_key:
    st.error("Clé API manquante.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-pro')

# --- 2. FONCTIONS ---

def extract_pdf_text(file_path_or_buffer):
    """Lit un PDF (chemin fichier ou buffer mémoire)"""
    try:
        pdf_reader = pypdf.PdfReader(file_path_or_buffer)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception:
        return "" # On ignore silencieusement les fichiers illisibles

def load_bibliotheque(folder_name):
    """Lit TOUS les PDF du dossier spécifié"""
    combined_text = ""
    liste_fichiers = []
    
    if os.path.exists(folder_name):
        files = os.listdir(folder_name)
        for filename in files:
            if filename.lower().endswith(".pdf"):
                path = os.path.join(folder_name, filename)
                with open(path, "rb") as f:
                    text = extract_pdf_text(f)
                    if text:
                        combined_text += f"\n--- SOURCE : {filename} ---\n{text}"
                        liste_fichiers.append(filename)
    return combined_text, liste_fichiers

def create_download_link(content):
    html = f"""
    <html><head><style>body {{ font-family: sans-serif; max-width: 800px; margin: auto; padding: 20px; }} h2 {{ color: #2e86c1; }} a {{ color: #e74c3c; }} </style></head><body>
    {content.replace(chr(10), '<br>').replace('**', '<b>').replace('## ', '<h2>').replace('### ', '<h3>')}
    </body></html>
    """
    return html.encode('utf-8')

# --- 3. CHARGEMENT DE LA MÉMOIRE (AUTO) ---
# On charge tout le dossier 'bibliotheque'
biblio_text, fichiers_charges = load_bibliotheque("bibliotheque")

# --- 4. INTERFACE ---
st.title("🇷🇪 Le Labo d'Anna")

# Affichage discret des sources chargées
if fichiers_charges:
    with st.expander(f"📚 Bibliothèque active ({len(fichiers_charges)} documents)"):
        st.write("Je me réfère à :")
        for f in fichiers_charges:
            st.caption(f"- {f}")
else:
    st.info("Aucun document de référence trouvé dans le dossier 'bibliotheque'.")

# Zone PDF du jour (Devoir spécifique)
with st.expander("📂 Ajouter un document spécifique (Devoir du jour)"):
    user_pdf = st.file_uploader("Glisse le fichier ici", type=["pdf"])
    user_pdf_content = ""
    if user_pdf:
        user_pdf_content = extract_pdf_text(user_pdf)
        st.success("Document du jour analysé.")

st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    sujet = st.text_input("1. Sujet ?", placeholder="Ex: Guerre Froide...")
with col2:
    humeur = st.selectbox("2. Mood ?", ["😴 Chill (Pas d'effort)", "🧐 Curieuse (Jeu)", "🚀 Focus (Cours complet)"])

outil_pref = st.radio("3. Outils ?", ["🎲 Mix Surprise", "📺 Vidéo (YouTube/Lumni)", "📱 iPad (Apps)"], horizontal=True)

# --- 5. LE PROMPT ---
system_prompt = f"""
Tu es le Coach d'Anna (14 ans, 3ème, Réunion).
Tu t'adresses à ELLE.

TES SOURCES DE VÉRITÉ :
1. **BIBLIOTHÈQUE PERMANENTE** : Tu disposes ci-dessous de textes extraits de manuels et programmes officiels. Utilise-les pour valider tes explications.
2. **DOCUMENT DU JOUR** : S'il y en a un, c'est la priorité absolue.

RÈGLES D'OR :
- **YOUTUBE/VIDÉO :** Si l'outil est "Vidéo" ou "Mix", fournis des liens cliquables (YouTube/Lumni).
- **ZÉRO PRESSION :** Mots bannis : Brevet, Lycée, Notes, Examens.
- **STYLE :** Markdown clair, ton encourageant, lien avec la Réunion.

STRUCTURE DE RÉPONSE :
1. **L'Accroche (Teaser)** : Lien avec la Réunion ou anecdote.
2. **Le Programme** : Activités concrètes.
3. **Le Défi Anna** : Création sans note.

---
📚 CONTENU DE LA BIBLIOTHÈQUE (Extraits) :
{biblio_text[:25000]} 
(Limité pour la mémoire)

📄 DOCUMENT DU JOUR (Devoir) :
{user_pdf_content}
---
"""

# --- 6. BOUTON ACTION ---
if st.button("✨ Lancer ma séance", type="primary"):
    if not sujet and not user_pdf:
        st.warning("Il me faut un sujet !")
    else:
        with st.spinner("Je consulte ma bibliothèque et je prépare tout..."):
            try:
                requete = f"Sujet: {sujet}. Mood: {humeur}. Outil: {outil_pref}. Instructions: {system_prompt}"
                response = model.generate_content(requete)
                st.markdown(response.text)
                
                # Téléchargement
                html_data = create_download_link(response.text)
                st.download_button(
                    label="📥 Télécharger la fiche",
                    data=html_data,
                    file_name=f"Seance_Anna_{sujet}.html",
                    mime="text/html"
                )
            except Exception as e:
                st.error(f"Erreur : {e}")
