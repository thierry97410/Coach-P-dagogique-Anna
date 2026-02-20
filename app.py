import streamlit as st
import google.generativeai as genai

# --- 1. DESIGN "DIAGNOSTIC SEREIN" ---
st.set_page_config(page_title="Joris : Diagnostic API", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #F0FDF4 !important; color: #1E3A8A !important; }
    h1 { color: #1E40AF !important; }
    .stCode { background-color: #FFFFFF !important; border: 1px solid #BFDBFE !important; border-radius: 10px; }
    header { visibility: hidden !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("🔍 Diagnostic des modèles disponibles")
st.write("Thierry, ce code interroge ton API pour lister les moteurs que nous pouvons utiliser pour Anna.")

# --- 2. LOGIQUE DE SCAN ---

if "GOOGLE_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        
        # Récupération de la liste
        available_models = genai.list_models()
        
        st.success("✅ Connexion à l'API réussie !")
        st.subheader("Liste des modèles accessibles pour ta clé :")
        
        # Affichage propre des modèles qui supportent la génération de contenu
        found_any = False
        for m in available_models:
            if 'generateContent' in m.supported_generation_methods:
                st.code(f"{m.name}", language="text")
                st.caption(f"Description : {m.description}")
                found_any = True
        
        if not found_any:
            st.warning("L'API est connectée, mais aucun modèle de génération de contenu n'a été trouvé.")
            
    except Exception as e:
        st.error(f"❌ Erreur lors de l'interrogation de l'API :")
        st.info(f"Détails : {e}")
else:
    st.error("🚨 Clé 'GOOGLE_API_KEY' introuvable dans les Secrets de Streamlit.")
    st.info("Vérifie que la clé est bien enregistrée dans Streamlit Cloud > Settings > Secrets.")

st.divider()
st.write("👉 **Action :** Copie-colle moi la liste des noms (ex: `models/gemini-1.5-flash`) qui s'affiche ci-dessus.")
