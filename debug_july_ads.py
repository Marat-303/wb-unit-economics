from app.wb_api import WBAPIClient
from app.secure_token import load_token

def main():
    token = load_token()
    if not token:
        print("Нет токена")
        return

    client = WBAPIClient(token)
    date_from = "2026-07-01"
    date_to = "2026-07-31"
    
    print(f"Запрашиваем статистику рекламы за июль ({date_from} - {date_to})...")
    
    # Запрашиваем ВООБЩЕ ВСЕ кампании (без фильтра по статусу)
    campaigns = client.fetch_campaigns()
    # Берем ID вообще всех кампаний
    all_ids = [c.get("id") for c in campaigns if c.get("id")]
    
    print(f"Всего найдено кампаний в кабинете (включая архивные): {len(all_ids)}")
    
    if not all_ids:
        print("Кампаний не найдено.")
        return

    # Запрашиваем статистику по всем ID
    stats = client.fetch_ads_stats(all_ids, date_from, date_to)
    
    total_sum = 0
    print("\n--- ЗАТРАТЫ ПО КАМПАНИЯМ ЗА ИЮЛЬ ---")
    
    for campaign in stats:
        campaign_id = campaign.get("advertId")
        campaign_sum = 0
        
        for day in campaign.get("days", []):
            sum_rub = float(day.get("sum") or 0)
            if sum_rub == 0 and "apps" in day:
                sum_rub = sum(float(app.get("sum") or 0) for app in day["apps"])
            
            campaign_sum += sum_rub
            
        if campaign_sum > 0:
            print(f"Кампания ID {campaign_id}: {campaign_sum:.2f} руб.")
            total_sum += campaign_sum
            
    print("-" * 40)
    print(f"ИТОГО расходов на рекламу за июль по API: {total_sum:.2f} руб.")
    print(f"Сравните эту цифру с тем, что написано у вас в приложении.")

if __name__ == "__main__":
    main()