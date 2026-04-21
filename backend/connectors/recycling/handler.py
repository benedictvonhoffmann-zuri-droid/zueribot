"""Recycling/waste connector — ERZ Stadt Zürich schedules + collection points."""

import csv
import io
from datetime import datetime, timedelta

import requests

from backend.connectors.base import BaseConnector

from .manifest import manifest

BASE_URL = "https://data.stadt-zuerich.ch/dataset"


def _csv_url(waste_type: str, year: int) -> str:
    paths = {
        "kehricht": f"entsorgungskalender_kehricht/download/entsorgungskalender_kehricht_{year}.csv",
        "bioabfall": f"entsorgungskalender_bioabfall/download/entsorgungskalender_bioabfall_{year}.csv",
        "papier": f"entsorgungskalender_papier/download/papier_{year}.csv",
        "karton": f"entsorgungskalender_karton/download/karton_{year}.csv",
        "sammelstellen": f"entsorgungskalender_sammelstellen/download/entsorgungskalender_sammelstellen_{year}.csv",
        "mobiler_recyclinghof": f"entsorgungskalender_mobiler_recyclinghof/download/mobiler_recyclinghof_{year}.csv",
    }
    return f"{BASE_URL}/{paths[waste_type]}"


WASTE_TYPES = {"kehricht", "bioabfall", "papier", "karton", "sammelstellen", "mobiler_recyclinghof"}


def _format_date(date_str):
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return d.strftime("%d.%m.%Y")
    except Exception:
        return date_str


