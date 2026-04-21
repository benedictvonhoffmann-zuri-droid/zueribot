"""Transit connector — transport.opendata.ch (SBB)."""

import re

import requests

from backend.connectors.base import BaseConnector

from .manifest import manifest


class TransitConnector(BaseConnector):
    manifest = manifest

    def get_departures(self, station: str = "Zürich HB", limit: int = 5) -> dict:
        try:
            resp = requests.get(
                "https://transport.opendata.ch/v1/stationboard",
                params={"station": station, "limit": limit},
                timeout=self.manifest.runtime.timeout_s,
            )
            resp.raise_for_status()
            data = resp.json()

            station_info = data.get("station", {})
            stationboard = data.get("stationboard", [])

            if not stationboard:
                return self.err(f"No departures found for '{station}'")

            departures = []
            for entry in stationboard:
                stop = entry.get("stop", {})
                departures.append({
                    "line": f"{entry.get('category', '')}{entry.get('number', '')}",
                    "to": entry.get("to", ""),
                    "departure": stop.get("departure", ""),
                    "departure_platform": stop.get("platform", ""),
                    "delay_min": stop.get("delay", 0) or 0,
                })

            return self.ok({
                "station": station_info.get("name", station),
                "departures": departures,
            })
        except Exception as e:
            return self.err(e)

    def get_connections(self, from_station: str, to_station: str, limit: int = 3, via: str | None = None) -> dict:
        try:
            params = {"from": from_station, "to": to_station, "limit": min(limit, 6)}
            if via:
                params["via[]"] = via
            resp = requests.get(
                "https://transport.opendata.ch/v1/connections",
                params=params,
                timeout=self.manifest.runtime.timeout_s,
            )
            resp.raise_for_status()
            data = resp.json()

            connections = data.get("connections", [])
            if not connections:
                return self.err(f"No connections found from '{from_station}' to '{to_station}'")

            result = []
            for conn in connections:
                dep = conn.get("from", {})
                arr = conn.get("to", {})

                duration_raw = conn.get("duration", "")
                dur_match = re.match(r'(\d+)d(\d+):(\d+):(\d+)', duration_raw) if duration_raw else None
                if dur_match:
                    d, h, m = int(dur_match.group(1)), int(dur_match.group(2)), int(dur_match.group(3))
                    if d > 0:
                        duration = f"{d}d {h}h {m}min"
                    elif h > 0:
                        duration = f"{h}h {m}min"
                    else:
                        duration = f"{m}min"
                else:
                    duration = duration_raw

                sections = []
                for sec in conn.get("sections", []):
                    journey = sec.get("journey")
                    walk = sec.get("walk")
                    sec_dep = sec.get("departure", {})
                    sec_arr = sec.get("arrival", {})

                    if journey:
                        sections.append({
                            "type": "transit",
                            "line": f"{journey.get('category', '')}{journey.get('number', '')}",
                            "to": journey.get("to", ""),
                            "departure_station": sec_dep.get("station", {}).get("name", ""),
                            "departure_time": sec_dep.get("departure", ""),
                            "arrival_station": sec_arr.get("station", {}).get("name", ""),
                            "arrival_time": sec_arr.get("arrival", ""),
                        })
                    elif walk:
                        walk_dur = walk.get("duration")
                        duration_min = walk_dur // 60 if isinstance(walk_dur, int) else 0
                        sections.append({
                            "type": "walk",
                            "from": sec_dep.get("station", {}).get("name", ""),
                            "to": sec_arr.get("station", {}).get("name", ""),
                            "duration_min": duration_min,
                        })

                result.append({
                    "departure_time": dep.get("departure", ""),
                    "departure_platform": dep.get("platform", ""),
                    "departure_delay_min": dep.get("delay", 0) or 0,
                    "arrival_time": arr.get("arrival", ""),
                    "arrival_platform": arr.get("platform", ""),
                    "duration": duration,
                    "transfers": conn.get("transfers", 0),
                    "sections": sections,
                })

            return self.ok({
                "from": data.get("from", {}).get("name", from_station),
                "to": data.get("to", {}).get("name", to_station),
                "connections": result,
            })
        except Exception as e:
            return self.err(e)
