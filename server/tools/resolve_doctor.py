from langchain.tools import tool
from typing import Optional, Dict
from difflib import SequenceMatcher
from typing import Optional, Dict


DOCTORS = [
    {
        "doctor_id": "a64f99c5-5d02-44de-865d-7190ed370b1a",
        "name": "Dr. Omar Khalil",
        "specialty": "General Medicine",
        "calendar_id": "cal_omar_general"
    },
    {
        "doctor_id": "df2d94a3-8815-4b9d-a72c-3fd6b2ad8916",
        "name": "Dr. Ahmad Saleh",
        "specialty": "Cardiology",
        "calendar_id": "cal_ahmad_cardio"
    },
    {
        "doctor_id": "e3c9c19f-c3c9-4f6e-8cad-50e82e038c7e",
        "name": "Dr. Lina Hassan",
        "specialty": "Dermatology",
        "calendar_id": "cal_lina_derma"
    }
]

SPECIALTY_SYNONYMS = {
    "cardiology": [
        "heart",
        "heart doctor",
        "chest pain",
        "cardio",
        "ahmad"
    ],
    "general medicine": [
        "general",
        "general doctor",
        "family doctor",
        "checkup",
        "regular doctor",
        "gp",
        "omar"
    ],
    "dermatology": [
        "skin",
        "skin doctor",
        "rash",
        "acne",
        "eczema",
        "lina"
    ]
}



def normalize(text: str) -> str:
    return text.lower().strip()

def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

@tool
def resolve_doctor(reference: str) -> Optional[Dict]:
    """
    Resolves a doctor's name or specialty into a doctor record.

    Use this when the user mentions:
    - A doctor's name (e.g., Dr. Ahmad)
    - A specialty (e.g., heart doctor, dermatologist)

    Returns:
        doctor_id, name, specialty, calendar_id
    """
    ref = normalize(reference)

    # 1️⃣ Direct name match
    for doctor in DOCTORS:
        if ref in normalize(doctor["name"]):
            return doctor

    # 2️⃣ Synonym-based specialty resolution
    for specialty, keywords in SPECIALTY_SYNONYMS.items():
        for keyword in keywords:
            if keyword in ref:
                for doctor in DOCTORS:
                    if normalize(doctor["specialty"]) == specialty:
                        return doctor

    # 3️⃣ Direct specialty match
    for doctor in DOCTORS:
        if ref in normalize(doctor["specialty"]):
            return doctor

    # 4️⃣ Fuzzy fallback (last resort)
    best_match = None
    best_score = 0.0

    for doctor in DOCTORS:
        score = max(
            SequenceMatcher(None, ref, normalize(doctor["name"])).ratio(),
            SequenceMatcher(None, ref, normalize(doctor["specialty"])).ratio()
        )
        if score > best_score:
            best_score = score
            best_match = doctor

    if best_score >= 0.65:
       return {
        "doctor_id": best_match["doctor_id"],
        "name": best_match["name"],
        "specialty": best_match["specialty"],
        "calendar_id": best_match["calendar_id"]
    }

    return None

