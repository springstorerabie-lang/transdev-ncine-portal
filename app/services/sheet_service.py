from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from pathlib import Path
from typing import Any

import gspread
import pandas as pd


class UserDataService:
    def __init__(
        self,
        *,
        data_source: str,
        excel_file_path: str,
        excel_sheet_name: str,
        service_account_file: str,
        spreadsheet_id: str,
        worksheet_name: str,
        cache_seconds: int = 30,
    ) -> None:
        self.data_source = (data_source or "excel").strip().lower()
        self.excel_file_path = excel_file_path
        self.excel_sheet_name = excel_sheet_name
        self.service_account_file = service_account_file
        self.spreadsheet_id = spreadsheet_id
        self.worksheet_name = worksheet_name
        self.cache_seconds = cache_seconds
        self._cached_df: pd.DataFrame | None = None
        self._cached_at: float = 0.0
        self._column_labels: dict[str, str] = {}

    def _get_gspread_client(self):
        service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()

        if service_account_json:
            creds_dict = json.loads(service_account_json)
            return gspread.service_account_from_dict(creds_dict)

        service_account_path = Path(self.service_account_file)
        if not service_account_path.exists():
            raise FileNotFoundError(
                f"Fichier de compte de service introuvable : {service_account_path}"
            )

        return gspread.service_account(filename=str(service_account_path))

    def _strip_accents(self, value: str) -> str:
        return "".join(
            char for char in unicodedata.normalize("NFKD", value)
            if not unicodedata.combining(char)
        )

    def _normalize_column(self, name: str) -> str:
        name = self._strip_accents(str(name).strip().lower())
        name = re.sub(r"[^a-z0-9]+", "_", name)
        return name.strip("_")

    def _normalize_text(self, value: Any) -> str:
        text = self._strip_accents(str(value).strip().lower())
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _prepare_df(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            raise ValueError("La source de données est vide.")

        original_columns = [str(col).strip() for col in df.columns]
        normalized_columns = [self._normalize_column(col) for col in original_columns]

        self._column_labels = {
            norm: original
            for norm, original in zip(normalized_columns, original_columns)
        }

        df.columns = normalized_columns
        df = df.fillna("")

        for col in list(df.columns):
            df[col] = df[col].map(lambda v: str(v).strip())
            df[f"__norm_{col}"] = df[col].map(self._normalize_text)

        return df

    def _load_google_sheets(self) -> pd.DataFrame:
        if not self.spreadsheet_id:
            raise ValueError("GOOGLE_SHEETS_SPREADSHEET_ID est vide.")

        gc = self._get_gspread_client()
        spreadsheet = gc.open_by_key(self.spreadsheet_id)
        worksheet = spreadsheet.worksheet(self.worksheet_name)
        rows = worksheet.get_all_records()
        df = pd.DataFrame(rows)
        return self._prepare_df(df)

    def _load_excel(self) -> pd.DataFrame:
        excel_path = Path(self.excel_file_path)
        if not excel_path.exists():
            raise FileNotFoundError(f"Fichier Excel introuvable : {excel_path}")

        df = pd.read_excel(str(excel_path), sheet_name=self.excel_sheet_name)
        return self._prepare_df(df)

    def load(self, force: bool = False) -> pd.DataFrame:
        if (
            not force
            and self._cached_df is not None
            and (time.time() - self._cached_at) < self.cache_seconds
        ):
            return self._cached_df

        if self.data_source == "google_sheets":
            self._cached_df = self._load_google_sheets()
        else:
            self._cached_df = self._load_excel()

        self._cached_at = time.time()
        return self._cached_df

    def refresh(self) -> None:
        self.load(force=True)

    def get_column_labels(self) -> dict[str, str]:
        self.load()
        return dict(self._column_labels)

    def find_user_by_ncine(self, ncine: str) -> dict[str, Any] | None:
        df = self.load()
        if "ncine" not in df.columns:
            raise ValueError("La colonne NCINE est introuvable dans la source de données.")

        ncine_norm = self._normalize_text(ncine)
        matches = df[df["__norm_ncine"] == ncine_norm]
        if matches.empty:
            return None

        public_cols = [col for col in df.columns if not col.startswith("__norm_")]
        return matches.iloc[0][public_cols].to_dict()

    def all_rows(self) -> list[dict[str, Any]]:
        df = self.load()
        public_cols = [col for col in df.columns if not col.startswith("__norm_")]
        return df[public_cols].to_dict(orient="records")

    def _parse_float(self, value: Any) -> float | None:
        text = str(value).strip()
        if not text:
            return None

        text = text.replace(" ", "").replace(",", ".")
        try:
            return float(text)
        except ValueError:
            return None

    def _to_float(self, value: Any) -> float:
        number = self._parse_float(value)
        return 0.0 if number is None else number

    def _is_missing(self, value: Any) -> bool:
        return self._normalize_text(value) == ""

    def _is_valid_cumul_abs(self, value: Any) -> bool:
        number = self._parse_float(value)
        return number is not None and number >= 0

    def top_absences(self, limit: int = 10) -> list[dict[str, Any]]:
        df = self.load()
        if "cumul_abs" not in df.columns:
            raise ValueError("La colonne CUMUL_ABS est introuvable dans la source de données.")

        public_cols = [col for col in df.columns if not col.startswith("__norm_")]
        work_df = df[public_cols].copy()

        work_df["__cumul_abs_num"] = work_df["cumul_abs"].map(self._to_float)
        work_df = work_df.sort_values(by="__cumul_abs_num", ascending=False, kind="stable")
        work_df = work_df[work_df["__cumul_abs_num"] > 0]

        if limit < 1:
            limit = 10

        work_df = work_df.head(limit)

        items: list[dict[str, Any]] = []
        for item in work_df.to_dict(orient="records"):
            abs_num = float(item.pop("__cumul_abs_num", 0.0))
            item["cumul_abs_num"] = int(abs_num) if abs_num.is_integer() else abs_num
            items.append(item)

        return items

    def anomalies(self, limit: int = 100) -> list[dict[str, Any]]:
        df = self.load()
        public_cols = [col for col in df.columns if not col.startswith("__norm_")]
        work_df = df[public_cols].copy()

        if work_df.empty:
            return []

        if "ncine" in work_df.columns:
            ncine_norm = work_df["ncine"].map(self._normalize_text)
            duplicate_ncine_mask = ncine_norm.ne("") & ncine_norm.duplicated(keep=False)
        else:
            duplicate_ncine_mask = pd.Series(False, index=work_df.index)

        items: list[dict[str, Any]] = []

        for idx, row in work_df.iterrows():
            reasons: list[str] = []

            if "service" in work_df.columns and self._is_missing(row["service"]):
                reasons.append("service manquant")

            if "nom_prenom" in work_df.columns and self._is_missing(row["nom_prenom"]):
                reasons.append("nom_prenom manquant")

            if "ncine" in work_df.columns and bool(duplicate_ncine_mask.loc[idx]):
                reasons.append("ncine dupliqué")

            if "cumul_abs" in work_df.columns and not self._is_valid_cumul_abs(row["cumul_abs"]):
                reasons.append("cumul_abs invalide")

            if reasons:
                item = {
                    "ligne": int(idx) + 2,
                    **row.to_dict(),
                    "anomalies": " | ".join(reasons),
                }
                items.append(item)

        if limit < 1:
            limit = 100

        return items[:limit]

    def metadata(self) -> dict[str, Any]:
        df = self.load()
        return {
            "data_source": "Google Sheets" if self.data_source == "google_sheets" else "Excel local",
            "sheet_name": self.worksheet_name if self.data_source == "google_sheets" else self.excel_sheet_name,
            "row_count": len(df),
        }