class RecyclingConnector(BaseConnector):
    manifest = manifest

    def _fetch_csv(self, url):
        resp = requests.get(
            url,
            timeout=self.manifest.runtime.timeout_s,
            headers={"User-Agent": "ZuriBot/1.0"},
        )
        resp.raise_for_status()
        text = resp.content.decode("utf-8-sig")
        return list(csv.DictReader(io.StringIO(text)))

    def _fetch_schedule_csv(self, waste_type: str):
        """Try current year, fall back to previous year (ERZ publishes annually)."""
        current = datetime.now().year
        last_err: Exception | None = None
        for year in (current, current - 1):
            try:
                return self._fetch_csv(_csv_url(waste_type, year))
            except requests.HTTPError as e:
                last_err = e
                if e.response is not None and e.response.status_code == 404:
                    continue
                raise
        if last_err:
            raise last_err
        return []

    def get_waste_schedule(self, zip_code: str = "", waste_type: str = "kehricht", upcoming_days: int = 30) -> dict:
        try:
            if waste_type not in WASTE_TYPES:
                return self.err(f"Unknown waste type: {waste_type}")

            rows = self._fetch_schedule_csv(waste_type)
            if not rows:
                return self.err("No data available")

            if zip_code:
                zip_str = str(zip_code)
                rows = [r for r in rows if str(r.get("PLZ", "")).startswith(zip_str)]

            today = datetime.now().date()
            end_date = today + timedelta(days=upcoming_days)

            schedule = []
            for row in rows:
                date_str = row.get("Abholdatum", "")
                try:
                    date = datetime.strptime(date_str, "%Y-%m-%d").date()
                except Exception:
                    continue

                if date < today or date > end_date:
                    continue

                entry = {
                    "date": date_str,
                    "date_formatted": _format_date(date_str),
                    "zip_code": row.get("PLZ", ""),
                }
                if "Station" in row:
                    entry["station"] = row.get("Station", "")
                schedule.append(entry)

            schedule.sort(key=lambda x: x["date"])

            seen = set()
            unique = []
            for s in schedule:
                key = (s["date"], s.get("zip_code", ""))
                if key not in seen:
                    seen.add(key)
                    unique.append(s)

            waste_names = {
                "kehricht": "Garbage (Kehricht)",
                "bioabfall": "Bio Waste (Bioabfall)",
                "papier": "Paper (Papier)",
                "karton": "Cardboard (Karton)",
            }

            return self.ok({
                "waste_type": waste_type,
                "waste_name": waste_names.get(waste_type, waste_type),
                "schedule": unique[:30],
                "total_upcoming": len(unique),
            })
        except Exception as e:
            return self.err(e)

    def get_collection_points(self, zip_code: str = "", material: str = "") -> dict:
        try:
            rows = self._fetch_schedule_csv("sammelstellen")
            if not rows:
                return self.err("No data available")

            points = []
            for row in rows:
                if zip_code:
                    zip_str = str(zip_code)
                    if not str(row.get("PLZ", "")).startswith(zip_str):
                        continue

                if material:
                    mat_key = material.lower()
                    if mat_key in ["glass", "glas"]:
                        if row.get("Glas", "").lower() != "x":
                            continue
                    elif mat_key in ["metal", "metall"]:
                        if row.get("Metall", "").lower() != "x":
                            continue
                    elif mat_key in ["oil", "oel", "öl"]:
                        if row.get("Oel", "").lower() != "x":
                            continue
                    elif mat_key in ["textiles", "textilien", "clothes"]:
                        if row.get("Textilien", "").lower() != "x":
                            continue

                point = {
                    "zip_code": row.get("PLZ", ""),
                    "station": row.get("Station", ""),
                    "materials": [],
                }
                if row.get("Glas", "").lower() == "x":
                    point["materials"].append("Glas")
                if row.get("Metall", "").lower() == "x":
                    point["materials"].append("Metall")
                if row.get("Oel", "").lower() == "x":
                    point["materials"].append("Öl")
                if row.get("Textilien", "").lower() == "x":
                    point["materials"].append("Textilien")

                points.append(point)

            return self.ok({
                "collection_points": points,
                "total": len(points),
            })
        except Exception as e:
            return self.err(e)

    def get_mobile_recycling(self, zip_code: str = "", upcoming_days: int = 60) -> dict:
        try:
            rows = self._fetch_schedule_csv("mobiler_recyclinghof")
            if not rows:
                return self.err("No data available")

            if zip_code:
                zip_str = str(zip_code)
                rows = [r for r in rows if str(r.get("PLZ", "")).startswith(zip_str)]

            today = datetime.now().date()
            end_date = today + timedelta(days=upcoming_days)

            centers = []
            for row in rows:
                date_str = row.get("Abholdatum", "")
                try:
                    date = datetime.strptime(date_str, "%Y-%m-%d").date()
                except Exception:
                    continue
                if date < today or date > end_date:
                    continue

                centers.append({
                    "date": date_str,
                    "date_formatted": _format_date(date_str),
                    "zip_code": row.get("PLZ", ""),
                    "station": row.get("Station", ""),
                })

            centers.sort(key=lambda x: x["date"])

            return self.ok({
                "mobile_recycling_centers": centers,
                "total_upcoming": len(centers),
            })
        except Exception as e:
            return self.err(e)

    def get_all_schedules(self, zip_code: str = "", upcoming_days: int = 14) -> dict:
        try:
            results = {}
            waste_types = ["kehricht", "bioabfall", "papier", "karton"]
            waste_names = {
                "kehricht": "Garbage (Kehricht)",
                "bioabfall": "Bio Waste (Bioabfall)",
                "papier": "Paper (Papier)",
                "karton": "Cardboard (Karton)",
            }

            for wt in waste_types:
                result = self.get_waste_schedule(zip_code=zip_code, waste_type=wt, upcoming_days=upcoming_days)
                if result["success"]:
                    results[wt] = {
                        "name": waste_names[wt],
                        "dates": [s["date_formatted"] for s in result["data"]["schedule"][:5]],
                    }
                else:
                    results[wt] = {"name": waste_names[wt], "dates": [], "error": result.get("error")}

            mobile = self.get_mobile_recycling(zip_code=zip_code, upcoming_days=upcoming_days)
            if mobile["success"]:
                results["mobiler_recyclinghof"] = {
                    "name": "Mobile Recycling Center",
                    "dates": [f"{m['date_formatted']} - {m['station']}" for m in mobile["data"]["mobile_recycling_centers"][:3]],
                }

            return self.ok(results)
        except Exception as e:
            return self.err(e)
