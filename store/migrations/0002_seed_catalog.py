from datetime import datetime, timezone

from django.db import migrations


def seed_catalog(apps, schema_editor):
    Category = apps.get_model("store", "Category")
    Product = apps.get_model("store", "Product")
    CareGuide = apps.get_model("store", "CareGuide")
    Coupon = apps.get_model("store", "Coupon")

    plants, _ = Category.objects.get_or_create(
        slug="plants",
        defaults={"name": "Plants", "description": "Happy indoor and outdoor plants."},
    )
    pots, _ = Category.objects.get_or_create(
        slug="pots",
        defaults={"name": "Pots", "description": "Planters and pots for your greenery."},
    )
    products = [
        ("Monstera Deliciosa", "The statement maker", "38.00", plants, 18, "BESTSELLER", "photo-1614594975525-e45190c55d0b", "Lush monstera plant with broad green leaves"),
        ("Olive Tree", "A little Mediterranean", "64.00", plants, 12, "NEW ARRIVAL", "photo-1470252649378-9c29740c9fa8", "Sunlit olive tree branches"),
        ("Sunday Morning", "Ceramic planter · handmade", "32.00", pots, 24, "", "photo-1485955900006-10f4d324d411", "Potted indoor plant in a warm-toned ceramic pot"),
        ("Bird of Paradise", "Bring the outside in", "52.00", plants, 9, "EASY CARE", "photo-1501004318641-b39e6451bec6", "Tropical bird of paradise plant"),
    ]
    for name, subtitle, price, category, stock, tag, image, alt_text in products:
        Product.objects.get_or_create(
            name=name,
            defaults={
                "subtitle": subtitle,
                "description": subtitle,
                "price": price,
                "category": category,
                "stock": stock,
                "tag": tag,
                "image_url": f"https://images.unsplash.com/{image}?auto=format&fit=crop&w=900&q=85",
                "alt_text": alt_text,
                "active": True,
            },
        )

    guides = [
        (
            "A gentle guide to watering houseplants",
            "Learn how to check the soil, choose a watering rhythm, and avoid overwatering.",
            "Check the top few centimetres of soil before watering. If they feel dry, water slowly until a little runs from the drainage holes, then empty the saucer. Plants need less water in cooler, darker months. A pot with drainage helps roots stay healthy.",
        ),
        (
            "Finding the right light for your plant",
            "A quick way to match your plant with a happy spot in your home.",
            "Bright, indirect light is a comfortable starting point for many houseplants. A spot near a window but away from harsh direct afternoon sun works well. Turn the pot every week or two so growth stays even. If leaves stretch toward a window, try a brighter spot.",
        ),
        (
            "Simple steps for a happy new plant",
            "Help a new plant settle in with a few easy first-week habits.",
            "Choose a spot with suitable light and give your new plant a little time to adjust. Check its soil before watering and make sure the pot drains freely. Keep it away from cold drafts and heating vents. When you are ready to repot, choose a pot only a little larger than the current one.",
        ),
    ]
    for title, summary, body in guides:
        CareGuide.objects.get_or_create(
            slug=title.lower().replace(" ", "-").replace("'", ""),
            defaults={"title": title, "summary": summary, "body": body, "published": True},
        )

    Coupon.objects.get_or_create(
        code="GREEN10",
        defaults={
            "discount_percent": 10,
            "minimum_order": "0.00",
            "starts_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "ends_at": datetime(2030, 12, 31, 23, 59, tzinfo=timezone.utc),
            "active": True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [("store", "0001_initial")]

    operations = [migrations.RunPython(seed_catalog, migrations.RunPython.noop)]
