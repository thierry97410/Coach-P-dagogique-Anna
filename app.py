import streamlit as st
import google.generativeai as genai
import pypdf

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Le Labo d'Anna", page_icon="🧠", layout="centered")

# Récupération de la clé API
api_key = st.secrets.get("GOOGLE_API_KEY")
if not api_key:
    st.error("Oups ! Clé API introuvable.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-pro')

# --- 2. FONCTION POUR LIRE LE PDF ---
def extract_pdf_text(uploaded_file):
    try:
        pdf_reader = pypdf.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        return None

# --- 3. L'INTERFACE ---
st.title("👋 Salut Anna !")
st.write("Configure ta séance (avec ou sans tes cours).")

# ZONE DÉPÔT DE FICHIER (Menu déroulant discret)
with st.expander("📂 J'ai un document de cours (PDF) à utiliser"):
    pdf_file = st.file_uploader("Glisse ton fichier ici", type=["pdf"])
    pdf_content = ""
    
    if pdf_file:
        with st.spinner("Analyse du document en cours..."):
            extracted_text = extract_pdf_text(pdf_file)
            if extracted_text:
                pdf_content = extracted_text
                st.success("✅ Document lu ! Je vais m'appuyer dessus.")
            else:
                st.error("Impossible de lire ce PDF.")

st.markdown("---")

# LES PARAMÈTRES
col1, col2 = st.columns(2)
with col1:
    sujet = st.text_input("1. Le sujet ?", placeholder="Ex: La Guerre Froide...")
with col2:
    humeur = st.selectbox("2. Ton énergie ?", [
        "😴 Mode Chill (15 min - Juste écouter)",
        "🧐 Mode Curieuse (30 min - Vidéo + Jeu)",
        "🚀 Mode Focus (45 min - Plan complet)"
    ])

outil_pref = st.radio("3. Outil ?", ["🎲 Mix Surprise", "📺 Lumni", "📱 iPad"], horizontal=True)

# --- 4. LE CERVEAU (Prompt) ---
system_prompt = f"""
Tu es le coach personnel d'Anna (14 ans, 3ème, Réunion).
TON OBJECTIF : Créer une séance sur mesure pour elle.

RÈGLES CAPITALES :
1. Si un CONTENU PDF est fourni ci-dessous, tu DOIS construire la séance en utilisant ces informations (définitions, dates, contexte du prof).
2. Zéro pression : sois cool, encourageante, pas de "scolaire".
3. Structure de réponse :
   - Titre Fun
   - Teaser (Accroche)
   - Le Programme (Étapes claires avec liens ou consignes iPad)
   - Le Défi "Anna Experte" (Validation ludique)

---
CONTENU DU DOCUMENT PDF FOURNI PAR ANNA :
{pdf_content if pdf_content else "Aucun document fourni. Utilise ta culture générale."}
---
"""

# --- 5. BOUTON ACTION ---
if st.button("✨ Générer ma séance", type="primary"):
    if not sujet and not pdf_file:
        st.warning("Il me faut au moins un sujet ou un fichier PDF !")
    else:
        with st.spinner("Je prépare ton programme..."):
            try:
                # On envoie tout à l'IA
                requete = f"Sujet: {sujet}. Énergie: {humeur}. Outil: {outil_pref}. Instructions système: {system_prompt}"
                response = model.generate_content(requete)
                st.markdown(response.text)
                
                # Petit bloc pour copier le plan (pour Papa)
                with st.expander("📝 Copier le plan (Format Texte)"):
                    st.code(response.text)
                    
            except Exception as e:
                st.error(f"Erreur : {e}")

st.markdown("---")
st.caption("Coach Cap 2nde - Lecture PDF activée")
