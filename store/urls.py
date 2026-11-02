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
    path("reminders/", views.reminders, name="reminders"),
    path("reminders/<int:reminder_id>/delete/", views.delete_reminder, name="delete_reminder"),
    path("guides/", views.care_guides, name="guides"),
    path("guides/<slug:slug>/", views.care_guide_detail, name="guide_detail"),
    path("subscribe/", views.subscribe, name="subscribe"),
    path("products/<int:product_id>/review/", views.review_product, name="review"),
    path("manage/", views.admin_dashboard, name="admin_dashboard"),
    path("manage/sales/", views.sales_report, name="sales_report"),
    path("inbox/", views.inbox_view, name="inbox"),
    path("contact/", views.contact_view, name="contact"),
]
