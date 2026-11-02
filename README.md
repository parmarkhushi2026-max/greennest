# GreenNest – Plant Nursery Store

GreenNest is a Django plant-nursery storefront with public plant browsing and care guides, customer accounts and shopping, and a staff-only management area.

## Run locally

From the project directory on Windows:

```powershell
python manage.py migrate
python manage.py runserver
```

The storefront is at `http://127.0.0.1:8000/`. Sample plants, categories, care guides, and the `GREEN10` coupon are added by the initial store data migration.

Create a staff administrator when needed:

```powershell
python manage.py createsuperuser
```

Sign in at `/admin/` for full category, product and stock, coupon, order and delivery-status, review-moderation, guide, reminder, and subscriber management. `/manage/` is the staff dashboard; `/manage/sales/` reports revenue from delivered orders.

## Store modules

- **Visitors:** browse/search/filter active in-stock products and read published care guides.
- **Customers:** register/sign in, manage a session shopping bag, apply coupons, check out with cash on delivery or select online payment, track their own orders, save care reminders, subscribe to plant notes, and submit reviews for moderation.
- **Admin/staff:** manage categories, products and stock, coupons, orders and delivery status, guides, reviews, reminders, and subscribers; review delivered-order sales reports.

## Payment and reminder setup

Online checkout is intentionally a demo placeholder: it creates an order with payment marked pending and does not collect card details or charge a customer. Integrate and configure a payment provider before enabling real online payments.

Care reminders are saved per customer. Run `python manage.py send_care_reminders` on a schedule to send due reminders. Development uses Django's console email backend, so messages are printed in the command output. Configure a real Django email backend before scheduling production delivery.
