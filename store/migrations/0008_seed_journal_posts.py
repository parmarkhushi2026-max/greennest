from django.db import migrations
from django.utils import timezone


def seed_journal(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Product = apps.get_model("store", "Product")
    Category = apps.get_model("store", "Category")
    JournalTag = apps.get_model("store", "JournalTag")
    JournalPost = apps.get_model("store", "JournalPost")
    JournalComment = apps.get_model("store", "JournalComment")

    # Pick a staff user or first user for author
    author = User.objects.filter(is_staff=True).first() or User.objects.first()
    if not author:
        author = User.objects.create(
            username="green_editor",
            email="editor@greennest.local",
            is_staff=True,
            is_active=True,
        )

    # Tags
    tag_monstera, _ = JournalTag.objects.get_or_create(name="Monstera Care", slug="monstera-care")
    tag_styling, _ = JournalTag.objects.get_or_create(name="Plant Styling", slug="plant-styling")
    tag_air, _ = JournalTag.objects.get_or_create(name="Air Purifying", slug="air-purifying")
    tag_beginners, _ = JournalTag.objects.get_or_create(name="Beginner Tips", slug="beginner-tips")
    tag_pots, _ = JournalTag.objects.get_or_create(name="Pots & Repotting", slug="pots-repotting")

    # Products & Categories
    monstera_product = Product.objects.filter(name__icontains="Monstera").first()
    olive_product = Product.objects.filter(name__icontains="Olive").first()
    pot_product = Product.objects.filter(name__icontains="Sunday Morning").first()
    plants_cat = Category.objects.filter(name__icontains="Plant").first() or Category.objects.first()
    pots_cat = Category.objects.filter(name__icontains="Pot").first()

    now = timezone.now()

    # Post 1: Monstera Fenestrations
    p1, created1 = JournalPost.objects.get_or_create(
        slug="how-to-get-huge-split-leaves-on-monstera",
        defaults={
            "title": "How to Get Those Giant Fenestrated Split Leaves on Your Monstera",
            "excerpt": "Wondering why your Swiss Cheese Plant only produces solid heart-shaped leaves? Discover the 3 simple sunlight and moisture triggers that unlock glorious natural fenestrations.",
            "body": """Monstera Deliciosa is revered for its dramatic, split leaves. But for many indoor gardeners, new foliage stubbornly unfolds into flat, solid green hearts.

### Why Leaves Split (The Science of Fenestration)
In their native tropical rainforests of Southern Mexico, Monsteras climb upward on giant trees. As they scale toward the canopy, they develop natural splits and holes—called fenestrations—to allow hurricane winds to pass through without snapping the foliage and to let precious dappled sunlight reach lower leaves.

### 1. Give It Direct Morning Sunlight
The number one reason Monsteras fail to split indoors is simply inadequate lighting. While Monsteras tolerate medium shade, they only produce mature fenestrations when bathed in bright indirect light or 2-3 hours of gentle morning sun. Place your pot within 3-4 feet of an east-facing window.

### 2. Introduce a Coco-Coir Moss Pole
Monsteras are natural hemiepiphytes: their aerial roots seek a textured trunk to climb. When you secure the main vine against a sturdy moss pole, the plant senses physical stability and produces substantially larger leaves with secondary splits!

### 3. Maintain Balanced Moisture
Water thoroughly when the top two inches of soil feel completely dry to touch. Empty the drainage saucer after 15 minutes to keep delicate root tips airy and oxygenated.

Happy growing, and enjoy the glorious foliage unfurling in your sanctuary!""",
            "cover_image": "https://images.unsplash.com/photo-1614594975525-e45190c55d0b?auto=format&fit=crop&w=1200&q=85",
            "author": author,
            "status": "published",
            "published_at": now,
            "product": monstera_product,
            "category": plants_cat,
            "seo_title": "How to Get Split Leaves on Monstera Deliciosa · GreenNest Plant Journal",
            "seo_description": "Learn the 3 essential light, moisture, and climbing tips that trigger giant fenestrated leaves on your Monstera.",
        }
    )
    if created1:
        p1.tags.add(tag_monstera, tag_beginners, tag_styling)
        # Sample comment
        JournalComment.objects.create(
            post=p1,
            author=author,
            body="Adding a moss pole made an instant difference to my 2-year old Monstera! Highly recommend this guide.",
            is_approved=True,
        )

    # Post 2: Planter Pairing & Aesthetics
    p2, created2 = JournalPost.objects.get_or_create(
        slug="the-art-of-styling-plants-choosing-the-right-pot",
        defaults={
            "title": "The Art of Plant Styling: Pairing Foliage with Earthy Ceramic Pots",
            "excerpt": "From textured terracotta to glazed minimalist stoneware, here is our nursery stylist guide to making your indoor jungle look like an architectural magazine.",
            "body": """Plants are living sculptures. Yet so many indoor plant parents leave their gorgeous greenery trapped in plastic nursery containers. 

### Contrast Texture and Silhouette
When styling an indoor corner, think of harmony through contrast:
- **Broad architectural leaves** (like Fiddle Leaf Figs and Monsteras) pair best with warm, neutral ceramic planters with smooth matte glazes.
- **Cascading vines** (like String of Pearls or Pothos) look spectacular resting on high wooden plant stands in handcrafted terracotta.

### Drainage Is Non-Negotiable
Always ensure your decorative pot has an unobstructed drainage hole or keep the plant inside its lightweight inner pot that slips seamlessly into the ceramic decorative vessel. This makes watering day effortless!

### Rule of Odd Numbers
When grouping plants on a console table or windowsill, arrange them in clusters of three or five varying in height: one tall hero specimen, one mid-size bushy companion, and one low trailing variety.

Elevate your room's natural energy by treating each planter as an extension of your interior decor.""",
            "cover_image": "https://images.unsplash.com/photo-1485955900006-10f4d324d411?auto=format&fit=crop&w=1200&q=85",
            "author": author,
            "status": "published",
            "published_at": now,
            "product": pot_product,
            "category": pots_cat,
            "seo_title": "Pairing Foliage with Ceramic Pots · Plant Styling Journal",
            "seo_description": "Our nursery stylist guide to elevating your living spaces with ceramic pots, drainage tips, and silhouette pairing.",
        }
    )
    if created2:
        p2.tags.add(tag_styling, tag_pots, tag_beginners)

    # Post 3: Air-Purifying Plants & Healthy Homes
    p3, created3 = JournalPost.objects.get_or_create(
        slug="5-air-purifying-plants-for-healthier-sleep",
        defaults={
            "title": "5 NASA-Approved Air-Purifying Plants for Deep, Restful Sleep",
            "excerpt": "Breathe easier and wake up refreshed. Discover the plants that release oxygen at night and filter out common household volatile organic compounds.",
            "body": """Modern homes can trap airborne particles, benzene, and formaldehyde from paint, furniture, and cleaning products. Fortunately, houseplants are Mother Nature's premier bio-filters.

### What Makes Bedroom Plants Special?
Unlike typical plants that consume oxygen at night, select varieties—such as Snake Plants and Aloe Vera—perform Crassulacean Acid Metabolism (CAM). They open their stomata after dark to absorb carbon dioxide and release fresh, pure oxygen right while you sleep.

### Our Top Recommended Bedroom Greenery:
1. **Sansevieria (Snake Plant)**: Virtually indestructible. Low light, infrequent watering, and outstanding toxin filtering.
2. **Peace Lily (Spathiphyllum)**: Elevates room humidity by up to 5%, which soothes dry throats and sinuses during winter months.
3. **Spider Plant**: Removes airborne xylene and carbon monoxide safely around curious pets.

Place two medium specimens on your bedside table or floating shelf to create a clean, peaceful bedtime retreat!""",
            "cover_image": "https://images.unsplash.com/photo-1501004318641-b39e6451bec6?auto=format&fit=crop&w=1200&q=85",
            "author": author,
            "status": "published",
            "published_at": now,
            "product": olive_product,
            "category": plants_cat,
            "seo_title": "Best Air-Purifying Plants for Better Sleep · GreenNest",
            "seo_description": "Discover 5 NASA-backed indoor plants that release oxygen at night for cleaner air and restorative sleep.",
        }
    )
    if created3:
        p3.tags.add(tag_air, tag_beginners)


def remove_journal(apps, schema_editor):
    JournalPost = apps.get_model("store", "JournalPost")
    JournalPost.objects.filter(slug__in=[
        "how-to-get-huge-split-leaves-on-monstera",
        "the-art-of-styling-plants-choosing-the-right-pot",
        "5-air-purifying-plants-for-healthier-sleep"
    ]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("store", "0007_journaltag_journalpost_journalcomment_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_journal, reverse_code=remove_journal),
    ]

