"""
Zürich City Services Connector
- General city information and services
- Emergency numbers, city offices, opening hours
"""

# ── Emergency Numbers ──────────────────────────────────────────
EMERGENCY_NUMBERS = {
    "polizei": {"number": "117", "name": "Polizei (Notruf)", "emoji": "🚔"},
    "sanität": {"number": "144", "name": "Sanität / Rettungsdienst", "emoji": "🚑"},
    "feuerwehr": {"number": "118", "name": "Feuerwehr", "emoji": "🚒"},
    "toxisch": {"number": "145", "name": "Tox Info Schweiz (Vergiftungsnotruf)", "emoji": "☠️"},
    "psychiatrie": {"number": "044 388 28 28", "name": "Psychiatrische Notdienst Zürich", "emoji": "🧠"},
    "frauenhaus": {"number": "044 271 59 59", "name": "Frauenhaus Zürich", "emoji": "🆘"},
    "dargebotene_hand": {"number": "143", "name": "Die Dargebotene Hand", "emoji": "📞"},
    "kinderjugend": {"number": "147", "name": "Pro Juventute (Kinder/Jugend)", "emoji": "👶"},
}

# ── City Offices ──────────────────────────────────────────────
CITY_OFFICES = {
    "stadthaus": {
        "name": "Stadthaus",
        "address": "Stadthausquai 17, 8001 Zürich",
        "hours": "Mo-Fr 08:00-12:00, 13:00-16:00",
        "phone": "044 412 12 12",
        "services": ["Anmeldung", "Abmeldung", "Wohnsitzbestätigung", "Steuern"],
        "emoji": "🏛️",
    },
    "einwohnerkontrolle": {
        "name": "Einwohnerkontrolle",
        "address": "Stadthausquai 17, 8001 Zürich",
        "hours": "Mo-Fr 08:00-12:00, 13:00-16:00",
        "phone": "044 412 41 11",
        "services": ["Anmeldung", "Abmeldung", "Wohnsitzbestätigung", "Identitätskarte"],
        "emoji": "📋",
    },
    "zivilstandsamt": {
        "name": "Zivilstandsamt",
        "address": "Stadthausquai 17, 8001 Zürich",
        "hours": "Mo-Fr 08:00-12:00, 13:00-16:00",
        "phone": "044 412 33 33",
        "services": ["Heirat", "Partnerschaft", "Geburt", "Tod"],
        "emoji": "💍",
    },
    "baudepartement": {
        "name": "Baudepartement",
        "address": "Beckenhofstrasse 22, 8006 Zürich",
        "hours": "Mo-Fr 08:30-12:00, 13:30-16:30",
        "phone": "044 412 55 55",
        "services": ["Baugesuch", "Bauberatung", "Denkmalschutz"],
        "emoji": "🏗️",
    },
    "sozialamt": {
        "name": "Sozialamt",
        "address": "Kasernenstrasse 29, 8004 Zürich",
        "hours": "Mo-Fr 08:30-12:00, 13:30-16:30",
        "phone": "044 412 31 11",
        "services": ["Sozialhilfe", "Notunterkunft", "Beratung"],
        "emoji": "🤝",
    },
    "arbeitsamt": {
        "name": "Arbeitsamt (RAV)",
        "address": "Kasernenstrasse 29, 8004 Zürich",
        "hours": "Mo-Fr 08:00-12:00, 13:30-17:00",
        "phone": "044 412 31 11",
        "services": ["Arbeitslosmeldung", "Stellensuche", "Beratung"],
        "emoji": "💼",
    },
    "gesundheitsamt": {
        "name": "Gesundheitsamt (UGZ)",
        "address": "Walchestrasse 31, 8006 Zürich",
        "hours": "Mo-Fr 08:00-12:00, 13:30-17:00",
        "phone": "044 412 23 23",
        "services": ["Gesundheitsberatung", "Impfung", "Lebensmittelkontrolle"],
        "emoji": "🏥",
    },
    "polizeidirektion": {
        "name": "Polizeidirektion",
        "address": "Kasernenstrasse 29, 8004 Zürich",
        "hours": "24h erreichbar",
        "phone": "044 412 11 11",
        "services": ["Strafanzeige", "Fundbüro", "Pass/ID"],
        "emoji": "🚔",
    },
}

