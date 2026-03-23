from __future__ import annotations

import json
import os
from typing import Any

from google import genai


class AIService:
    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.model = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview").strip()
        self.enabled = bool(self.api_key)
        self._client = genai.Client(api_key=self.api_key) if self.enabled else None

    def rewrite_user_row(self, ncine: str, item: dict[str, Any]) -> str:
        if not self.enabled or not self._client:
            print("Gemini disabled or client not initialized")
            return "[FALLBACK] " + self._build_fallback_text(ncine, item)

        prompt = self._build_prompt(ncine, item)
        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            text = (response.text or "").strip()
            print("Gemini raw response:", repr(text))
            return text if text else self._build_fallback_text(ncine, item)
        except Exception as e:
            print("Gemini error:", repr(e))
            return self._build_fallback_text(ncine, item)

    def summarize_admin_results(self, summary_type: str, items: list[dict[str, Any]]) -> str:
        if not items:
            if summary_type == "top_absences":
                return "Aucune donnée significative à résumer pour les absences."
            if summary_type == "anomalies":
                return "Aucune anomalie à résumer."
            return "Aucune donnée à résumer."

        if not self.enabled or not self._client:
            return self._build_admin_fallback_summary(summary_type, items)

        prompt = self._build_admin_summary_prompt(summary_type, items)

        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            text = (response.text or "").strip()
            print("Gemini admin summary raw response:", repr(text))
            return text if text else self._build_admin_fallback_summary(summary_type, items)
        except Exception as e:
            print("Gemini admin summary error:", repr(e))
            return self._build_admin_fallback_summary(summary_type, items)

    def _build_prompt(self, ncine: str, item: dict[str, Any]) -> str:
        return (
            "Tu es un assistant interne de Transdev.\n"
            "Réponds toujours en français.\n"
            "Utilise uniquement les données fournies.\n"
            "N'invente aucune information.\n"
            "Ne réponds pas en Markdown.\n"
            "Rédige un message naturel, fluide, professionnel et un peu varié dans sa formulation.\n"
            "Tu peux reformuler librement d'un utilisateur à l'autre, tout en restant clair.\n"
            "Évite de commencer toujours par la même phrase.\n"
            "Si une information est absente, ignore-la simplement.\n\n"
            f"NCINE demandé : {ncine}\n"
            f"Données trouvées : {item}\n\n"
            "Rédige uniquement le message final à afficher à l'utilisateur."
        )

    def _build_admin_summary_prompt(self, summary_type: str, items: list[dict[str, Any]]) -> str:
        if summary_type == "top_absences":
            instruction = (
                "Tu analyses une liste des collaborateurs ayant le plus d'absences. "
                "Résume les constats principaux de façon claire, concise et professionnelle. "
                "Mentionne les niveaux d'absence les plus marquants, les services concernés si visibles, "
                "et les éventuelles notes importantes. "
                "Ne fais aucune recommandation non justifiée par les données."
            )
        elif summary_type == "anomalies":
            instruction = (
                "Tu analyses une liste d'anomalies détectées dans les données. "
                "Résume les principaux problèmes observés de façon claire, concise et professionnelle. "
                "Indique les types d'anomalies les plus fréquents, les lignes ou profils les plus sensibles si visibles, "
                "et ce qui mérite une vérification prioritaire. "
                "N'invente aucune information."
            )
        else:
            instruction = (
                "Tu analyses un jeu de données administratif. "
                "Rédige un résumé clair, professionnel et fidèle aux données."
            )

        data_json = json.dumps(items, ensure_ascii=False, indent=2)

        return (
            "Tu es un assistant interne de Transdev.\n"
            "Réponds toujours en français.\n"
            "Utilise uniquement les données fournies.\n"
            "N'invente aucune information.\n"
            "Ne réponds pas en Markdown.\n"
            "Le style doit être naturel, professionnel, synthétique et utile pour un administrateur.\n"
            "Fais un paragraphe court ou deux petits paragraphes maximum.\n\n"
            f"Type d'analyse : {summary_type}\n"
            f"Instruction : {instruction}\n\n"
            f"Données à analyser :\n{data_json}\n\n"
            "Rédige uniquement le résumé final."
        )

    def _build_fallback_text(self, ncine: str, item: dict[str, Any]) -> str:
        parts: list[str] = [f"J'ai trouvé vos informations pour le NCINE {ncine}."]

        name = item.get("nom_prenom") or item.get("nom")
        if name:
            parts.append(f"Le collaborateur concerné est {name}.")

        mle = item.get("mle")
        if mle:
            parts.append(f"Le matricule enregistré est {mle}.")

        service = item.get("service")
        if service:
            parts.append(f"Le service associé est {service}.")

        cumul_ca = item.get("cumul_ca")
        if cumul_ca:
            parts.append(f"Le cumul CA est {cumul_ca}.")

        cumul_hr = item.get("cumul_hr")
        if cumul_hr:
            parts.append(f"Le cumul HR est {cumul_hr}.")

        cumul_abs = item.get("cumul_abs")
        if cumul_abs:
            parts.append(f"Le cumul ABS est {cumul_abs}.")

        note = item.get("note")
        if note:
            parts.append(f"Note : {note}.")

        return " ".join(parts)

    def _build_admin_fallback_summary(self, summary_type: str, items: list[dict[str, Any]]) -> str:
        count = len(items)

        if summary_type == "top_absences":
            top = items[:3]
            details: list[str] = []
            for item in top:
                name = item.get("nom_prenom") or "Collaborateur non précisé"
                abs_value = item.get("cumul_abs_num") or item.get("cumul_abs") or "non précisé"
                service = item.get("service") or "service non précisé"
                note = item.get("note") or ""
                chunk = f"{name} (service {service}, absences {abs_value})"
                if note:
                    chunk += f", note : {note}"
                details.append(chunk)

            return (
                f"{count} enregistrement(s) figurent dans le classement des absences les plus élevées. "
                f"Les cas les plus marquants sont : {' ; '.join(details)}."
            )

        if summary_type == "anomalies":
            anomaly_types: dict[str, int] = {}
            for item in items:
                raw = str(item.get("anomalies", "")).strip()
                if not raw:
                    continue
                for part in raw.split("|"):
                    label = part.strip()
                    if label:
                        anomaly_types[label] = anomaly_types.get(label, 0) + 1

            if anomaly_types:
                ranked = sorted(anomaly_types.items(), key=lambda x: x[1], reverse=True)
                text = ", ".join(f"{label} ({qty})" for label, qty in ranked[:5])
                return (
                    f"{count} ligne(s) présentent une ou plusieurs anomalies. "
                    f"Les problèmes les plus fréquents sont : {text}."
                )

            return f"{count} ligne(s) présentent des anomalies nécessitant une vérification."

        return f"{count} élément(s) ont été analysés."