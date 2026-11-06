import requests
import datetime
import time

class WBAdAPI:
    BASE_URL = "https://advert-api.wildberries.ru"
    STATS_URL = "https://statistics-api.wildberries.ru"

    def __init__(self, token):
        self.headers = {"Authorization": token}
        self.token = token

    def get_active_campaigns(self):
        url = f"{self.BASE_URL}/api/advert/v2/adverts"
        params = {"statuses": "9,11"}
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=10)
            if resp.status_code != 200:
                raise Exception(f"HTTP {resp.status_code}: {resp.text}")
            data = resp.json()
            active_camps = []
            adverts = data if isinstance(data, list) else data.get("adverts", [])
            for camp in adverts:
                if not isinstance(camp, dict): continue
                if "advert_list" in camp:
                    for sub_camp in camp["advert_list"]:
                        c_id = sub_camp.get("advertId") or sub_camp.get("id")
                        c_name = sub_camp.get("name") or sub_camp.get("campaign_name") or sub_camp.get("title")
                        if not c_name: c_name = f"Кампания {c_id}"
                        active_camps.append({"advertId": c_id, "name": c_name, "status": int(sub_camp.get("status", 9))})
                else:
                    c_id = camp.get("advertId") or camp.get("id")
                    if c_id is None: continue
                    c_name = camp.get("name") or camp.get("campaign_name") or camp.get("title")
                    if not c_name: c_name = f"Кампания {c_id}"
                    active_camps.append({"advertId": c_id, "name": c_name, "status": int(camp.get("status", 9))})
            return active_camps
        except Exception as e:
            raise Exception(f"Ошибка: {e}")

    def get_today_stats(self, campaign_ids: list) -> dict:
        today = datetime.date.today().strftime("%Y-%m-%d")
        ids_str = ",".join(str(i) for i in campaign_ids)
        url = f"{self.BASE_URL}/adv/v3/fullstats"
        params = {"beginDate": today, "endDate": today, "ids": ids_str}
        for attempt in range(3):
            try:
                resp = requests.get(url, headers=self.headers, params=params, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    result = {}
                    for camp in data:
                        camp_id = camp.get("advertId")
                        total_sum = sum(day.get("sum", 0) for day in camp.get("days", []))
                        result[camp_id] = total_sum
                    return result
                elif resp.status_code == 429:
                    time.sleep(60)
                else:
                    raise Exception(f"Ошибка API {resp.status_code}: {resp.text}")
            except Exception:
                time.sleep(5)
        return {}

    def pause_campaign(self, campaign_id: int) -> bool:
        url = f"{self.BASE_URL}/adv/v0/pause?id={campaign_id}"
        resp = requests.get(url, headers=self.headers, timeout=10)
        return resp.status_code in (200, 204)

    def start_campaign(self, campaign_id: int) -> bool:
        url = f"{self.BASE_URL}/adv/v0/start?id={campaign_id}"
        resp = requests.get(url, headers=self.headers, timeout=10)
        return resp.status_code in (200, 204)

    def get_campaign_products(self, advert_id: int) -> list[dict]:
        url = f"{self.BASE_URL}/api/advert/v2/adverts"
        params = {"statuses": "9,11"}
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=15)
            if resp.status_code != 200:
                raise Exception(f"HTTP {resp.status_code}: {resp.text}")
            data = resp.json()
            adverts = data if isinstance(data, list) else data.get("adverts", [])
            products = []
            for camp in adverts:
                if not isinstance(camp, dict): continue
                camp_id = camp.get("advertId") or camp.get("id")
                if camp_id != advert_id: continue
                nm_settings = camp.get("nm_settings") or []
                for nm in nm_settings:
                    if not isinstance(nm, dict): continue
                    nm_id = nm.get("nm_id") or nm.get("nmId")
                    if not nm_id: continue
                    bids_kopecks = nm.get("bids_kopecks") or {}
                    search_bid_kopecks = bids_kopecks.get("search") if isinstance(bids_kopecks, dict) else 0
                    if search_bid_kopecks is None: search_bid_kopecks = 0
                    bid_rub = float(search_bid_kopecks) / 100.0
                    products.append({"nm_id": int(nm_id), "current_bid_rub": round(bid_rub, 2)})
            return products
        except Exception as e:
            raise Exception(f"Ошибка получения товаров кампании: {e}")

    def get_campaign_stats(self, advert_id: int, nm_ids: list[int], days: int = 7) -> dict:
        """Считает ОБЩИЙ расход и ОБЩУЮ выручку по кампании за N дней."""
        end_date = datetime.date.today().strftime("%Y-%m-%d")
        start_date = (datetime.date.today() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
        
        total_spend = 0.0
        total_revenue = 0.0

        url_adv = f"{self.BASE_URL}/adv/v3/fullstats"
        params_adv = {"beginDate": start_date, "endDate": end_date, "ids": str(advert_id)}
        
        # 1. Расход и выручка из рекламного API
        for attempt in range(3):
            try:
                resp = requests.get(url_adv, headers=self.headers, params=params_adv, timeout=20)
                if resp.status_code == 429:
                    time.sleep(60)
                    continue
                if resp.status_code != 200:
                    break
                
                data = resp.json()
                for camp in data:
                    if camp.get("advertId") != advert_id: continue
                    for day in camp.get("days", []):
                        total_spend += float(day.get("sum", 0))
                        for nm_stat in day.get("nms", []):
                            total_revenue += float(nm_stat.get("sum_price", 0))
                break
            except Exception as e:
                print(f"Ошибка fullstats: {e}")
                time.sleep(5)

        # 2. Если рекламная выручка нулевая, берем выручку из заказов (по тем же артикулам)
        if total_revenue == 0:
            url_orders = f"{self.STATS_URL}/api/v1/supplier/orders"
            params_orders = {"dateFrom": f"{start_date}T00:00:00"}
            try:
                resp = requests.get(url_orders, headers=self.headers, params=params_orders, timeout=20)
                if resp.status_code == 200:
                    orders = resp.json()
                    if isinstance(orders, list):
                        for order in orders:
                            if order.get("isCancel", False): continue
                            nm_id = order.get("nmId")
                            if nm_id in nm_ids:
                                total_revenue += float(order.get("priceWithDisc", 0))
            except Exception as e:
                print(f"Ошибка orders: {e}")

        drr = 0.0
        if total_spend > 0 and total_revenue == 0:
            drr = 999.9
        elif total_revenue > 0:
            drr = (total_spend / total_revenue) * 100
        
        return {
            "total_spend": total_spend,
            "total_revenue": total_revenue,
            "drr": round(drr, 1) if drr != 999.9 else 999.9
        }

    def update_bid(self, advert_id: int, nm_id: int, new_bid_rub: float) -> bool:
        url = f"{self.BASE_URL}/api/advert/v1/bids"
        bid_kopecks = int(round(new_bid_rub * 100))
        payload = {"bids": [{"advert_id": advert_id, "nm_bids": [{"nm_id": nm_id, "bid_kopecks": bid_kopecks, "placement": "search"}]}]}
        try:
            resp = requests.patch(url, headers=self.headers, json=payload, timeout=15)
            return resp.status_code in (200, 204)
        except Exception:
            return False