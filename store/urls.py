from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

app_name = "store"

urlpatterns = [
    path("", views.home, name="home"),
    path("shop/", views.shop, name="shop"),
    path("category/<slug:category_slug>/", views.shop, name="category_page"),
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("products/<int:product_id>/", views.product_detail, name="product_detail"),
    path("cart/", views.cart, name="cart"),
    path("cart/apply-coupon/", views.quick_apply_coupon, name="quick_apply_coupon"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("checkout/", views.checkout, name="checkout"),
    path("orders/", views.orders, name="orders"),
    path("orders/<str:tracking_code>/", views.order_detail, name="order_detail"),
    path("orders/<str:tracking_code>/email-receipt/", views.order_email_receipt_view, name="order_email_receipt"),
    path("account/", views.customer_dashboard, name="customer_dashboard"),
    path("account/bookmarks/", views.customer_bookmarks, name="customer_bookmarks"),
    path("reminders/", views.reminders, name="reminders"),
    path("reminders/<int:reminder_id>/delete/", views.delete_reminder, name="delete_reminder"),
    path("guides/", views.care_guides, name="guides"),
    path("guides/<slug:slug>/", views.care_guide_detail, name="guide_detail"),
    path("subscribe/", views.subscribe, name="subscribe"),
    path("products/<int:product_id>/review/", views.review_product, name="review"),
    path("manage/", views.admin_dashboard, name="admin_dashboard"),
    path("dashboard/", views.admin_dashboard, name="dashboard_alias"),
    path("manage/sales/", views.sales_report, name="sales_report"),
    path("inbox/", views.inbox_view, name="inbox"),
    path("contact/", views.contact_view, name="contact"),

    # Plant Journal Public & Customer Routes
    path("journal/", views.journal_list, name="journal_list"),
    path("journal/<slug:slug>/", views.journal_detail, name="journal_detail"),
    path("journal/<slug:slug>/comment/", views.journal_add_comment, name="journal_add_comment"),
    path("journal/<slug:slug>/bookmark/", views.journal_toggle_bookmark, name="journal_toggle_bookmark"),

    # Plant Journal Staff Management Routes
    path("manage/journal/", views.manage_journal, name="manage_journal"),
    path("manage/journal/create/", views.manage_journal_create, name="manage_journal_create"),
    path("manage/journal/<int:post_id>/edit/", views.manage_journal_edit, name="manage_journal_edit"),
    path("manage/journal/<int:post_id>/toggle-publish/", views.manage_journal_toggle_publish, name="manage_journal_toggle_publish"),
    path("manage/journal/comments/<int:comment_id>/moderate/", views.manage_journal_comment_moderate, name="manage_journal_comment_moderate"),
]
