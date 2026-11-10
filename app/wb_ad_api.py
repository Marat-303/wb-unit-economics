import requests
import datetime
import time
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class WBAdAPI:
    BASE_URL = "https://advert-api.wildberries.ru"

    def __init__(self, token):
        self.headers = {"Authorization": token}
        self.token = token

    def get_active_campaigns(self):
        url = f"{self.BASE_URL}/api/advert/v2/adverts"
        params = {"statuses": "9,11"}
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=10, verify=False)
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
                resp = requests.get(url, headers=self.headers, params=params, timeout=15, verify=False)
                if resp.status_code == 200:
                    data = resp.json()
                    result = {}
                    for camp in data:
                        camp_id = camp.get("advertId")
                        days = camp.get("days", [])
                        if days: # Если есть данные за сегодня
                            total_sum = sum(day.get("sum", 0) for day in days)
                            result[camp_id] = total_sum
                    return result
                elif resp.status_code == 429:
                    time.sleep(60) # Если блок, ждем минуту
                else:
                    raise Exception(f"Ошибка API {resp.status_code}: {resp.text}")
            except Exception:
                time.sleep(5)
        return {}

    def pause_campaign(self, campaign_id: int) -> bool:
        url = f"{self.BASE_URL}/adv/v0/pause?id={campaign_id}"
        resp = requests.get(url, headers=self.headers, timeout=10, verify=False)
        return resp.status_code in (200, 204)

    def start_campaign(self, campaign_id: int) -> bool:
        url = f"{self.BASE_URL}/adv/v0/start?id={campaign_id}"
        resp = requests.get(url, headers=self.headers, timeout=10, verify=False)
        return resp.status_code in (200, 204)

    def get_campaign_products(self, advert_id: int) -> list[dict]:
        url = f"{self.BASE_URL}/api/advert/v2/adverts"
        params = {"statuses": "9,11"}
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=15, verify=False)
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

    def get_product_positions(self, advert_id: int, nm_ids: list[int]) -> dict[int, float]:
        """Пытается извлечь среднюю позицию из boosterStats за 7 дней."""
        end_date = datetime.date.today().strftime("%Y-%m-%d")
        start_date = (datetime.date.today() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        
        url = f"{self.BASE_URL}/adv/v3/fullstats"
        params = {"beginDate": start_date, "endDate": end_date, "ids": str(advert_id)}
        
        for attempt in range(3):
            try:
                resp = requests.get(url, headers=self.headers, params=params, timeout=20, verify=False)
                if resp.status_code == 429:
                    time.sleep(60)
                    continue
                if resp.status_code != 200:
                    return {}
                
                data = resp.json()
                result = {}
                for camp in data:
                    if camp.get("advertId") != advert_id:
                        continue
                    
                    booster = camp.get("boosterStats")
                    if booster:
                        for item in booster:
                            nm = item.get("nm")
                            avg_pos = item.get("avg_position")
                            if nm and avg_pos is not None:
                                result[int(nm)] = float(avg_pos)
                    
                    if not result:
                        for day in camp.get("days", []):
                            day_booster = day.get("boosterStats")
                            if day_booster:
                                for item in day_booster:
                                    nm = item.get("nm")
                                    avg_pos = item.get("avg_position")
                                    if nm and avg_pos is not None:
                                        result[int(nm)] = float(avg_pos)
                return result
            except Exception:
                time.sleep(5)
        return {}

    def update_bid(self, advert_id: int, nm_id: int, new_bid_rub: float) -> bool:
        url = f"{self.BASE_URL}/api/advert/v1/bids"
        bid_kopecks = int(round(new_bid_rub * 100))
        payload = {"bids": [{"advert_id": advert_id, "nm_bids": [{"nm_id": nm_id, "bid_kopecks": bid_kopecks, "placement": "search"}]}]}
        try:
            resp = requests.patch(url, headers=self.headers, json=payload, timeout=15, verify=False)
            return resp.status_code in (200, 204)
        except Exception:
            return False