import json
import os
from pathlib import Path
import requests
from typing import Optional

_DEMO_FILE = Path(__file__).resolve().parent.parent.parent / 'demo' / 'lusha_responses.json'
_DEMO_DATA: dict | None = None


def _load_demo_data() -> dict:
    global _DEMO_DATA
    if _DEMO_DATA is None:
        with open(_DEMO_FILE) as f:
            _DEMO_DATA = json.load(f)
    return _DEMO_DATA


class LushaClient:
    """
    Client for the LUSHA contact enrichment API.
    Finds email, phone, and LinkedIn URL for a named person at a company.

    Expected response shape from LUSHA:
    {
      "data": {
        "emails": [{"email": "john@corp.com"}],
        "phones": [{"number": "+1234567890"}],
        "linkedin_url": "https://linkedin.com/in/john"
      }
    }
    """

    BASE_URL = "https://api.lusha.com/v2"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("LUSHA_API_KEY", "")
        self.session = requests.Session()
        self.session.headers.update({
            "api_key": self.api_key,
            "Content-Type": "application/json",
        })

    def find_contact(
        self,
        first_name: str,
        last_name: str,
        company_name: str,
    ) -> dict:
        """
        Enrich a contact by name + company.
        Returns dict with keys: email, phone, linkedin_url, raw.
        Returns empty dict keys (None values) on failure.
        """
        empty = {"email": None, "phone": None, "linkedin_url": None, "raw": {}}
        if not first_name or not company_name:
            return empty

        if not self.api_key:
            demo = _load_demo_data()
            key = f"{first_name} {last_name}|{company_name}".lower()
            data = demo.get(key, {})
            if data:
                emails = data.get("emails", [])
                phones = data.get("phones", [])
                return {
                    "email": emails[0]["email"] if emails else None,
                    "phone": phones[0]["number"] if phones else None,
                    "linkedin_url": data.get("linkedin_url"),
                    "raw": data,
                }
            return empty

        try:
            response = self.session.get(
                f"{self.BASE_URL}/person",
                params={
                    "firstName": first_name,
                    "lastName": last_name,
                    "company": company_name,
                },
                timeout=15,
            )
            response.raise_for_status()
            data = response.json().get("data", {})
            emails = data.get("emails", [])
            phones = data.get("phones", [])
            return {
                "email": emails[0]["email"] if emails else None,
                "phone": phones[0]["number"] if phones else None,
                "linkedin_url": data.get("linkedin_url"),
                "raw": data,
            }
        except requests.RequestException as exc:
            print(f"[LushaClient] API error: {exc}")
            return empty
