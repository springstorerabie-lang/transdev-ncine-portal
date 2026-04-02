from __future__ import annotations

import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.services.ai_service import AIService
from app.services.settings_service import SettingsService
from app.services.sheet_service import UserDataService

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "app" / "static"
DEFAULT_EXCEL = BASE_DIR / "data" / "UtilisateursChatbot3.xlsx"

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Tr@n$dev2026")
SESSION_COOKIE_NAME = "transdev_admin_session"

DATA_SOURCE = os.getenv("DATA_SOURCE", "excel").strip().lower()
EXCEL_FILE_PATH = os.getenv("EXCEL_FILE_PATH", str(DEFAULT_EXCEL))
EXCEL_SHEET_NAME = os.getenv("EXCEL_SHEET_NAME", "UtilisateursChatbot")
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv(
    "GOOGLE_SERVICE_ACCOUNT_FILE",
    "secrets/google-service-account.json",
)
GOOGLE_SHEETS_SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "")
GOOGLE_SHEETS_WORKSHEET = os.getenv("GOOGLE_SHEETS_WORKSHEET", "UtilisateursChatbot")
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

sheet_service = UserDataService(
    data_source=DATA_SOURCE,
    excel_file_path=str(BASE_DIR / EXCEL_FILE_PATH) if not Path(EXCEL_FILE_PATH).is_absolute() else EXCEL_FILE_PATH,
    excel_sheet_name=EXCEL_SHEET_NAME,
    service_account_file=str(BASE_DIR / GOOGLE_SERVICE_ACCOUNT_FILE)
    if not Path(GOOGLE_SERVICE_ACCOUNT_FILE).is_absolute()
    else GOOGLE_SERVICE_ACCOUNT_FILE,
    spreadsheet_id=GOOGLE_SHEETS_SPREADSHEET_ID,
    worksheet_name=GOOGLE_SHEETS_WORKSHEET,
)
settings_service = SettingsService(DATABASE_URL)
ai_service = AIService()

app = FastAPI(title="Portail Transdev Gemini", version="3.0.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

admin_sessions: set[str] = set()


class NcineRequest(BaseModel):
    ncine: str


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class SettingsUpdateRequest(BaseModel):
    title: str
    announcement_text: str
    announcement_enabled: bool


class AdminSummaryRequest(BaseModel):
    summary_type: str
    limit: int = 10


def is_admin(request: Request) -> bool:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    return bool(token and token in admin_sessions)


def require_admin(request: Request) -> None:
    if not is_admin(request):
        raise HTTPException(status_code=401, detail="Accès administrateur requis.")


def get_first_non_empty(item: dict, *keys: str) -> str:
    for key in keys:
        value = str(item.get(key, "")).strip()
        if value:
            return value
    return ""


def build_user_message(item: dict) -> str:
    name = get_first_non_empty(item, "nom_prenom", "nom", "name")
    last_update = get_first_non_empty(
        item,
        "mise_a_jour",
        "last_updated",
        "derniere_mise_a_jour",
        "date_mise_a_jour",
        "updated_at",
    )

    first_line = f"Bonjour {name}" if name else "Bonjour"
    second_line = f"Dernière mise à jour : {last_update or 'Non disponible'}"

    return f"{first_line}\n{second_line}"


@app.get("/")
def user_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "user.html")


@app.get("/api/status")
def status() -> dict:
    return {
        "app_name": "Assistant Transdev",
        "data_source": DATA_SOURCE,
        "worksheet": GOOGLE_SHEETS_WORKSHEET,
        "spreadsheet_id_configured": bool(GOOGLE_SHEETS_SPREADSHEET_ID),
        "excel_path": EXCEL_FILE_PATH,
        "gemini_enabled": bool(os.getenv("GEMINI_API_KEY", "")),
        "settings_backend": settings_service.backend,
    }


@app.get("/admin/login")
def admin_login_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "admin_login.html")


@app.get("/admin")
def admin_page(request: Request) -> FileResponse:
    if not is_admin(request):
        return FileResponse(STATIC_DIR / "admin_login.html")
    return FileResponse(STATIC_DIR / "admin.html")


@app.get("/api/public/config")
def public_config() -> dict:
    settings = settings_service.get_public_settings()
    metadata = sheet_service.metadata()
    return {
        **settings,
        **metadata,
        "ai_enabled": ai_service.enabled,
        "ai_model": ai_service.model if ai_service.enabled else None,
    }


