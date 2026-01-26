import streamlit as st
import google.generativeai as genai
import os

st.set_page_config(page_title="Inspecteur de Clé", page_icon="🕵️‍♂️")

st.title("🕵️‍♂️ Inspecteur de Clé API")

# 1. Vérification de la clé
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("❌ Aucune clé trouvée dans les Secrets.")
    st.stop()
else:
    st.success(f"✅ Clé détectée (commence par : {api_key[:5]}...)")

# 2. Configuration
try:
    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"❌ Erreur de configuration : {e}")

# 3. Interrogation de Google
st.write("---")
st.write("📡 J'interroge les serveurs de Google pour voir vos modèles accessibles...")

if st.button("Lancer l'inspection maintenant"):
    try:
        models = genai.list_models()
        found_models = []
        
        st.write("### 📋 Résultat de l'enquête :")
        
        for m in models:
            # On cherche les modèles capables de générer du texte (generateContent)
            if 'generateContent' in m.supported_generation_methods:
                st.markdown(f"- ✅ **`{m.name}`**")
                found_models.append(m.name)
        
        if not found_models:
            st.warning("Aucun modèle de génération de texte trouvé. La clé semble valide mais n'a accès à rien.")
        else:
            st.success(f"🎉 Victoire ! Ta clé a accès à {len(found_models)} modèles.")
            st.info("Copie le nom exact d'un des modèles ci-dessus (ex: models/gemini-1.5-flash) pour l'utiliser.")
            
    except Exception as e:
        st.error(f"❌ Erreur critique lors de la connexion : {e}")
        st.warning("Il est possible que ta clé API n'ait pas les droits 'Generative Language API' activés dans la console Google Cloud.")
