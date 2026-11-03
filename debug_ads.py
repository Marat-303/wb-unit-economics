from app.wb_api import WBAPIClient
from app.secure_token import load_token

def main():
    token = load_token()
    client = WBAPIClient(token)
    date_str = "2026-10-26"
    
    print(f"Запрашиваем рекламу за {date_str}...")
    campaigns = client.fetch_campaigns()
    campaign_ids = [c.get("id") for c in campaigns if c.get("id") and c.get("status") not in (7, 8)]
    
    stats = client.fetch_ads_stats(campaign_ids, date_str, date_str)
    
    total = 0
    for campaign in stats:
        for day in campaign.get("days", []):
            # Берем сумму из API
            sum_rub = float(day.get("sum") or 0)
            if sum_rub == 0 and "apps" in day:
                sum_rub = sum(float(app.get("sum") or 0) for app in day["apps"])
            
            if sum_rub > 0:
                print(f"Кампания {campaign.get('advertId')}: {sum_rub:.2f} руб.")
                total += sum_rub
                
    print(f"\nИТОГО по API за {date_str}: {total:.2f} руб.")
    print(f"В приложении: 1999 руб.")

if __name__ == "__main__":
    main()