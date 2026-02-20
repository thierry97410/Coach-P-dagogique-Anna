import streamlit as st
import pandas as pd
import os
from PyPDF2 import PdfReader
import google.generativeai as genai

# --- CONFIGURATION ---
st.set_page_config(page_title="Le Coach d'Anna", layout="wide")

# Vérification de ta clé (nommée GOOGLE_API_KEY comme tu l'as indiqué)
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("🚨 ERREUR : La clé 'GOOGLE_API_KEY' est absente des secrets Streamlit.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-pro')

# --- FONCTIONS TECHNIQUES ---

def extract_pdf_text(file):
    """Extrait le texte d'un PDF."""
    try:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
        return text
    except Exception as e:
        return f"Erreur de lecture PDF : {e}"

@st.cache_data
def get_subject_content(folder, matiere):
    """
    Charge les PDF de la matière. 
    STRATÉGIE FAIL-FAST : L'appli s'arrête si aucun fichier ne correspond.
    """
    if not os.path.exists(folder):
        st.error(f"❌ DOSSIER INTROUVABLE : Le dossier '{folder}' n'existe pas sur GitHub.")
        st.stop()
    
    # On prend les 4 premières lettres pour le préfixe (MATH, FRAN, HIST, SVT, PHYS, TECH, ENSE)
    prefix = matiere[:4].upper()
    files = [f for f in os.listdir(folder) if f.upper().startswith(prefix) and f.lower().endswith(".pdf")]
    
    if not files:
        st.error(f"🚨 ERREUR CRITIQUE : Aucun fichier PDF trouvé pour '{matiere}' (préfixe attendu : {prefix}_).")
        st.info("L'outil refuse de générer du contenu sans sources officielles pour Anna. Vérifie tes noms de fichiers sur GitHub.")
        st.stop()
    
    full_text = ""
    for filename in files:
        with open(os.path.join(folder, filename), "rb") as f:
            full_text += f"\n--- SOURCE OFFICIELLE : {filename} ---\n"
            full_text += extract_pdf_text(f)
            
    return full_text[:120000] # Limite de sécurité pour le contexte

# --- INTERFACE UTILISATEUR ---

st.title("🎓 Le Coach Scolaire d'Anna")
st.markdown(f"**Objectif :** Continuité pédagogique (Niveau 3ème)")

# Chargement du CSV de structure
if not os.path.exists("bibliotheque/programme.csv"):
    st.error("🚨 FICHIER MANQUANT : 'programme.csv' est introuvable dans le dossier 'bibliotheque'.")
    st.stop()

df_prog = pd.read_csv("bibliotheque/programme.csv", sep=";")

# Barre latérale de navigation
with st.sidebar:
    st.header("📖 Programme")
    liste_matieres = df_prog["Matiere"].unique()
    choix_matiere = st.selectbox("Matière", liste_matieres)
    
    chapitres = df_prog[df_prog["Matiere"] == choix_matiere]["Chapitre"].tolist()
    choix_chapitre = st.selectbox("Chapitre à travailler", chapitres)
    
    st.divider()
    doc_eleve = st.file_uploader("Document d'exercice ou cours collège (PDF)", type="pdf")

# Entrée du sujet
sujet = st.text_input("Quelle notion Anna doit-elle aborder ?", 
                      placeholder="Ex: Explique-moi les puissances de 10 ou aide-moi pour cet exercice.")

if st.button("🚀 Lancer la séance", type="primary"):
    if not sujet and not doc_eleve:
        st.warning("Précise un sujet ou télécharge un document pour commencer.")
    else:
        with st.spinner("Joris prépare la leçon..."):
            # Récupération des données (Plante ici si fichiers mal nommés)
            contexte_officiel = get_subject_content("bibliotheque", choix_matiere)
            contexte_exercice = extract_pdf_text(doc_eleve) if doc_eleve else "Aucun document supplémentaire."
            
            prompt = f"""
            Tu es Joris, le tuteur d'Anna. Elle est en 3ème, déscolarisée pour anxiété, et travaille seule.
            Tu es sa seule source de cours fiable en attendant le CNED.
            
            MATIÈRE : {choix_matiere}
            CHAPITRE : {choix_chapitre}
            DEMANDE SPÉCIFIQUE : {sujet}

            SOURCES OFFICIELLES (Bibliothèque) :
            {contexte_officiel}

            DOCUMENT DE TRAVAIL (Exercice) :
            {contexte_exercice}

            TA MISSION :
            1. Explique la notion de façon claire et structurée.
            2. Si un exercice est fourni, accompagne-la dans la résolution SANS donner la réponse brute.
            3. Sois direct, bienveillant mais exigeant sur la méthode.
            4. Termine obligatoirement par une section '### 📝 Quiz rapide' avec 3 questions de compréhension.
            """
            
            try:
                response = model.generate_content(prompt)
                st.markdown("---")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Erreur de communication avec l'IA : {e}")

# Footer
st.caption("Mode sécurité : L'application s'arrête si les sources PDF ne sont pas synchronisées avec le CSV.")
