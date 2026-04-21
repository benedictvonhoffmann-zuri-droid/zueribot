"""Water connector — lake temperatures + Badi status for Zürich."""

import xml.etree.ElementTree as ET

import requests

from backend.connectors.base import BaseConnector

from .manifest import manifest

STATIONS = ["tiefenbrunnen", "mythenquai"]

FREIBAEDER = [
    "Letten", "Oberer Letten", "Unterer Letten",
    "Mythenquai", "Tiefenbrunnen", "Enge",
    "Utoquai", "Wollishofen", "Allenmoos",
    "Heuried", "Letzigraben", "Seebach",
    "Schanzengraben", "Frauenbad", "Männerbad",
    "Au-Höngg",
]


class WaterConnector(BaseConnector):
    manifest = manifest

    def get_water_temps(self) -> dict:
        stations = []
        for station_key in STATIONS:
            try:
                resp = requests.get(
                    f"https://tecdottir.metaodi.ch/measurements/{station_key}",
                    params={"sort": "timestamp_cet desc", "limit": 1},
                    timeout=self.manifest.runtime.timeout_s,
                )
                resp.raise_for_status()
                data = resp.json()

                if not data.get("ok") or not data.get("result"):
                    stations.append({"name": station_key, "error": "No data"})
                    continue

                vals = data["result"][0].get("values", {})
                stations.append({
                    "name": "Tiefenbrunnen" if station_key == "tiefenbrunnen" else "Mythenquai",
                    "timestamp": vals.get("timestamp_cet", {}).get("value"),
                    "water_temp_c": vals.get("water_temperature", {}).get("value"),
                    "air_temp_c": vals.get("air_temperature", {}).get("value"),
                    "wind_speed_ms": vals.get("wind_speed_avg_10min", {}).get("value"),
                    "wind_direction_deg": vals.get("wind_direction", {}).get("value"),
                    "humidity_pct": vals.get("humidity", {}).get("value"),
                    "pressure_hpa": vals.get("barometric_pressure_qfe", {}).get("value"),
                    "precipitation_mm": vals.get("precipitation", {}).get("value"),
                    "water_level_m": vals.get("water_level", {}).get("value"),
                })
            except Exception as e:
                stations.append({"name": station_key, "error": str(e)})

        return self.ok({"stations": stations})

    def get_badi_info(self, badi_name: str = "") -> dict:
        try:
            resp = requests.get(
                "https://www.stadt-zuerich.ch/stzh/bathdatadownload",
                timeout=self.manifest.runtime.timeout_s,
                headers={"User-Agent": "ZuriBot/1.0"},
            )
            resp.raise_for_status()
            root = ET.fromstring(resp.content)

            all_badis = []
            all_names = []
            for bath in root.findall('.//bath'):
                title = bath.findtext("title", "")
                all_names.append(title)
                all_badis.append({
                    "name": title,
                    "water_temp": bath.findtext("temperatureWater", ""),
                    "status": bath.findtext("openClosedTextPlain", "").strip(),
                    "opening_hours": bath.findtext("openingHoursText", ""),
                    "modified": bath.findtext("dateModified", "").strip(),
                    "url": bath.findtext("urlPage", ""),
                })

            if badi_name:
                q = badi_name.lower().strip()
                for freibad in FREIBAEDER:
                    if q in freibad.lower() or freibad.lower() in q:
                        matches = [b for b in all_badis if freibad.lower() in b["name"].lower()]
                        if matches:
                            return self.ok(matches)
                        return self.ok([{
                            "name": freibad,
                            "water_temp": "",
                            "status": "Closed (seasonal — Freibäder are open May–September)",
                            "opening_hours": "Seasonal: typically May–September",
                            "modified": "",
                            "url": "",
                        }])

                matches = [b for b in all_badis if q in b["name"].lower()]
                if matches:
                    return self.ok(matches)

                # Not found: surface helpful metadata via err (legacy included data on error)
                envelope = self.err(f"No badi found for '{badi_name}'")
                envelope["data"] = {
                    "current_badis": all_names,
                    "seasonal_badis": FREIBAEDER,
                    "note": "Freibäder (outdoor pools) are seasonal (May–September). Currently only Hallenbäder (indoor pools) are available.",
                }
                return envelope

            return self.ok(all_badis)
        except Exception as e:
            return self.err(e)
