"""Parking connector — ParkenDD feed for Zürich."""

import requests

from backend.connectors.base import BaseConnector

from .manifest import manifest


class ParkingConnector(BaseConnector):
    manifest = manifest

    def get_parking(self, name_filter: str | None = None) -> dict:
        try:
            resp = requests.get(
                "https://api.parkendd.de/Zuerich",
                timeout=self.manifest.runtime.timeout_s,
            )
            resp.raise_for_status()
            data = resp.json()

            lots = data.get("lots", [])
            if name_filter:
                nf = name_filter.lower()
                lots = [
                    l for l in lots
                    if nf in l.get("name", "").lower()
                    or nf in l.get("address", "").lower()
                ]

            if not lots:
                suffix = f" for {name_filter}" if name_filter else ""
                return self.err(f"No parking found{suffix}")

            parking_lots = []
            for lot in lots:
                free = lot.get("free")
                total = lot.get("total")
                state = lot.get("state", "unknown")

                occupancy_pct = None
                if (
                    isinstance(free, int)
                    and isinstance(total, int)
                    and total > 0
                    and state == "open"
                ):
                    occupancy_pct = round((1 - free / total) * 100)

                parking_lots.append({
                    "name": lot.get("name", ""),
                    "address": lot.get("address", ""),
                    "lot_type": lot.get("lot_type", ""),
                    "state": state,
                    "free": free,
                    "total": total,
                    "occupancy_pct": occupancy_pct,
                    "coords": lot.get("coords"),
                })

            return self.ok({
                "lots": parking_lots,
                "last_updated": data.get("last_updated", ""),
            })
        except Exception as e:
            return self.err(e)
