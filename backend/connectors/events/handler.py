"""Events connector — Eventfrog."""

import os
from datetime import datetime

import requests

from backend.connectors.base import BaseConnector

from .manifest import manifest

EVENTFROG_API = "https://api.eventfrog.net/public/v1/events"

RUBRIC_MAP = {
    1: "Single-Party", 2: "Sonstige Veranstaltungen", 3: "Speed-Dating",
    4: "Ausfahrt", 5: "Ausflug", 6: "Brauchtum", 7: "Familie",
    8: "Fest", 9: "Führungen", 10: "Gottesdienst",
    11: "Kurs / Seminar", 12: "Lesung", 13: "Messe / Ausstellung",
    14: "Musik - Klassik", 15: "Musik - Rock/Pop", 16: "Musik - Jazz/Blues/Folk",
    17: "Musik - Schlager/Volksmusik", 18: "Musik - Weltmusik", 19: "Musik - Sonstiges",
    20: "Sport - Anlass", 21: "Sport - Aktiv", 22: "Theater / Tanz",
    23: "Vortrag / Diskussion", 24: "Film", 25: "Party",
    26: "Konzert", 27: "Festival", 28: "Comedy",
    29: "Musical / Show", 30: "Oper", 31: "Kabarett",
    32: "Ausstellung", 33: "Museum", 34: "Workshop",
    35: "Networking", 36: "Kinder", 37: "Senioren",
}


class EventsConnector(BaseConnector):
    manifest = manifest

    def _headers(self) -> dict:
        key = os.environ.get("EVENTFROG_KEY")
        if not key:
            raise RuntimeError("EVENTFROG_KEY env var not set")
        return {"Authorization": f"Bearer {key}", "Accept": "application/json"}

    def get_events(self, query: str = "", category: str = "", limit: int = 10) -> dict:
        try:
            params = {
                "country": "CH",
                "limit": min(limit * 3, 50),
            }
            if query:
                params["q"] = query

            resp = requests.get(
                EVENTFROG_API,
                params=params,
                headers=self._headers(),
                timeout=self.manifest.runtime.timeout_s,
            )
            resp.raise_for_status()
            data = resp.json()

            events = []
            for event in data.get("events", []):
                location_alias = event.get("locationAlias", {}).get("de") or ""
                title = event.get("title", {}).get("de") or ""
                loc_ids = event.get("locationIds", [])

                begin = event.get("begin", "")
                end = event.get("end", "")

                try:
                    begin_fmt = datetime.strptime(begin[:19], "%Y-%m-%dT%H:%M:%S").strftime("%d.%m.%Y %H:%M") if begin else ""
                except Exception:
                    begin_fmt = begin

                try:
                    end_fmt = datetime.strptime(end[:19], "%Y-%m-%dT%H:%M:%S").strftime("%d.%m.%Y %H:%M") if end else ""
                except Exception:
                    end_fmt = end

                rubric_id = event.get("rubricId")
                category_name = RUBRIC_MAP.get(rubric_id, "Sonstige")

                events.append({
                    "id": event.get("id", ""),
                    "title": title,
                    "begin": begin,
                    "begin_formatted": begin_fmt,
                    "end": end,
                    "end_formatted": end_fmt,
                    "category": category_name,
                    "rubric_id": rubric_id,
                    "url": event.get("url", ""),
                    "organizer": event.get("organizerName", ""),
                    "location_ids": loc_ids,
                    "location_alias": location_alias,
                    "short_description": event.get("shortDescription", {}).get("de", ""),
                    "cancelled": event.get("cancelled", False),
                    "sold_out": event.get("soldOut"),
                    "image_url": (event.get("emblemToShow") or {}).get("url", ""),
                })

            if category:
                cat_lower = category.lower()
                events = [e for e in events if cat_lower in e["category"].lower()]

            now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            events = [e for e in events if e.get("begin", "") >= now]

            events = events[:limit]

            return self.ok({
                "events": events,
                "total_available": data.get("totalNumberOfResources", 0),
            })
        except Exception as e:
            return self.err(e)