@app.post("/api/user/lookup")
def user_lookup(payload: NcineRequest) -> dict:
    ncine = payload.ncine.strip()
    if not ncine:
        raise HTTPException(status_code=400, detail="Veuillez saisir un NCINE.")

    row = sheet_service.find_user_by_ncine(ncine)
    if not row:
        raise HTTPException(status_code=404, detail="Aucune donnée trouvée pour ce NCINE.")

    return {
        "item": row,
        "labels": sheet_service.get_column_labels(),
        "message": build_user_message(row),
    }


@app.post("/api/admin/login")
def admin_login(payload: AdminLoginRequest, response: Response) -> dict:
    if payload.username.strip() != ADMIN_USERNAME or payload.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Identifiants administrateur invalides.")

    token = secrets.token_urlsafe(32)
    admin_sessions.add(token)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    return {"message": "Connexion administrateur réussie."}


@app.post("/api/admin/logout")
def admin_logout(request: Request, response: Response) -> dict:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token and token in admin_sessions:
        admin_sessions.discard(token)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return {"message": "Déconnexion réussie."}


@app.get("/api/admin/me")
def admin_me(request: Request) -> dict:
    require_admin(request)
    return {"authenticated": True, "username": ADMIN_USERNAME}


@app.get("/api/admin/config")
def admin_get_config(request: Request) -> dict:
    require_admin(request)
    settings = settings_service.get_public_settings()
    metadata = sheet_service.metadata()
    return {**settings, **metadata, "data_source": metadata["data_source"]}


@app.post("/api/admin/config")
def admin_update_config(payload: SettingsUpdateRequest, request: Request) -> dict:
    require_admin(request)
    settings_service.update_settings(
        title=payload.title,
        announcement_text=payload.announcement_text,
        announcement_enabled=payload.announcement_enabled,
    )
    return {"message": "Paramètres enregistrés avec succès."}


@app.post("/api/admin/refresh")
def admin_refresh(request: Request) -> dict:
    require_admin(request)
    sheet_service.refresh()
    return {"message": "Les données ont été rechargées avec succès."}


@app.get("/api/admin/users")
def admin_users(request: Request) -> dict:
    require_admin(request)
    return {
        "items": sheet_service.all_rows(),
        "labels": sheet_service.get_column_labels(),
    }


@app.get("/api/admin/top-absences")
def admin_top_absences(request: Request, limit: int = 10) -> dict:
    require_admin(request)

    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="La limite doit être comprise entre 1 et 100.")

    items = sheet_service.top_absences(limit=limit)
    return {
        "items": items,
        "count": len(items),
        "limit": limit,
    }


@app.get("/api/admin/anomalies")
def admin_anomalies(request: Request, limit: int = 100) -> dict:
    require_admin(request)

    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="La limite doit être comprise entre 1 et 500.")

    items = sheet_service.anomalies(limit=limit)
    return {
        "items": items,
        "labels": sheet_service.get_column_labels(),
        "count": len(items),
        "limit": limit,
    }


@app.post("/api/admin/ai-summary")
def admin_ai_summary(payload: AdminSummaryRequest, request: Request) -> dict:
    require_admin(request)

    summary_type = payload.summary_type.strip().lower()
    limit = payload.limit

    if summary_type not in {"top_absences", "anomalies"}:
        raise HTTPException(
            status_code=400,
            detail="Le type de résumé doit être 'top_absences' ou 'anomalies'.",
        )

    if summary_type == "top_absences":
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=400,
                detail="La limite des absences doit être comprise entre 1 et 100.",
            )
        items = sheet_service.top_absences(limit=limit)
    else:
        if limit < 1 or limit > 500:
            raise HTTPException(
                status_code=400,
                detail="La limite des anomalies doit être comprise entre 1 et 500.",
            )
        items = sheet_service.anomalies(limit=limit)

    summary = ai_service.summarize_admin_results(summary_type, items)

    return {
        "summary_type": summary_type,
        "count": len(items),
        "limit": limit,
        "summary": summary,
        "ai_enabled": ai_service.enabled,
        "ai_model": ai_service.model if ai_service.enabled else None,
    }


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return JSONResponse(status_code=500, content={"detail": f"Erreur serveur inattendue : {exc}"})


@app.get("/api/debug/storage")
def debug_storage() -> dict:
    return {
        "settings_backend": getattr(settings_service, "backend", "unknown"),
        "database_url_configured": bool(DATABASE_URL),
    }