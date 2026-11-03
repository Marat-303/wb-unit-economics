import time
from typing import Any

import requests


WB_COMMON = "https://common-api.wildberries.ru"
WB_STATISTICS = "https://statistics-api.wildberries.ru"
WB_ADVERT = "https://advert-api.wildberries.ru"
WB_CONTENT = "https://content-api.wildberries.ru"
WB_FINANCE = "https://finance-api.wildberries.ru"


class WBAPIError(Exception):
    """Ошибка при запросе к WB API."""
    pass


class WBAPIClient:
    def __init__(self, token: str):
        if not token:
            raise ValueError("Токен WB API не задан")
        self.token = token.strip()
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": self.token,
            "Content-Type": "application/json",
        })

    def _get(self, base: str, path: str, params: dict[str, Any] | None = None, max_retries: int = 3) -> Any:
        url = f"{base}{path}"
        delay = 60.0
        
        for attempt in range(max_retries):
            resp = self.session.get(url, params=params, timeout=60)
            
            if resp.status_code == 429:
                if attempt < max_retries - 1:
                    print(f"[Лимит WB 429] Ожидание {delay:.0f} сек. перед повтором...")
                    time.sleep(delay)
                    delay *= 1.5
                    continue
                    
            return self._handle(resp)

    def _post(self, base: str, path: str, payload: dict[str, Any]) -> Any:
        url = f"{base}{path}"
        resp = self.session.post(url, json=payload, timeout=60)
        return self._handle(resp)

    def _handle(self, resp: requests.Response) -> Any:
        if resp.status_code == 401:
            raise WBAPIError("401: токен отсутствует, истёк или повреждён")
        if resp.status_code == 403:
            raise WBAPIError("403: у токена недостаточно прав (проверьте категории)")
        if resp.status_code == 404:
            raise WBAPIError(f"404: метод не найден. Проверьте URL. Ответ: {resp.text[:200]}")
        if resp.status_code == 429:
            raise WBAPIError("429: превышен лимит запросов. Пожалуйста, подождите минуту.")
        if not resp.ok:
            raise WBAPIError(f"{resp.status_code}: {resp.text[:500]}")
        
        if not resp.text.strip():
            return []
            
        return resp.json()

    def ping(self) -> dict:
        return self._get(WB_COMMON, "/ping")

    def fetch_sales(self, date_from: str, date_to: str) -> list[dict]:
        data = self._get(
            WB_STATISTICS,
            "/api/v1/supplier/sales",
            params={"dateFrom": date_from, "dateTo": date_to, "flag": 0},
        )
        if not isinstance(data, list):
            raise WBAPIError(f"Неожиданный формат ответа продаж: {type(data)}")
        return data

    def fetch_financial_report(self, date_from: str, date_to: str) -> list[dict]:
        """
        Возвращает финансовый отчёт о реализации (логистика, хранение, штрафы).
        Использует актуальный метод POST /api/finance/v1/sales-reports/detailed.
        """
        all_rows: list[dict] = []
        rrd_id = 0
        
        while True:
            payload = {
                "dateFrom": date_from,
                "dateTo": date_to,
                "limit": 100000,
                "rrdId": rrd_id,
                "period": "daily",
            }
            data = self._post(WB_FINANCE, "/api/finance/v1/sales-reports/detailed", payload)
            
            if not isinstance(data, list) or not data:
                break
            
            all_rows.extend(data)
            rrd_id = data[-1].get("rrdId", 0)
            
            if len(data) < 100000 or not rrd_id:
                break
                
        return all_rows

    def fetch_campaigns(self) -> list[dict]:
        data = self._get(WB_ADVERT, "/api/advert/v2/adverts")
        campaigns: list[dict] = []

        def _collect(obj: dict):
            cid = obj.get("advertId") or obj.get("id")
            if cid:
                campaigns.append({
                    "id": cid,
                    "status": obj.get("status"),
                })
                return
            for value in obj.values():
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            _collect(item)
                elif isinstance(value, dict):
                    _collect(value)

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    _collect(item)
        elif isinstance(data, dict):
            _collect(data)

        return campaigns

    def fetch_ads_stats(self, campaign_ids: list[int], date_from: str, date_to: str) -> list[dict]:
        if not campaign_ids:
            return []
        ids_param = ",".join(str(i) for i in campaign_ids)
        data = self._get(
            WB_ADVERT,
            "/adv/v3/fullstats",
            params={"ids": ids_param, "beginDate": date_from, "endDate": date_to},
        )
        return data if isinstance(data, list) else []

    def fetch_cards(self) -> list[dict]:
        all_cards: list[dict] = []
        cursor: dict[str, Any] = {"limit": 100}
        while True:
            payload = {
                "settings": {
                    "cursor": cursor,
                    "filter": {"withPhoto": -1},
                }
            }
            data = self._post(WB_CONTENT, "/content/v2/get/cards/list", payload)
            cards = data.get("cards", []) if isinstance(data, dict) else []
            all_cards.extend(cards)
            cur = data.get("cursor", {}) if isinstance(data, dict) else {}
            if len(cards) < 100 or not cur.get("nmID"):
                break
            cursor = {
                "limit": 100,
                "updatedAt": cur.get("updatedAt"),
                "nmID": cur.get("nmID"),
            }
        return all_cards