import streamlit as st
import google.generativeai as genai
import pypdf

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Le Labo d'Anna", page_icon="islands", layout="centered")

# Clé API
api_key = st.secrets.get("GOOGLE_API_KEY")
if not api_key:
    st.error("Clé API manquante.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-pro')

# --- 2. FONCTION LECTURE PDF ---
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
st.title("🇷🇪 Le Labo d'Anna")
st.write("Ton espace de découverte, sans stress.")

# Zone PDF
with st.expander("📂 Ajouter un document (Cours prof, Exercice...)"):
    pdf_file = st.file_uploader("Glisse ton fichier PDF ici", type=["pdf"])
    pdf_content = ""
    if pdf_file:
        with st.spinner("Je lis le document..."):
            extracted = extract_pdf_text(pdf_file)
            if extracted:
                pdf_content = extracted
                st.success("Document lu ! Je l'intègre à la séance.")

st.markdown("---")

# Les Paramètres
col1, col2 = st.columns(2)
with col1:
    sujet = st.text_input("1. Le sujet du jour ?", placeholder="Ex: Les Volcans, Pythagore...")
with col2:
    humeur = st.selectbox("2. Ton mood ?", [
        "😴 Mode Chill (15 min - Juste écouter)",
        "🧐 Mode Curieuse (30 min - Vidéo + Jeu)",
        "🚀 Mode Focus (45 min - Plan complet)"
    ])

outil_pref = st.radio("3. Tes outils préférés ?", ["🎲 Mix Surprise", "📺 Full Lumni", "📱 Team iPad"], horizontal=True)

# --- 4. LE CERVEAU (TON PROMPT ADAPTÉ) ---
# Ici, j'ai fusionné tes règles pédagogiques avec la logique de l'App
system_prompt = f"""
Tu es le "Coach Pédago Bienveillant" personnel d'Anna (14 ans, 3ème, Réunion).
Tu t'adresses DIRECTEMENT à Anna.

CONTEXTE & MATÉRIEL :
- Lieu : Île de la Réunion (Fais des liens avec la nature locale si possible).
- Matériel : iPad 9 (Apps, Tactile, Audio), Compte Lumni.
- Philosophie : "Curiosité & Sérénité".

RÈGLES D'OR (Non négociables) :
1. **ZÉRO PRESSION :** Tu ne parles JAMAIS d'enjeux futurs (Lycée, Seconde, Brevet, Notes). Ces mots sont BANNIS.
2. **CURIOSITÉ :** Concentre-toi sur l'intérêt immédiat ("Pourquoi c'est cool maintenant").
3. **DOCUMENT :** Si un contenu PDF est fourni ci-dessous, base le cours dessus mais simplifie-le.

STRUCTURE DE TA RÉPONSE (Format Markdown) :

## 1. L'Approche "Douceur" (Le Teaser)
- Une phrase d'intro intrigante ou une anecdote (lien Réunion apprécié).
- Le "Pourquoi c'est cool" : Utilité dans la vraie vie (pas pour l'école).

## 2. La Stratégie Outils
Propose la ressource adaptée ({outil_pref}) :
- **Le Choix du Chef :** Nom de l'outil + LIEN DIRECT.
- **Pourquoi :** Pourquoi ce format est relaxant/ludique ?

## 3. Le "Mode d'Emploi" & Le Jeu "Anna Experte"
- **L'activité :** Quoi faire concrètement (regarder, manipuler sur l'iPad).
- **Le Défi Créatif :** Propose une mini-tâche sur l'iPad (ex: "Enregistre un vocal", "Fais un croquis sur Freeform"). JAMAIS d'exercice type examen.

## 4. Le Filet de Sécurité (Si fatigue)
Une alternative papier/crayon calme (5 min).

---
CONTENU DU PDF FOURNI (Si vide, ignore) :
{pdf_content}
---
"""

# --- 5. GÉNÉRATION ---
if st.button("✨ Lancer ma séance", type="primary"):
    if not sujet and not pdf_file:
        st.warning("Dis-moi au moins quel est le sujet !")
    else:
        with st.spinner("Préparation de ta séance sur mesure..."):
            try:
                requete = f"Sujet: {sujet}. Mood: {humeur}. Outil: {outil_pref}. Instructions: {system_prompt}"
                response = model.generate_content(requete)
                st.markdown(response.text)
                
                # Zone pour Papa (Cachée par défaut)
                with st.expander("👨‍🏫 Zone Parents (Copier le plan)"):
                    st.text_area("Texte brut", value=response.text, height=100)
                    
            except Exception as e:
                st.error(f"Erreur : {e}")

st.markdown("---")
st.caption("Coach Pédago - Mode Curiosité & Sérénité 🇷🇪")
