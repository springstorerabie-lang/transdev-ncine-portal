# Portail Transdev NCINE + Gemini

Cette version du portail garde la règle de confidentialité suivante :
- l'utilisateur saisit uniquement son **NCINE**
- l'application récupère **une seule ligne** (celle du NCINE)
- **Gemini reformule uniquement cette ligne** pour rendre la réponse plus naturelle en français

## Fonctionnalités
- Page utilisateur : affichage des données d'un seul NCINE
- Réponse conversationnelle via Gemini si `GEMINI_API_KEY` est configurée
- Affichage structuré des champs de la ligne trouvée
- Page admin :
  - modification du titre
  - modification de la notification globale
  - affichage/masquage de la notification via un toggle
  - actualisation des données
  - consultation complète des lignes
- Deux sources de données possibles :
  - `excel`
  - `google_sheets`

## Installation
```powershell
cd D:\downloads\transdev-ncine-portal-gemini
py -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

## Variables `.env`
### Gemini
- `GEMINI_API_KEY` : clé créée dans Google AI Studio
- `GEMINI_MODEL` : par défaut `gemini-3-flash-preview`

### Source de données
#### Mode Excel
- `DATA_SOURCE=excel`
- `EXCEL_FILE_PATH=data/UtilisateursChatbot3.xlsx`
- `EXCEL_SHEET_NAME=UtilisateursChatbot`

#### Mode Google Sheets
- `DATA_SOURCE=google_sheets`
- `GOOGLE_SERVICE_ACCOUNT_FILE=secrets/google-service-account.json`
- `GOOGLE_SHEETS_SPREADSHEET_ID=...`
- `GOOGLE_SHEETS_WORKSHEET=UtilisateursChatbot`

## Passer plus tard à Google Sheets
1. Créer ou utiliser un projet Google Cloud
2. Activer l'API Google Sheets
3. Créer un service account et télécharger le fichier JSON
4. Partager la feuille Google avec l'email du service account en mode Lecteur
5. Placer le JSON dans `secrets/google-service-account.json`
6. Remplir `GOOGLE_SHEETS_SPREADSHEET_ID`
7. Mettre `DATA_SOURCE=google_sheets`
8. Redémarrer l'application

## Routes principales
- `/` : page utilisateur
- `/admin/login` : connexion admin
- `/admin` : interface admin
- `/api/public/config` : titre / notification / source
- `/api/user/lookup` : recherche par NCINE

## Remarque sécurité
Cette version améliore la confidentialité en ne renvoyant qu'une seule ligne par NCINE, mais ce n'est pas encore une authentification forte. Si quelqu'un connaît le NCINE d'une autre personne, il pourrait encore consulter sa ligne. L'étape suivante recommandée est d'ajouter un mot de passe ou un code personnel par utilisateur.
