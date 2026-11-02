from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import CareGuide, CareReminder, Category, Coupon, NewsletterSubscriber, Order, Product, Review


class StorefrontTests(TestCase):
    def setUp(self):
        self.category = Category.objects.get(slug="plants")
        self.product = Product.objects.get(name="Monstera Deliciosa")
        self.product.stock = 5
        self.product.save(update_fields=["stock"])
        self.user = User.objects.create_user(
            username="plantfan",
            email="plantfan@example.com",
            password="SecureTestPass!234",
            first_name="Plant",
        )

    def test_visitors_can_browse_catalog_and_care_guides(self):
        home = self.client.get(reverse("store:home"))
        guides = self.client.get(reverse("store:guides"))
        self.assertEqual(home.status_code, 200)
        self.assertContains(home, "Monstera Deliciosa")
        self.assertContains(home, "Plants")
        self.assertEqual(guides.status_code, 200)
        self.assertContains(guides, "watering houseplants")
        guide = CareGuide.objects.filter(published=True).first()
        self.assertEqual(
            self.client.get(reverse("store:guide_detail", args=[guide.slug])).status_code,
            200,
        )
        self.assertEqual(self.client.get(reverse("store:product_detail", args=[self.product.pk])).status_code, 200)

    def test_customer_can_register(self):
        response = self.client.post(reverse("store:register"), {
            "first_name": "New",
            "username": "newcustomer",
            "email": "new@example.com",
            "password1": "StrongPass!234",
            "password2": "StrongPass!234",
        })
        self.assertRedirects(response, reverse("store:home"))
        self.assertTrue(User.objects.filter(username="newcustomer").exists())

    def test_coupon_cart_online_order_and_tracking(self):
        self.client.force_login(self.user)
        self.client.post(reverse("store:add_to_cart", args=[self.product.pk]), {"next": "/"})
        coupon = Coupon.objects.get(code="GREEN10")
        self.assertTrue(coupon.is_valid_for(Decimal("38.00")))
        self.client.post(reverse("store:cart"), {"action": "apply_coupon", "code": "GREEN10"})
        cart_page = self.client.get(reverse("store:cart"))
        self.assertContains(cart_page, "GREEN10")
        response = self.client.post(reverse("store:checkout"), {
            "customer_name": "Plant Fan",
            "phone": "555-0101",
            "address": "12 Green Street",
            "payment_method": "online",
        })
        order = Order.objects.get(user=self.user)
        self.assertRedirects(response, reverse("store:order_detail", args=[order.tracking_code]))
        self.assertEqual(order.payment_method, Order.PaymentMethod.ONLINE)
        self.assertEqual(order.payment_status, Order.PaymentStatus.PENDING)
        self.assertEqual(order.total, Decimal("34.20"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 4)
        self.assertEqual(self.client.get(reverse("store:orders")).status_code, 200)
        self.assertContains(self.client.get(reverse("store:order_detail", args=[order.tracking_code])), order.tracking_code)

    def test_customer_can_save_reminder_and_submit_review(self):
        self.client.force_login(self.user)
        reminder_response = self.client.post(reverse("store:reminders"), {
            "plant_name": "",
            "product": self.product.pk,
            "interval_days": 7,
            "next_reminder": (date.today() + timedelta(days=7)).isoformat(),
        })
        self.assertRedirects(reminder_response, reverse("store:reminders"))
        self.assertTrue(CareReminder.objects.filter(user=self.user, plant_name=self.product.name).exists())
        review_response = self.client.post(reverse("store:review", args=[self.product.pk]), {
            "rating": 5,
            "comment": "Beautiful and healthy plant.",
        })
        self.assertRedirects(review_response, reverse("store:home"))
        self.assertTrue(Review.objects.filter(user=self.user, product=self.product, approved=False).exists())

    def test_newsletter_subscription_is_persisted(self):
        response = self.client.post(reverse("store:subscribe"), {
            "email": "green@example.com",
            "next": "/",
        })
        self.assertRedirects(response, "/")
        self.assertTrue(NewsletterSubscriber.objects.filter(email="green@example.com", active=True).exists())

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_due_care_reminders_send_email_and_reschedule(self):
        reminder = CareReminder.objects.create(
            user=self.user,
            product=self.product,
            plant_name=self.product.name,
            interval_days=7,
            next_reminder=date.today(),
        )
        call_command("send_care_reminders", stdout=None)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.product.name, mail.outbox[0].subject)
        reminder.refresh_from_db()
        self.assertGreater(reminder.next_reminder, date.today())

    def test_staff_can_open_management_and_sales_reports(self):
        staff = User.objects.create_user(
            username="nurseryadmin",
            password="SecureTestPass!234",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(staff)
        self.assertEqual(self.client.get(reverse("store:admin_dashboard")).status_code, 200)
        self.assertEqual(self.client.get(reverse("store:sales_report")).status_code, 200)
        self.assertEqual(self.client.get("/admin/store/product/").status_code, 200)

    def test_checkout_and_orders_require_customer_login(self):
        response = self.client.get(reverse("store:orders"))
        self.assertRedirects(response, f"{reverse('store:login')}?next={reverse('store:orders')}")
