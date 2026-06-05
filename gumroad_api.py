# gumroad_api.py - Integración con API de Gumroad
import requests
import os
from typing import Dict, List, Optional
from pathlib import Path

class GumroadAPI:
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://api.gumroad.com/v2"
        self.headers = {"Authorization": f"Bearer {token}"}
        self.last_error = None

    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict:
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(method, url, headers=self.headers, data=data, params=params, timeout=15)
            response.raise_for_status()
            result = response.json()
            if not result.get("success"):
                self.last_error = result.get("message", "Error desconocido de Gumroad")
                return {"success": False, "error": self.last_error}
            self.last_error = None
            return result
        except requests.exceptions.HTTPError as e:
            self.last_error = f"HTTP Error {e.response.status_code}: {e.response.text}"
            return {"success": False, "error": self.last_error}
        except Exception as e:
            self.last_error = str(e)
            return {"success": False, "error": self.last_error}

    def create_product(self, name: str, description: str, price_usd: float, content_text: str = "", published: bool = True) -> Dict:
        """Crear producto en Gumroad con contenido opcional."""
        price_cents = int(price_usd * 100)
        custom_permalink = name.lower().replace(" ", "-").replace("/", "-").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
        
        data = {
            "name": name,
            "description": description,
            "price": str(price_cents),
            "published": str(published).lower(),
            "custom_permalink": custom_permalink
        }
        
        # Si hay contenido de texto, agrégalo
        if content_text:
            data["content"] = content_text

        result = self._request("POST", "/products", data=data)
        
        if result.get("success"):
            product = result.get("product", {})
            return {
                "success": True,
                "product_id": product.get("id"),
                "url": f"https://gumroad.com/l/{product.get('custom_permalink', product.get('id'))}",
                "name": product.get("name"),
                "price": f"${price_usd:.2f}",
                "message": f"✅ Producto '{name}' creado y publicado"
            }
        return result

    def list_products(self) -> List[Dict]:
        result = self._request("GET", "/products")
        if result.get("success"):
            return result.get("products", [])
        return []

    def get_sales(self, limit: int = 20) -> List[Dict]:
        result = self._request("GET", "/sales", params={"limit": str(limit)})
        if result.get("success"):
            return result.get("sales", [])
        return []

    def get_stats(self) -> Dict:
        products = self.list_products()
        sales = self.get_sales(limit=50)
        total_sales = len(sales)
        total_revenue = sum(float(s.get("price", 0)) for s in sales)
        active_products = len([p for p in products if p.get("published")])
        
        return {
            "success": True,
            "total_products": len(products),
            "active_products": active_products,
            "total_sales": total_sales,
            "total_revenue": f"${total_revenue:.2f}",
            "recent_sales": sales[:5]
        }