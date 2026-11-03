from decimal import Decimal
from django.db.models import Count, Q
from store.models import Category, Product


def shopping_bag(request):
    cart = request.session.get("cart", {})
    count = sum(int(quantity) for quantity in cart.values())
    subtotal = Decimal("0.00")
    if cart:
        for product in Product.objects.filter(pk__in=cart.keys(), active=True):
            subtotal += product.price * int(cart.get(str(product.pk), 0))

    categories = Category.objects.annotate(
        product_count=Count("products", filter=Q(products__active=True, products__stock__gt=0))
    ).order_by("name")

    total_active_plants = Product.objects.filter(active=True, stock__gt=0).count()

    return {
        "cart_item_count": count,
        "cart_subtotal": subtotal,
        "nav_categories": categories,
        "total_active_plants": total_active_plants,
    }

# Alias for compatibility with cart_context
cart_context = shopping_bag
