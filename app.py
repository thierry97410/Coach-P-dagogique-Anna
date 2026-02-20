import streamlit as st
import pandas as pd
import os
from PyPDF2 import PdfReader
import google.generativeai as genai

# --- 1. CONFIGURATION ET SÉCURITÉ ---
st.set_page_config(page_title="Le Coach d'Anna", layout="wide")

# Utilisation de ton nom de clé : GOOGLE_API_KEY
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("🚨 CLÉ API MANQUANTE : Ajoute 'GOOGLE_API_KEY' dans les Secrets de Streamlit.")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-pro')

# --- 2. FONCTIONS DE LECTURE ---

def extract_pdf_text(file):
    """Extrait le texte brut d'un PDF pour l'IA."""
    try:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
        return text
    except Exception as e:
        return f"Erreur technique de lecture PDF : {e}"

@st.cache_data
def get_subject_content(folder, matiere):
    """
    Charge les fichiers PDF. 
    L'application S'ARRÊTE si aucun fichier ne correspond au préfixe.
    """
    if not os.path.exists(folder):
        st.error(f"❌ DOSSIER BIBLIOTHÈQUE INTROUVABLE : Crée le dossier '{folder}' sur GitHub.")
        st.stop()
    
    # On prend les 4 premières lettres (MATH, FRAN, HIST, SVT, PHYS, TECH, ENSE)
    prefix = matiere[:4].upper()
    files = [f for f in os.listdir(folder) if f.upper().startswith(prefix) and f.lower().endswith(".pdf")]
    
    if not files:
        st.error(f"🚨 FICHIER MANQUANT : Aucun PDF trouvé pour '{matiere}' (préfixe '{prefix}_' attendu).")
        st.info(f"Vérifie que tes fichiers dans '{folder}' commencent bien par {prefix}_")
        st.stop()
    
    full_text = ""
    for filename in files:
        path = os.path.join(folder, filename)
        with open(path, "rb") as f:
            full_text += f"\n--- SOURCE OFFICIELLE : {filename} ---\n"
            full_text += extract_pdf_text(f)
            
    return full_text[:120000] # Sécurité de contexte (env. 200 pages)

# --- 3. CHARGEMENT DES DONNÉES (CSV) ---

CSV_PATH = "bibliotheque/programme.csv"
if not os.path.exists(CSV_PATH):
    st.error(f"🚨 CSV MANQUANT : Le fichier '{CSV_PATH}' est introuvable.")
    st.stop()

# Lecture avec le séparateur VIRGULE comme dans ton fichier
try:
    df_prog = pd.read_csv(CSV_PATH, sep=",")
    # On nettoie les espaces éventuels dans les noms de colonnes
    df_prog.columns = df_prog.columns.str.strip()
except Exception as e:
    st.error(f"🚨 ERREUR CSV : Impossible de lire le fichier. Détails : {e}")
    st.stop()

# --- 4. INTERFACE UTILISATEUR ---

st.title("🎓 Le Coach Scolaire d'Anna")
st.markdown("---")

with st.sidebar:
    st.header("📚 Session de travail")
    
    # Choix de la matière
    if "Matiere" in df_prog.columns:
        liste_matieres = df_prog["Matiere"].unique()
        choix_matiere = st.selectbox("Matière", liste_matieres)
        
        # Choix du chapitre (filtré par matière)
        chapitres = df_prog[df_prog["Matiere"] == choix_matiere]["Chapitre"].tolist()
        choix_chapitre = st.selectbox("Chapitre", chapitres)
    else:
        st.error("🚨 COLONNE MANQUANTE : 'Matiere' introuvable dans le CSV.")
        st.stop()
    
    st.divider()
    doc_eleve = st.file_uploader("Ajouter un document d'exercice (Optionnel)", type="pdf")

# Entrée du sujet par l'utilisateur
sujet_travail = st.text_input("Sur quoi Anna veut-elle travailler ?", 
                               placeholder="Ex: Explique-moi le cours / Aide-moi pour l'exercice 2...")

if st.button("🚀 Lancer la séance", type="primary"):
    if not sujet_travail and not doc_eleve:
        st.warning("Indique un sujet ou dépose un document pour que Joris puisse t'aider.")
    else:
        with st.spinner("Joris analyse tes documents..."):
            # Récupération du contenu (fail-fast si préfixe PDF non trouvé)
            contexte_biblio = get_subject_content("bibliotheque", choix_matiere)
            contexte_eleve = extract_pdf_text(doc_eleve) if doc_eleve else "Aucun document d'exercice."

            # Construction du Prompt
            prompt = f"""
            Tu es Joris, le tuteur d'Anna (élève de 3ème travaillant seule). 
            Elle compte sur toi pour remplacer ses professeurs absents.

            CONTEXTE OFFICIEL (Bibliothèque) :
            {contexte_biblio}

            TRAVAIL DEMANDÉ :
            Matière : {choix_matiere}
            Chapitre : {choix_chapitre}
            Question d'Anna : {sujet_travail}
            Document fourni : {contexte_eleve}

            INSTRUCTIONS :
            1. Sois direct, pédagogique et utilise les méthodes des documents officiels.
            2. Ne donne JAMAIS la solution d'un exercice directement, guide-la.
            3. Si la demande est hors sujet par rapport au chapitre, recadre-la poliment.
            4. TERMINE TOUJOURS par une section '### 📝 Quiz de fin' avec 3 questions rapides pour tester sa compréhension.
            """

            try:
                response = model.generate_content(prompt)
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Erreur de génération : {e}")

# --- PIED DE PAGE ---
st.caption("Sécurité activée : L'application exige des fichiers sources valides pour fonctionner.")
