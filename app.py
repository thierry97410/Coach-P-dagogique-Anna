import streamlit as st
import google.generativeai as genai
import os

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Le Labo d'Anna",
    page_icon="🧠",
    layout="centered"
)

# --- 2. CONNEXION À L'IA (LA CLÉ) ---
# On va chercher la clé dans les "Secrets" de Streamlit
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    # Si on teste sur son propre PC sans les secrets, on peut mettre la clé ici provisoirement
    # Mais pour la mise en ligne, il faudra utiliser les Secrets
    st.info("👋 Bonjour Thierry ! Pour que l'app fonctionne en ligne, n'oublie pas de configurer la clé dans les Secrets sur share.streamlit.io")
    st.stop()

# Configuration du moteur
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-pro')

# --- 3. L'INTERFACE (CE QU'ANNA VOIT) ---
st.title("👋 Salut Anna !")
st.write("Configure ta séance selon ton envie du moment.")

st.markdown("---")

# Les 3 questions pour Anna
col1, col2 = st.columns(2)

with col1:
    sujet = st.text_input("1. On explore quel sujet ?", placeholder="Ex: Les Volcans, Pythagore, English...")

with col2:
    humeur = st.selectbox(
        "2. Ton énergie actuelle ?",
        [
            "😴 Mode Chill (15 min - Juste écouter)",
            "🧐 Mode Curieuse (30 min - Vidéo + Jeu)",
            "🚀 Mode Focus (45 min - Plan complet)"
        ]
    )

outil_pref = st.radio(
    "3. Ta préférence d'outil ?",
    ["🎲 Surprends-moi", "📺 Full Lumni (Vidéo)", "📱 Team iPad (Apps & Tactile)"],
    horizontal=True
)

st.markdown("---")

# --- 4. LE PROMPT SYSTÈME (TON COACH PÉDAGO) ---
system_prompt = """
Tu es le moteur pédagogique de l'application "Anna's Learning App".
Ton rôle est de générer une séance sur mesure pour Anna (14 ans, 3ème, Réunion, refus scolaire anxieux).

CONTEXTE :
- Lieu : Île de la Réunion.
- Matériel : iPad 9 (Apps, Tactile), Compte Lumni Premium.
- Philosophie : Zéro pression, curiosité pure. Pas de mention d'enjeux futurs (Lycée/Brevet).

RÈGLES DE GÉNÉRATION SELON LES PARAMÈTRES :

A. Si "Mode Chill" (15 min) :
   - Contenu 100% passif (Vidéo Lumni ou Podcast).
   - Pas d'exercice. Juste de la découverte.

B. Si "Mode Curieuse" (30 min) :
   - Mix : Vidéo/Contenu + Une activité interactive sur iPad (Simulateur, Quiz, Schéma).

C. Si "Mode Focus" (45 min) :
   - Plan complet : Intro Fun + Contenu + Activité créative + Synthèse.

D. Gestion des Outils :
   - Si "Full Lumni" : Force l'usage de Lumni.
   - Si "Team iPad" : Propose Apps natives (Freeform, Dictée), Sites web interactifs.
   - Si "Surprends-moi" : Fais un mix équilibré.

FORMAT DE SORTIE ATTENDU (Markdown) :
Ne dis pas bonjour. Affiche directement :

## 🎯 [Titre Fun de la Séance]

### 🥑 L'Accroche
[Une phrase intrigante pour capter l'attention]

### ⏱️ Le Programme
1. **[Titre Étape 1]** : [Lien URL direct cliquable]
   *Pourquoi c'est cool :* [Une phrase]

2. **[Titre Étape 2]** : [Consigne iPad précise]
   *L'activité :* [Instructions simples]

### ✨ Le petit défi "Anna Experte"
[Une micro-tâche de validation sans stress : audio, dessin, explication orale]

---
*(Généré pour le profil : 3ème / Réunion)*
"""

# --- 5. LE BOUTON MAGIQUE ---
if st.button("✨ Générer ma séance", type="primary"):
    if not sujet:
        st.warning("Oups ! Tu as oublié de dire quel sujet t'intéresse.")
    else:
        with st.spinner("Je connecte les neurones..."):
            try:
                # On assemble la requête pour l'IA
                requete_finale = f"""
                Génère une séance pour Anna avec ces paramètres :
                - SUJET : {sujet}
                - ÉNERGIE : {humeur}
                - OUTIL : {outil_pref}
                
                Instructions système à suivre impérativement : {system_prompt}
                """
                
                # Appel à Gemini
                response = model.generate_content(requete_finale)
                
                # Affichage du résultat
                st.markdown(response.text)
                
            except Exception as e:
                st.error(f"Une petite erreur est survenue : {e}")

# Footer
st.markdown("---")
st.caption("Coach Cap 2nde - Propulsé par Gemini Pro")