# ── Common Services ────────────────────────────────────────────
COMMON_SERVICES = {
    "anmeldung": {
        "name": "Anmeldung (Wohnsitznahme)",
        "office": "Einwohnerkontrolle",
        "hours": "Mo-Fr 08:00-12:00, 13:00-16:00",
        "info": "Innerhalb von 14 Tagen nach Zuzug anmelden. Ausweis und Mietvertrag mitnehmen.",
        "emoji": "📝",
    },
    "abmeldung": {
        "name": "Abmeldung (Wohnsitzaufgabe)",
        "office": "Einwohnerkontrolle",
        "hours": "Mo-Fr 08:00-12:00, 13:00-16:00",
        "info": "Mindestens 14 Tage vor Wegzug abmelden. Abmeldebestätigung für neue Gemeinde.",
        "emoji": "📤",
    },
    "identitätskarte": {
        "name": "Identitätskarte / Pass",
        "office": "Einwohnerkontrolle",
        "hours": "Mo-Fr 08:00-12:00, 13:00-16:00",
        "info": "Termin online buchen empfohlen. Ausweis und aktuelles Foto mitnehmen.",
        "emoji": "🪪",
    },
    "steuern": {
        "name": "Steuererklärung",
        "office": "Stadthaus / Steuerverwaltung",
        "hours": "Mo-Fr 08:00-12:00, 13:00-16:00",
        "info": "Steuererklärung jährlich bis 31. März einreichen. Online über Steueramt ZH möglich.",
        "emoji": "💰",
    },
    "baugesuch": {
        "name": "Baugesuch",
        "office": "Baudepartement",
        "hours": "Mo-Fr 08:30-12:00, 13:30-16:30",
        "info": "Baugesuch online einreichen. Vorabklärung empfohlen.",
        "emoji": "🏠",
    },
    "hunderegistrierung": {
        "name": "Hunderegistrierung",
        "office": "Veterinärdienst",
        "hours": "Mo-Fr 08:00-12:00, 13:30-16:00",
        "info": "Hunde innerhalb von 10 Tagen nach Erwerb registrieren. Impfpass und Chipnummer mitnehmen.",
        "emoji": "🐕",
    },
}


def get_emergency_numbers(category=None):
    """Get emergency numbers, optionally filtered by category."""
    if category:
        cat_lower = category.lower()
        filtered = {k: v for k, v in EMERGENCY_NUMBERS.items() if cat_lower in k or cat_lower in v["name"].lower()}
        if not filtered:
            return f"Kei Notruf gfunde für '{category}'."
    else:
        filtered = EMERGENCY_NUMBERS
    
    lines = [
        "🆘 Notruf-Nummere Stadt Züri",
        "   🏛️ Quelle: Stadt Züri (✅ Offiziell)",
        ""
    ]
    for key, info in filtered.items():
        lines.append(f"  {info['emoji']} {info['name']}")
        lines.append(f"     📞 {info['number']}")
        lines.append("")
    return "\n".join(lines)


def get_city_office(office_name=None):
    """Get city office information, optionally filtered by name."""
    if office_name:
        off_lower = office_name.lower()
        # Search by key or name
        for key, office in CITY_OFFICES.items():
            if off_lower in key or off_lower in office["name"].lower():
                lines = [
                    f"{office['emoji']} {office['name']}",
                    "   🏛️ Quelle: Stadt Züri (✅ Offiziell)",
                    ""
                ]
                lines.append(f"  📍 {office['address']}")
                lines.append(f"  🕐 {office['hours']}")
                lines.append(f"  📞 {office['phone']}")
                lines.append(f"  Services: {', '.join(office['services'])}")
                return "\n".join(lines)
        return f"Keis Amt gfunde für '{office_name}'."
    
    # Return all offices
    lines = [
        "🏛️ Stadt Züri Ämter",
        "   🏛️ Quelle: Stadt Züri (✅ Offiziell)",
        ""
    ]
    for key, office in CITY_OFFICES.items():
        lines.append(f"  {office['emoji']} {office['name']}")
        lines.append(f"     📍 {office['address']}")
        lines.append(f"     🕐 {office['hours']}")
        lines.append(f"     📞 {office['phone']}")
        lines.append("")
    return "\n".join(lines)


def get_service_info(service_name=None):
    """Get information about common city services."""
    if service_name:
        svc_lower = service_name.lower()
        for key, service in COMMON_SERVICES.items():
            if svc_lower in key or svc_lower in service["name"].lower():
                lines = [
                    f"{service['emoji']} {service['name']}",
                    "   🏛️ Quelle: Stadt Züri (✅ Offiziell)",
                    ""
                ]
                lines.append(f"  Amt: {service['office']}")
                lines.append(f"  🕐 {service['hours']}")
                lines.append(f"  ℹ️ {service['info']}")
                return "\n".join(lines)
        return f"Kei Service gfunde für '{service_name}'."
    
    # Return all services
    lines = [
        "📋 Stadt Züri Services",
        "   🏛️ Quelle: Stadt Züri (✅ Offiziell)",
        ""
    ]
    for key, service in COMMON_SERVICES.items():
        lines.append(f"  {service['emoji']} {service['name']}")
        lines.append(f"     Amt: {service['office']} | 🕐 {service['hours']}")
        lines.append("")
    return "\n".join(lines)