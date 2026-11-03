from django.contrib import admin
from .models import (
    CareGuide,
    CareReminder,
    Category,
    Coupon,
    JournalBookmark,
    JournalComment,
    JournalPost,
    JournalTag,
    NewsletterSubscriber,
    Order,
    OrderItem,
    Product,
    Review,
)

# Custom Green Nest Nursery Admin Header
admin.site.site_header = "Green Nest Nursery · Admin Portal"
admin.site.site_title = "Green Nest Admin"
admin.site.index_title = "Store Management & Nursery Operations"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "product_count"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ["name"]}

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = "Products"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "price", "stock", "tag", "active", "created_at"]
    list_filter = ["category", "active", "tag"]
    search_fields = ["name", "subtitle", "description"]
    list_editable = ["price", "stock", "active"]
    list_per_page = 20


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ["code", "discount_percent", "minimum_order", "starts_at", "ends_at", "active"]
    list_filter = ["active"]
    search_fields = ["code"]
    list_editable = ["active", "discount_percent"]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["product", "product_name", "unit_price", "quantity", "line_total"]
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["tracking_code", "customer_name", "user", "status", "payment_method", "payment_status", "total", "created_at"]
    list_filter = ["status", "payment_method", "payment_status", "created_at"]
    search_fields = ["tracking_code", "customer_name", "phone", "user__username", "user__email"]
    readonly_fields = ["tracking_code", "user", "subtotal", "discount", "total", "created_at"]
    list_editable = ["status", "payment_status"]
    inlines = [OrderItemInline]
    list_per_page = 25


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["product", "user", "rating", "approved", "created_at"]
    list_filter = ["approved", "rating"]
    list_editable = ["approved"]
    search_fields = ["product__name", "user__username", "comment"]


@admin.register(CareGuide)
class CareGuideAdmin(admin.ModelAdmin):
    list_display = ["title", "slug", "published", "created_at"]
    list_filter = ["published"]
    search_fields = ["title", "summary", "body"]
    prepopulated_fields = {"slug": ["title"]}


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ["email", "subscribed_at"]
    search_fields = ["email"]
    readonly_fields = ["subscribed_at"]


@admin.register(CareReminder)
class CareReminderAdmin(admin.ModelAdmin):
    list_display = ["plant_name", "user", "product", "interval_days", "next_reminder", "active"]
    list_filter = ["interval_days", "active"]
    search_fields = ["plant_name", "user__username", "user__email"]


class JournalCommentInline(admin.TabularInline):
    model = JournalComment
    extra = 0
    fields = ["author", "body", "is_approved", "created_at"]
    readonly_fields = ["author", "created_at"]


@admin.register(JournalTag)
class JournalTagAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "posts_count"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ["name"]}

    def posts_count(self, obj):
        return obj.posts.count()
    posts_count.short_description = "Articles"


@admin.register(JournalPost)
class JournalPostAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "status", "published_at", "category", "product", "comments_count", "created_at"]
    list_filter = ["status", "category", "created_at", "tags"]
    search_fields = ["title", "excerpt", "body", "author__username"]
    prepopulated_fields = {"slug": ["title"]}
    list_editable = ["status"]
    filter_horizontal = ["tags"]
    inlines = [JournalCommentInline]
    date_hierarchy = "published_at"

    def comments_count(self, obj):
        return obj.comments.count()
    comments_count.short_description = "Comments"


@admin.register(JournalComment)
class JournalCommentAdmin(admin.ModelAdmin):
    list_display = ["post", "author", "is_approved", "created_at"]
    list_filter = ["is_approved", "created_at"]
    list_editable = ["is_approved"]
    search_fields = ["post__title", "author__username", "body"]


@admin.register(JournalBookmark)
class JournalBookmarkAdmin(admin.ModelAdmin):
    list_display = ["user", "post", "created_at"]
    search_fields = ["user__username", "post__title"]
    list_filter = ["created_at"]
