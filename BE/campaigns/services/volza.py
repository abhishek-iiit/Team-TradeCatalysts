import os
import requests
from typing import Optional


class VölzaClient:
    """
    Client for the Volza trade data API.
    Searches for companies that import a given product.

    Expected response shape from Volza (adapt if actual API differs):
    {
      "results": [
        {
          "company_name": "Acme Chemicals",
          "country": "IN",
          "website": "https://acme.com",
          "contact_name": "Rajesh Kumar",
          "contact_designation": "Purchase Manager",
          "contact_email": "rajesh@acme.com",
          "num_transactions": 24,
          "purchase_history": [...],
          "pricing_trend": {...}
        }
      ]
    }
    """

    BASE_URL = "https://api.volza.com/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("VOLZA_API_KEY", "")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })

    def search_importers(
        self,
        product_name: str,
        hsn_code: str = "",
        countries: list = None,
        min_transactions: int = 0,
    ) -> list[dict]:
        """
        Search Volza for companies that import the given product.
        Returns a list of importer dicts. Returns [] on any error.
        """
        params = {
            "product_name": product_name,
            "hsn_code": hsn_code,
            "min_transactions": min_transactions,
        }
        if countries:
            params["countries"] = ",".join(countries)

        try:
            response = self.session.get(
                f"{self.BASE_URL}/importers/search",
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            return response.json().get("results", [])
        except requests.RequestException as exc:
            print(f"[VölzaClient] API error: {exc}")
            return []
