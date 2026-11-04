from django.http import JsonResponse
from .email_utils import send_order_receipt_email
import json
from django.conf import settings
import secrets
from decimal import Decimal, ROUND_HALF_UP

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.http import require_POST

from .forms import CareReminderForm, CheckoutForm, CouponForm, LoginForm, RegisterForm, ReviewForm, JournalCommentForm, JournalPostForm
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import (
    CareGuide,
    CareReminder,
    Category,
    ContactInquiry,
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


def _cart(request):
    return request.session.get("cart", {})


def _cart_summary(request):
    cart = _cart(request)
    products = Product.objects.filter(pk__in=cart, active=True).select_related("category")
    lines = []
    subtotal = Decimal("0.00")
    for product in products:
        quantity = max(0, int(cart.get(str(product.pk), 0)))
        if not quantity:
            continue
        line_total = product.price * quantity
        subtotal += line_total
        lines.append({"product": product, "quantity": quantity, "line_total": line_total})

    coupon = None
    discount = Decimal("0.00")
    code = request.session.get("coupon_code")
    if code:
        coupon = Coupon.objects.filter(code=code, active=True).first()
        now = timezone.now()
        if coupon and coupon.starts_at <= now <= coupon.ends_at:
            if subtotal >= coupon.minimum_order:
                discount = (subtotal * coupon.discount_percent / 100).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
        else:
            coupon = None
            request.session.pop("coupon_code", None)
    return lines, subtotal, coupon, discount, subtotal - discount


def home(request):
    query = (request.GET.get("q") or request.GET.get("s", "")).strip()
    category_slug = (request.GET.get("category") or request.GET.get("product_cat", "")).strip()
    if category_slug.lower() in ["all", "all-categories"]:
        category_slug = ""
    products = Product.objects.filter(active=True, stock__gt=0).select_related("category")
    if query:
        products = products.filter(name__icontains=query) | products.filter(subtitle__icontains=query) | products.filter(category__name__icontains=query)
    if category_slug:
        products = products.filter(category__slug=category_slug)
    else:
        from django.db.models import Case, When
        featured_ids = [28, 41, 45, 61, 1, 4, 9, 29]
        priority = Case(*[When(id=pid, then=pos) for pos, pid in enumerate(featured_ids)], default=99)
        products = products.order_by(priority, "name")
    products = products.annotate(
        review_count=Count("reviews", filter=Q(reviews__approved=True)),
        average_rating=Avg("reviews__rating", filter=Q(reviews__approved=True)),
    )
    return render(request, "store/home.html", {
        "products": products.distinct()[:8],
        "categories": Category.objects.annotate(product_count=Count("products")).order_by("name"),
        "query": query,
        "category_slug": category_slug,
        "guides": CareGuide.objects.filter(published=True)[:4],
    })


def shop(request, category_slug=None):
    query = (request.GET.get("q") or request.GET.get("s", "")).strip()
    category_slug = (category_slug or request.GET.get("category") or request.GET.get("product_cat", "")).strip()
    sort = request.GET.get("sort", "featured").strip()
    price_range = request.GET.get("price", "").strip()
    tag = request.GET.get("tag", "").strip()
    is_offer = request.GET.get("offer", "").strip().lower() in ("true", "1", "yes")

    if category_slug.lower() in ["all", "all-categories"]:
        category_slug = ""

    products = Product.objects.filter(active=True, stock__gt=0).select_related("category")
    if is_offer:
        products = products.filter(
            Q(tag__icontains="Bestseller") |
            Q(tag__icontains="Popular") |
            Q(tag__icontains="Trending") |
            Q(tag__icontains="NASA") |
            Q(price__lte=500)
        )

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(subtitle__icontains=query) |
            Q(category__name__icontains=query) |
            Q(tag__icontains=query)
        )
    if category_slug:
        products = products.filter(category__slug=category_slug)

    if tag:
        products = products.filter(tag__icontains=tag)

    if price_range == "under-200":
        products = products.filter(price__lt=200)
    elif price_range == "200-500":
        products = products.filter(price__gte=200, price__lte=500)
    elif price_range == "500-1000":
        products = products.filter(price__gte=500, price__lte=1000)
    elif price_range == "above-1000":
        products = products.filter(price__gt=1000)

    products = products.annotate(
        review_count=Count("reviews", filter=Q(reviews__approved=True)),
        average_rating=Avg("reviews__rating", filter=Q(reviews__approved=True)),
    )

    if sort == "price_asc":
        products = products.order_by("price", "name")
    elif sort == "price_desc":
        products = products.order_by("-price", "name")
    elif sort == "rating":
        products = products.order_by("-average_rating", "-review_count", "name")
    elif sort == "newest":
        products = products.order_by("-created_at", "name")
    else:  # featured / default
        from django.db.models import Case, When
        featured_ids = [28, 41, 45, 61, 1, 4, 9, 29]
        priority = Case(*[When(id=pid, then=pos) for pos, pid in enumerate(featured_ids)], default=99)
        products = products.order_by(priority, "name")

    total_count = products.count()
    categories = Category.objects.annotate(product_count=Count("products")).order_by("name")

    current_category = None
    if category_slug:
        current_category = Category.objects.filter(slug=category_slug).first()

    return render(request, "store/shop.html", {
        "products": products,
        "categories": categories,
        "query": query,
        "category_slug": category_slug,
        "current_category": current_category,
        "sort": sort,
        "price_range": price_range,
        "tag": tag,
        "total_count": total_count,
        "all_products_count": Product.objects.filter(active=True, stock__gt=0).count(),
        "is_offer": is_offer,
    })


def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return redirect("store:admin_dashboard")
        return redirect("store:home")
    
    # Handle Password Reset Form Action from "Need Help?" Modal
    if request.method == "POST" and request.POST.get("action") == "reset_password":
        reset_id = request.POST.get("reset_id", "").strip()
        new_password = request.POST.get("new_password", "").strip()
        
        user_obj = None
        if "@" in reset_id:
            user_obj = User.objects.filter(email__iexact=reset_id).first()
        if not user_obj:
            user_obj = User.objects.filter(username__iexact=reset_id).first()
            
        if user_obj:
            if len(new_password) < 6:
                messages.error(request, "New password must be at least 6 characters long.")
            else:
                user_obj.set_password(new_password)
                user_obj.save()
                messages.success(request, f"✓ Password for account '{user_obj.username}' has been reset successfully! Please sign in with your new password.")
        else:
            messages.error(request, f"No account found matching '{reset_id}'. Please check your username or registered email.")
        return redirect("store:login")

    next_url = request.GET.get("next") or request.POST.get("next") or "store:home"
    form = LoginForm(request.POST or None)
    
    if request.method == "POST":
        if form.is_valid():
            login_id = form.cleaned_data["username_or_email"].strip()
            password = form.cleaned_data["password"]
            remember_me = form.cleaned_data.get("remember_me", True)
            
            # Allow login via username or email
            user_obj = None
            if "@" in login_id:
                user_obj = User.objects.filter(email__iexact=login_id).first()
            if not user_obj:
                user_obj = User.objects.filter(username__iexact=login_id).first()
            
            user = None
            if user_obj:
                user = authenticate(request, username=user_obj.username, password=password)
            
            if user is not None:
                if user.is_active:
                    login(request, user)
                    if not remember_me:
                        request.session.set_expiry(0)  # expires on browser close
                    else:
                        request.session.set_expiry(1209600)  # 2 weeks
                    messages.success(request, f"Welcome back, {user.first_name or user.username}!")
                    
                    # IF ADMIN / STAFF: REDIRECT DIRECTLY TO ADMIN DASHBOARD
                    if user.is_staff or user.is_superuser:
                        if next_url and next_url not in ["store:home", "/", "/login/"] and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                            return redirect(next_url)
                        return redirect("store:admin_dashboard")
                        
                    if next_url and next_url not in ["store:home", "/", "/login/"] and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                        return redirect(next_url)
                    return redirect("store:customer_dashboard")
                else:
                    messages.error(request, "This account is inactive. Please contact support.")
            else:
                messages.error(request, "Incorrect username/email or password. Please try again.")
        else:
            messages.error(request, "Please enter valid credentials.")
            
    return render(request, "store/login.html", {
        "form": form,
        "next": next_url,
        "active_tab": "login",
    })


def register_view(request):
    if request.user.is_authenticated:
        return redirect("store:home")
    
    next_url = request.GET.get("next") or request.POST.get("next") or "store:home"
    form = RegisterForm(request.POST or None)
    
    if request.method == "POST":
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to Green Nest Nursery, {user.first_name or user.username}! Your account is active.")
            if next_url and next_url not in ["store:home", "/", "/login/", "/register/"] and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect("store:customer_dashboard")
        else:
            messages.error(request, "Please resolve the errors highlighted below.")
            
    return render(request, "store/register.html", {
        "form": form,
        "next": next_url,
        "active_tab": "register",
    })



def product_detail(request, product_id):
    product = get_object_or_404(
        Product.objects.annotate(
            review_count=Count("reviews", filter=Q(reviews__approved=True)),
            average_rating=Avg("reviews__rating", filter=Q(reviews__approved=True)),
        ),
        pk=product_id,
        active=True,
    )
    related_products = Product.objects.filter(
        category=product.category, active=True
    ).exclude(pk=product.pk)[:4]
    if not related_products.exists():
        related_products = Product.objects.filter(active=True).exclude(pk=product.pk)[:4]
    now = timezone.now()
    journal_posts = JournalPost.objects.filter(
        Q(product=product) | Q(category=product.category),
        status=JournalPost.Status.PUBLISHED,
        published_at__lte=now,
    ).distinct()[:3]
    return render(request, "store/product_detail.html", {
        "product": product,
        "related_products": related_products,
        "reviews": Review.objects.filter(product=product, approved=True).select_related("user"),
        "journal_posts": journal_posts,
    })


@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id, active=True)
    cart = _cart(request)
    key = str(product.pk)
    quantity = int(cart.get(key, 0))
    try:
        qty_to_add = int(request.POST.get("quantity", 1))
    except (ValueError, TypeError):
        qty_to_add = 1
    qty_to_add = max(1, qty_to_add)

    if quantity + qty_to_add > product.stock:
        messages.error(request, f"Only {product.stock} {product.name} available in stock.")
    else:
        cart[key] = quantity + qty_to_add
        request.session["cart"] = cart
        messages.success(request, f"🌿 {qty_to_add} × {product.name} added to your bag.")

    action = request.POST.get("action", "")
    if action == "buy_now":
        return redirect("store:checkout")

    next_url = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = reverse("store:cart")
    return redirect(next_url)




def quick_apply_coupon(request):
    code = (request.GET.get("code") or request.POST.get("code") or "GREEN10").strip().upper()
    coupon = Coupon.objects.filter(code=code, active=True).first()
    now = timezone.now()
    if coupon and coupon.starts_at <= now <= coupon.ends_at:
        request.session["coupon_code"] = coupon.code
        if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("format") == "json":
            return JsonResponse({
                "success": True,
                "code": coupon.code,
                "discount_percent": coupon.discount_percent,
                "message": f"Coupon {coupon.code} applied! {coupon.discount_percent}% discount activated.",
            })
        messages.success(request, f"Coupon '{coupon.code}' applied! {coupon.discount_percent}% discount activated.")
    else:
        if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("format") == "json":
            return JsonResponse({
                "success": False,
                "message": "Invalid or expired coupon code.",
            }, status=400)
        messages.error(request, "That coupon is invalid or expired.")

    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER") or reverse("store:cart")
    return redirect(next_url)

def cart(request):
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "apply_coupon":
            form = CouponForm(request.POST)
            if form.is_valid():
                code = form.cleaned_data["code"].strip().upper()
                subtotal = sum(
                    (product.price * int(_cart(request).get(str(product.pk), 0))
                     for product in Product.objects.filter(pk__in=_cart(request), active=True)),
                    Decimal("0.00"),
                )
                coupon = Coupon.objects.filter(code=code).first()
                if coupon and coupon.is_valid_for(subtotal):
                    request.session["coupon_code"] = coupon.code
                    messages.success(request, f"Coupon {coupon.code} applied.")
                else:
                    messages.error(request, "That coupon is invalid, expired, or your subtotal is too low.")
        elif action == "update":
            cart_items = _cart(request)
            product_id = request.POST.get("product_id")
            product = get_object_or_404(Product, pk=product_id, active=True)
            try:
                quantity = int(request.POST.get("quantity", "1"))
            except ValueError:
                quantity = 0
            if quantity <= 0:
                cart_items.pop(str(product.pk), None)
            elif quantity <= product.stock:
                cart_items[str(product.pk)] = quantity
            else:
                messages.error(request, f"Only {product.stock} {product.name} available.")
            request.session["cart"] = cart_items
        elif action == "remove":
            cart_items = _cart(request)
            cart_items.pop(request.POST.get("product_id"), None)
            request.session["cart"] = cart_items
        return redirect("store:cart")
    lines, subtotal, coupon, discount, total = _cart_summary(request)
    return render(request, "store/cart.html", {
        "lines": lines, "subtotal": subtotal, "coupon": coupon,
        "discount": discount, "total": total, "coupon_form": CouponForm(),
    })


@login_required(login_url="store:login")
def checkout(request):
    lines, subtotal, coupon, discount, total = _cart_summary(request)
    if not lines:
        messages.info(request, "Your bag is empty. Please choose plants before checking out.")
        return redirect("store:shop")

    # Pre-populate customer name, phone, and address from latest order if available
    latest_order = Order.objects.filter(user=request.user).order_by("-created_at").first()
    initial = {
        "customer_name": request.user.get_full_name() or request.user.first_name or request.user.username,
        "email": request.user.email if request.user and request.user.email else "",
        "phone": latest_order.phone if latest_order else "",
        "address": latest_order.address if latest_order else "",
        "payment_method": "cod",
    }

    form = CheckoutForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            locked_products = {
                product.pk: product
                for product in Product.objects.select_for_update().filter(
                    pk__in=[line["product"].pk for line in lines], active=True
                )
            }
            for line in lines:
                current = locked_products.get(line["product"].pk)
                if current is None or current.stock < line["quantity"]:
                    messages.error(request, f"{line['product'].name} no longer has enough stock. Please review your bag.")
                    return redirect("store:cart")

            tracking_code = secrets.token_hex(5).upper()
            while Order.objects.filter(tracking_code=tracking_code).exists():
                tracking_code = secrets.token_hex(5).upper()

            method = form.cleaned_data["payment_method"]
            razorpay_pid = form.cleaned_data.get("razorpay_payment_id", "").strip()

            if method == "razorpay":
                if not razorpay_pid:
                    razorpay_pid = f"pay_{secrets.token_hex(8)}"
                payment_status = Order.PaymentStatus.PAID
                order_status = Order.Status.CONFIRMED
            else:
                method = "cod"
                payment_status = Order.PaymentStatus.PENDING
                order_status = Order.Status.CONFIRMED

            order = Order.objects.create(
                user=request.user,
                customer_name=form.cleaned_data["customer_name"],
                phone=form.cleaned_data["phone"],
                address=form.cleaned_data["address"],
                payment_method=method,
                payment_status=payment_status,
                payment_id=razorpay_pid,
                status=order_status,
                coupon=coupon,
                subtotal=subtotal,
                discount=discount,
                total=total,
                tracking_code=tracking_code,
            )
            for line in lines:
                product = locked_products[line["product"].pk]
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=product.name,
                    unit_price=product.price,
                    quantity=line["quantity"],
                )
                product.stock -= line["quantity"]
                product.save(update_fields=["stock"])

        request.session["cart"] = {}
        request.session.pop("coupon_code", None)

        # Update customer email if provided
        cust_email = form.cleaned_data.get("email", "").strip()
        if cust_email and request.user and not request.user.email:
            request.user.email = cust_email
            request.user.save(update_fields=["email"])

        # Send official order receipt via email
        target_email = cust_email or (request.user.email if request.user else None)
        email_sent, email_msg = send_order_receipt_email(order, target_email)

        if method == "razorpay":
            messages.success(request, f"Payment successful! ₹{total} received via Razorpay (Ref: {razorpay_pid}). Order {order.tracking_code} confirmed.")
        else:
            messages.success(request, f"Order {order.tracking_code} placed successfully via Cash on Delivery (COD). Total ₹{total} payable on delivery.")

        if email_sent:
            messages.success(request, f"Order receipt & invoice has been sent to your email ({target_email})!")

        return redirect("store:order_detail", tracking_code=order.tracking_code)

    razorpay_key_id = getattr(settings, "RAZORPAY_KEY_ID", "rzp_test_greenNestStore")
    return render(request, "store/checkout.html", {
        "form": form,
        "lines": lines,
        "subtotal": subtotal,
        "discount": discount,
        "total": total,
        "razorpay_key_id": razorpay_key_id,
    })


def orders(request):
    query_code = (
        request.GET.get("tracking_code")
        or request.GET.get("code")
        or request.POST.get("tracking_code", "")
    ).strip().upper()

    if query_code:
        order = Order.objects.filter(tracking_code__iexact=query_code).first()
        if order:
            return redirect("store:order_detail", tracking_code=order.tracking_code)
        else:
            messages.error(
                request,
                f"No shipment found matching tracking code '{query_code}'. Please verify your code or try one of the demo tracking numbers below.",
            )

    user_orders = []
    if request.user.is_authenticated:
        user_orders = Order.objects.filter(user=request.user).prefetch_related("items__product").order_by("-created_at")

    demo_orders = {
        "confirmed": Order.objects.filter(status="confirmed").first(),
        "packed": Order.objects.filter(status="packed").first(),
        "shipped": Order.objects.filter(status="shipped").first(),
        "delivered": Order.objects.filter(status="delivered").first(),
    }

    return render(
        request,
        "store/orders.html",
        {
            "user_orders": user_orders,
            "demo_orders": demo_orders,
            "searched_code": query_code,
        },
    )


def order_detail(request, tracking_code):
    tracking_code = tracking_code.strip()
    order = get_object_or_404(
        Order.objects.prefetch_related("items__product"),
        tracking_code__iexact=tracking_code,
    )

    # Allow customer or admin to trigger sending receipt email
    if request.method == "POST" and request.POST.get("action") == "email_receipt":
        custom_email = request.POST.get("email_to", "").strip() or (order.user.email if order.user else None)
        if custom_email:
            success, msg = send_order_receipt_email(order, custom_email)
            if success:
                messages.success(request, f"Receipt for order #{order.tracking_code} sent successfully to {custom_email}!")
            else:
                messages.error(request, f"Could not send email receipt: {msg}")
        else:
            messages.error(request, "Please provide a valid email address to receive the receipt.")
        return redirect("store:order_detail", tracking_code=order.tracking_code)

    # Allow staff / admin to change status directly on the tracking page for live testing
    if request.method == "POST" and request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        new_status = request.POST.get("status")
        if new_status in dict(Order.Status.choices):
            order.status = new_status
            order.save(update_fields=["status"])
            messages.success(request, f"Order status updated to '{order.get_status_display()}'! Live tracker updated.")
            return redirect("store:order_detail", tracking_code=order.tracking_code)

    estimated_delivery = order.created_at + timedelta(days=3)

    return render(
        request,
        "store/order_detail.html",
        {
            "order": order,
            "estimated_delivery": estimated_delivery,
            "is_staff_viewer": request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser),
        },
    )


@login_required
def reminders(request):
    return redirect(reverse("store:customer_dashboard") + "?tab=reminders")


@require_POST
@login_required
def delete_reminder(request, reminder_id):
    reminder = get_object_or_404(CareReminder, pk=reminder_id, user=request.user)
    name = reminder.plant_name
    reminder.delete()
    messages.success(request, f"Care schedule for '{name}' removed.")
    return redirect(reverse("store:customer_dashboard") + "?tab=reminders")




@login_required(login_url="store:login")
def customer_dashboard(request):
    user = request.user

    # Action 1: Update Profile Details
    if request.method == "POST" and request.POST.get("action") == "update_profile":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        if not email:
            messages.error(request, "Email address cannot be empty.")
        elif User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
            messages.error(request, "An account with this email address already exists.")
        else:
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.save(update_fields=["first_name", "last_name", "email"])
            messages.success(request, "Your profile details have been updated successfully! 🌱")
        return redirect(reverse("store:customer_dashboard") + "?tab=profile")

    # Action 2: Add Plant Care Reminder
    if request.method == "POST" and request.POST.get("action") == "add_reminder":
        plant_name = request.POST.get("plant_name", "").strip()
        product_id = request.POST.get("product_id")
        try:
            interval = int(request.POST.get("interval_days", 7))
        except (ValueError, TypeError):
            interval = 7
        next_date_str = request.POST.get("next_reminder")

        product = None
        if product_id:
            product = Product.objects.filter(pk=product_id, active=True).first()
            if not plant_name and product:
                plant_name = product.name

        if not plant_name:
            messages.error(request, "Please provide a plant name or select from our nursery catalog.")
            return redirect(reverse("store:customer_dashboard") + "?tab=reminders")

        from datetime import datetime
        if next_date_str:
            try:
                next_reminder = datetime.strptime(next_date_str, "%Y-%m-%d").date()
            except ValueError:
                next_reminder = timezone.now().date() + timedelta(days=interval)
        else:
            next_reminder = timezone.now().date() + timedelta(days=interval)

        CareReminder.objects.create(
            user=user,
            product=product,
            plant_name=plant_name,
            interval_days=max(1, min(90, interval)),
            next_reminder=next_reminder,
            active=True,
        )
        messages.success(request, f"Care schedule for '{plant_name}' has been created! 🌿")
        return redirect(reverse("store:customer_dashboard") + "?tab=reminders")

    # Action 3: Quick Mark Watered Today
    if request.method == "POST" and request.POST.get("action") == "mark_watered":
        reminder_id = request.POST.get("reminder_id")
        reminder = get_object_or_404(CareReminder, pk=reminder_id, user=user)
        reminder.next_reminder = timezone.now().date() + timedelta(days=reminder.interval_days)
        reminder.save(update_fields=["next_reminder"])
        messages.success(request, f"Marked '{reminder.plant_name}' as watered! Next care due on {reminder.next_reminder.strftime('%b %d, %Y')}. 💧")
        return redirect(reverse("store:customer_dashboard") + "?tab=reminders")

    # Query customer data
    customer_orders = Order.objects.filter(user=user).prefetch_related("items", "items__product").order_by("-created_at")
    total_orders = customer_orders.count()
    active_orders = customer_orders.filter(status__in=[Order.Status.CONFIRMED, Order.Status.PACKED, Order.Status.SHIPPED]).count()
    completed_orders = customer_orders.filter(status=Order.Status.DELIVERED).count()
    total_spent = customer_orders.exclude(status=Order.Status.CANCELLED).aggregate(s=Sum("total"))["s"] or Decimal("0.00")

    # Process Care Reminders with status
    raw_reminders = CareReminder.objects.filter(user=user).select_related("product").order_by("next_reminder")
    today = timezone.now().date()
    care_reminders = []
    overdue_count = 0
    today_due_count = 0
    for r in raw_reminders:
        days_left = (r.next_reminder - today).days
        is_overdue = days_left < 0
        is_today = days_left == 0
        if is_overdue:
            overdue_count += 1
            status_label = f"Overdue by {abs(days_left)} day(s)"
            badge_class = "badge-overdue"
        elif is_today:
            today_due_count += 1
            status_label = "Due Today 💧"
            badge_class = "badge-today"
        else:
            status_label = f"Due in {days_left} day(s)"
            badge_class = "badge-upcoming"

        care_reminders.append({
            "reminder": r,
            "days_left": days_left,
            "is_overdue": is_overdue,
            "is_today": is_today,
            "status_label": status_label,
            "badge_class": badge_class,
        })

    # Latest shipping address & contact phone
    latest_order = customer_orders.first()
    shipping_address = latest_order.address if latest_order else ""
    phone = latest_order.phone if latest_order else ""

    # Guides & Catalog options
    guides = CareGuide.objects.filter(published=True)[:4]
    catalog_products = Product.objects.filter(active=True).order_by("name")[:25]
    active_tab = request.GET.get("tab", "orders").strip().lower()
    if active_tab not in ["orders", "reminders", "profile", "guides", "analytics", "bookmarks"]:
        active_tab = "orders"

    # Customer Chart Analytics Data
    months_labels = ["May", "Jun", "Jul", "Aug", "Sep", "Oct"]
    spent_val = float(total_spent)
    if spent_val > 0:
        cust_spending_trend = [
            round(spent_val * 0.15, 2),
            round(spent_val * 0.22, 2),
            round(spent_val * 0.12, 2),
            round(spent_val * 0.28, 2),
            round(spent_val * 0.18, 2),
            round(spent_val, 2),
        ]
    else:
        cust_spending_trend = [0, 0, 0, 0, 0, 0]

    cust_cat_labels = ["Indoor Plants", "Air Purifying", "Succulents", "Outdoor Plants", "Planters & Pots"]
    cust_cat_data = [3, 2, 1, 2, 1] if total_orders > 0 else [1, 1, 1, 1, 1]

    user_bookmarks = JournalBookmark.objects.filter(user=user).select_related("post", "post__author", "post__category").order_by("-created_at")
    return render(request, "store/customer_dashboard.html", {
        "customer": user,
        "user_bookmarks": user_bookmarks,
        "bookmarks_count": user_bookmarks.count(),
        "orders": customer_orders,
        "total_orders": total_orders,
        "active_orders": active_orders,
        "completed_orders": completed_orders,
        "total_spent": total_spent,
        "care_reminders": care_reminders,
        "active_reminders_count": len(care_reminders),
        "overdue_count": overdue_count,
        "today_due_count": today_due_count,
        "shipping_address": shipping_address,
        "phone": phone,
        "guides": guides,
        "catalog_products": catalog_products,
        "today": today,
        "active_tab": active_tab,
        "chart_months_json": json.dumps(months_labels),
        "chart_spending_json": json.dumps(cust_spending_trend),
        "chart_cat_labels_json": json.dumps(cust_cat_labels),
        "chart_cat_data_json": json.dumps(cust_cat_data),
    })


def care_guides(request):
    return render(request, "store/guides.html", {"guides": CareGuide.objects.filter(published=True)})


def care_guide_detail(request, slug):
    guide = get_object_or_404(CareGuide, slug=slug, published=True)
    now = timezone.now()
    journal_posts = JournalPost.objects.filter(
        status=JournalPost.Status.PUBLISHED,
        published_at__lte=now,
    ).order_by("-published_at")[:3]
    return render(request, "store/guide_detail.html", {"guide": guide, "journal_posts": journal_posts})


@require_POST
def subscribe(request):
    email = request.POST.get("email", "").strip().lower()
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError

    try:
        validate_email(email)
    except ValidationError:
        messages.error(request, "Enter a valid email address to subscribe.")
        return redirect(request.POST.get("next") or "store:home")
    subscriber, created = NewsletterSubscriber.objects.get_or_create(email=email)
    if not subscriber.active:
        subscriber.active = True
        subscriber.save(update_fields=["active"])
    messages.success(request, "You're on the GreenNest list. Plant-care notes are on their way.")
    return redirect(request.POST.get("next") or "store:home")


@login_required
def review_product(request, product_id):
    product = get_object_or_404(Product, pk=product_id, active=True)
    if Review.objects.filter(product=product, user=request.user).exists():
        messages.info(request, f"You have already shared a review for {product.name}.")
        return redirect("store:product_detail", product_id=product.pk)
    form = ReviewForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        review = form.save(commit=False)
        review.product = product
        review.user = request.user
        review.approved = True
        review.save()
        messages.success(request, f"Thank you! Your {review.rating}★ rating for {product.name} has been published successfully.")
        return redirect("store:product_detail", product_id=product.pk)
    return render(request, "store/form_page.html", {
        "form": form, "title": f"Review {product.name}", "submit_label": "Submit review",
    })


@staff_member_required(login_url="store:login")
def admin_dashboard(request):
    tab = request.GET.get("tab", "overview").lower()
    order_filter = request.GET.get("status", "").lower()
    product_search = request.GET.get("prod_q", "").strip()
    category_filter = request.GET.get("cat", "").strip()

    if request.method == "POST":
        action = request.POST.get("action")
        
        # 1. Add Plant
        if action == "add_product":
            name = request.POST.get("name", "").strip()
            cat_id = request.POST.get("category_id")
            price = request.POST.get("price", "0.00").strip()
            stock = int(request.POST.get("stock", 0))
            tag = request.POST.get("tag", "").strip()
            image_url = request.POST.get("image_url", "").strip()
            subtitle = request.POST.get("subtitle", "").strip()
            description = request.POST.get("description", "").strip() or subtitle
            sunlight = request.POST.get("sunlight", "Bright Indirect").strip() or "Bright Indirect"
            water_days = int(request.POST.get("water_days", 5) or 5)
            pot_type = request.POST.get("pot_type", "Nursery Pot Inc.").strip() or "Nursery Pot Inc."
            air_purifying = request.POST.get("air_purifying", "High Oxygen").strip() or "High Oxygen"
            
            if name and cat_id and price:
                category = get_object_or_404(Category, pk=cat_id)
                Product.objects.create(
                    name=name,
                    category=category,
                    price=Decimal(price),
                    stock=max(0, stock),
                    tag=tag,
                    image_url=image_url or "https://images.unsplash.com/photo-1485955900006-10f4d324d411?auto=format&fit=crop&w=800&q=85",
                    subtitle=subtitle,
                    description=description,
                    sunlight=sunlight,
                    water_days=max(1, water_days),
                    pot_type=pot_type,
                    air_purifying=air_purifying,
                    active=True
                )
                messages.success(request, f"Plant '{name}' added successfully to Green Nest catalog!")
            else:
                messages.error(request, "Please fill in plant name, category, and price.")
            return redirect(f"{reverse('store:admin_dashboard')}?tab=products")

        # 2. Edit Plant (Full CRUD Update)
        elif action == "edit_product":
            product_id = request.POST.get("product_id")
            product = get_object_or_404(Product, pk=product_id)
            name = request.POST.get("name", "").strip()
            cat_id = request.POST.get("category_id")
            price = request.POST.get("price", "").strip()
            stock = request.POST.get("stock", "").strip()
            tag = request.POST.get("tag", "").strip()
            image_url = request.POST.get("image_url", "").strip()
            subtitle = request.POST.get("subtitle", "").strip()
            description = request.POST.get("description", "").strip()
            sunlight = request.POST.get("sunlight", "").strip()
            water_days = request.POST.get("water_days", "").strip()
            pot_type = request.POST.get("pot_type", "").strip()
            air_purifying = request.POST.get("air_purifying", "").strip()
            is_active = request.POST.get("active") in ["1", "true", "on", True]

            if name:
                product.name = name
            if cat_id:
                product.category = get_object_or_404(Category, pk=cat_id)
            if price:
                product.price = Decimal(price)
            if stock:
                product.stock = max(0, int(stock))
            product.tag = tag
            if image_url:
                product.image_url = image_url
            product.subtitle = subtitle
            if description:
                product.description = description
            if sunlight:
                product.sunlight = sunlight
            if water_days:
                product.water_days = max(1, int(water_days))
            if pot_type:
                product.pot_type = pot_type
            if air_purifying:
                product.air_purifying = air_purifying
            product.active = is_active
            product.save()

            messages.success(request, f"Plant '{product.name}' details updated successfully!")
            return redirect(f"{reverse('store:admin_dashboard')}?tab=products")

        # 3. Update Inventory Stock Only
        elif action == "update_stock":
            product_id = request.POST.get("product_id")
            new_stock = int(request.POST.get("stock", 0))
            product = get_object_or_404(Product, pk=product_id)
            product.stock = max(0, new_stock)
            product.save()
            messages.success(request, f"Stock for '{product.name}' updated to {product.stock}.")
            return redirect(f"{reverse('store:admin_dashboard')}?tab=products")

        # 4. Toggle Product Active Status
        elif action == "toggle_product":
            product_id = request.POST.get("product_id")
            product = get_object_or_404(Product, pk=product_id)
            product.active = not product.active
            product.save()
            status_text = "activated" if product.active else "hidden"
            messages.success(request, f"Plant '{product.name}' is now {status_text}.")
            return redirect(f"{reverse('store:admin_dashboard')}?tab=products")

        # 5. Delete Plant (with Safe Archive if Referenced in Orders)
        elif action == "delete_product":
            product_id = request.POST.get("product_id")
            product = get_object_or_404(Product, pk=product_id)
            name = product.name
            try:
                product.delete()
                messages.success(request, f"Plant '{name}' has been permanently deleted from catalog.")
            except Exception:
                product.active = False
                product.save()
                messages.warning(request, f"Plant '{name}' has past orders attached, so it was safely archived (hidden) instead of permanently deleted.")
            return redirect(f"{reverse('store:admin_dashboard')}?tab=products")

        # 6. Update Order Status
        elif action == "update_order_status":
            order_id = request.POST.get("order_id")
            new_status = request.POST.get("status")
            order = get_object_or_404(Order, pk=order_id)
            if new_status in Order.Status.values:
                order.status = new_status
                if new_status == Order.Status.DELIVERED and order.payment_method == Order.PaymentMethod.COD:
                    order.payment_status = Order.PaymentStatus.PAID
                order.save()
                messages.success(request, f"Order #{order.tracking_code} status updated to '{order.get_status_display()}'.")
            return redirect(f"{reverse('store:admin_dashboard')}?tab=orders")

        # 7. Customer Inquiries Management
        elif action == "update_inquiry_status":
            inquiry_id = request.POST.get("inquiry_id")
            new_status = request.POST.get("status")
            admin_notes = request.POST.get("admin_notes", "").strip()
            inquiry = get_object_or_404(ContactInquiry, pk=inquiry_id)
            if new_status in ContactInquiry.Status.values:
                inquiry.status = new_status
            if admin_notes:
                inquiry.admin_notes = admin_notes
            inquiry.save()
            messages.success(request, f"Inquiry from '{inquiry.name}' updated to {inquiry.get_status_display()}.")
            return redirect(f"{reverse('store:admin_dashboard')}?tab=inquiries")

        elif action == "delete_inquiry":
            inquiry_id = request.POST.get("inquiry_id")
            inquiry = get_object_or_404(ContactInquiry, pk=inquiry_id)
            cust_name = inquiry.name
            inquiry.delete()
            messages.success(request, f"Requirement inquiry from '{cust_name}' removed.")
            return redirect(f"{reverse('store:admin_dashboard')}?tab=inquiries")

        # 8. Create Coupon
        elif action == "create_coupon":
            code = request.POST.get("code", "").strip().upper()
            discount_percent = int(request.POST.get("discount_percent", 10))
            minimum_order = Decimal(request.POST.get("minimum_order", "0.00").strip() or "0.00")
            duration_days = int(request.POST.get("duration_days", 90))
            if code and 1 <= discount_percent <= 90:
                starts_at = timezone.now()
                ends_at = starts_at + timedelta(days=duration_days)
                coupon, created = Coupon.objects.update_or_create(
                    code=code,
                    defaults={
                        "discount_percent": discount_percent,
                        "minimum_order": minimum_order,
                        "starts_at": starts_at,
                        "ends_at": ends_at,
                        "active": True
                    }
                )
                messages.success(request, f"Coupon '{code}' ({discount_percent}% off) is now live!")
            else:
                messages.error(request, "Please enter a valid coupon code and discount percentage (1-90%).")
            return redirect(f"{reverse('store:admin_dashboard')}?tab=coupons")

        elif action == "toggle_coupon":
            coupon_id = request.POST.get("coupon_id")
            coupon = get_object_or_404(Coupon, pk=coupon_id)
            coupon.active = not coupon.active
            coupon.save()
            status_text = "activated" if coupon.active else "paused"
            messages.success(request, f"Coupon '{coupon.code}' is now {status_text}.")
            return redirect(f"{reverse('store:admin_dashboard')}?tab=coupons")

        elif action == "delete_coupon":
            coupon_id = request.POST.get("coupon_id")
            coupon = get_object_or_404(Coupon, pk=coupon_id)
            code = coupon.code
            coupon.delete()
            messages.success(request, f"Coupon '{code}' has been removed.")
            return redirect(f"{reverse('store:admin_dashboard')}?tab=coupons")

        # 6. Moderate Review
        elif action == "approve_review":
            review_id = request.POST.get("review_id")
            review = get_object_or_404(Review, pk=review_id)
            review.approved = True
            review.save()
            messages.success(request, f"Review by {review.user.username} approved.")
            return redirect(f"{reverse('store:admin_dashboard')}?tab=reviews")

        elif action == "delete_review":
            review_id = request.POST.get("review_id")
            review = get_object_or_404(Review, pk=review_id)
            review.delete()
            messages.success(request, "Review removed.")
            return redirect(f"{reverse('store:admin_dashboard')}?tab=reviews")

        # 10. Plant Category Management (Direct in Web Dashboard)
        elif action == "add_category":
            cat_name = request.POST.get("name", "").strip()
            cat_desc = request.POST.get("description", "").strip()
            if cat_name:
                cat = Category.objects.create(name=cat_name, description=cat_desc)
                messages.success(request, f"Plant category '{cat.name}' created.")
            return redirect(f"{reverse('store:admin_dashboard')}?tab=categories")

        elif action == "edit_category":
            cat_id = request.POST.get("category_id")
            cat = get_object_or_404(Category, pk=cat_id)
            cat_name = request.POST.get("name", "").strip()
            cat_desc = request.POST.get("description", "").strip()
            if cat_name:
                cat.name = cat_name
                cat.description = cat_desc
                cat.save()
                messages.success(request, f"Category '{cat.name}' updated successfully.")
            return redirect(f"{reverse('store:admin_dashboard')}?tab=categories")

        elif action == "delete_category":
            cat_id = request.POST.get("category_id")
            cat = get_object_or_404(Category, pk=cat_id)
            name = cat.name
            try:
                cat.delete()
                messages.success(request, f"Category '{name}' deleted.")
            except Exception:
                messages.error(request, f"Cannot delete category '{name}' because it contains active plants. Please reassign or delete the plants first.")
            return redirect(f"{reverse('store:admin_dashboard')}?tab=categories")

        # 11. Care Guide Management (Direct in Web Dashboard)
        elif action == "add_guide":
            title = request.POST.get("title", "").strip()
            summary = request.POST.get("summary", "").strip()
            body = request.POST.get("body", "").strip()
            published = request.POST.get("published") in ["1", "true", "on", True]
            if title and summary and body:
                guide = CareGuide.objects.create(title=title, summary=summary, body=body, published=published)
                messages.success(request, f"Botanical Care Guide '{guide.title}' published successfully.")
            return redirect(f"{reverse('store:admin_dashboard')}?tab=guides")

        elif action == "edit_guide":
            guide_id = request.POST.get("guide_id")
            guide = get_object_or_404(CareGuide, pk=guide_id)
            title = request.POST.get("title", "").strip()
            summary = request.POST.get("summary", "").strip()
            body = request.POST.get("body", "").strip()
            published = request.POST.get("published") in ["1", "true", "on", True]
            if title:
                guide.title = title
            if summary:
                guide.summary = summary
            if body:
                guide.body = body
            guide.published = published
            guide.save()
            messages.success(request, f"Care Guide '{guide.title}' updated successfully.")
            return redirect(f"{reverse('store:admin_dashboard')}?tab=guides")

        elif action == "delete_guide":
            guide_id = request.POST.get("guide_id")
            guide = get_object_or_404(CareGuide, pk=guide_id)
            title = guide.title
            guide.delete()
            messages.success(request, f"Care Guide '{title}' removed.")
            return redirect(f"{reverse('store:admin_dashboard')}?tab=guides")

        # 12. Care Reminder Management (Direct in Web Dashboard)
        elif action == "delete_reminder_admin":
            rem_id = request.POST.get("reminder_id")
            rem = get_object_or_404(CareReminder, pk=rem_id)
            plant_name = rem.plant_name
            rem.delete()
            messages.success(request, f"Care reminder for '{plant_name}' removed.")
            return redirect(f"{reverse('store:admin_dashboard')}?tab=reminders")

        # 13. Newsletter Subscriber Management (Direct in Web Dashboard)
        elif action == "toggle_subscriber":
            sub_id = request.POST.get("subscriber_id")
            sub = get_object_or_404(NewsletterSubscriber, pk=sub_id)
            sub.active = not sub.active
            sub.save()
            status_text = "subscribed" if sub.active else "paused/unsubscribed"
            messages.success(request, f"Subscriber '{sub.email}' is now {status_text}.")
            return redirect(f"{reverse('store:admin_dashboard')}?tab=subscribers")

        elif action == "delete_subscriber":
            sub_id = request.POST.get("subscriber_id")
            sub = get_object_or_404(NewsletterSubscriber, pk=sub_id)
            email = sub.email
            sub.delete()
            messages.success(request, f"Subscriber '{email}' removed.")
            return redirect(f"{reverse('store:admin_dashboard')}?tab=subscribers")

        # 14. User & Staff Management (Direct in Web Dashboard)
        elif action == "toggle_staff":
            user_id = request.POST.get("user_id")
            target_user = get_object_or_404(User, pk=user_id)
            if target_user == request.user:
                messages.warning(request, "You cannot alter your own staff status.")
            else:
                target_user.is_staff = not target_user.is_staff
                target_user.save()
                status_text = "granted Staff permissions" if target_user.is_staff else "revoked Staff permissions"
                messages.success(request, f"User '{target_user.username}' {status_text}.")
            return redirect(f"{reverse('store:admin_dashboard')}?tab=customers")

        elif action == "reset_user_password":
            user_id = request.POST.get("user_id")
            new_pw = request.POST.get("new_password", "").strip()
            target_user = get_object_or_404(User, pk=user_id)
            if new_pw and len(new_pw) >= 6:
                target_user.set_password(new_pw)
                target_user.save()
                messages.success(request, f"Password for user '{target_user.username}' successfully reset.")
            else:
                messages.error(request, "Password must be at least 6 characters.")
            return redirect(f"{reverse('store:admin_dashboard')}?tab=customers")

    # Metrics & Analytics
    delivered_sales = Order.objects.filter(status=Order.Status.DELIVERED).aggregate(total=Sum("total"))["total"] or Decimal("0.00")
    pending_sales = Order.objects.filter(status__in=[Order.Status.PENDING, Order.Status.CONFIRMED, Order.Status.PACKED, Order.Status.SHIPPED]).aggregate(total=Sum("total"))["total"] or Decimal("0.00")
    total_orders = Order.objects.exclude(status=Order.Status.CANCELLED).count()
    pending_orders = Order.objects.filter(status=Order.Status.PENDING).count()
    low_stock_count = Product.objects.filter(stock__lte=5, active=True).count()
    
    # Querysets
    orders_qs = Order.objects.select_related("user").prefetch_related("items").order_by("-created_at")
    if order_filter and order_filter in Order.Status.values:
        orders_qs = orders_qs.filter(status=order_filter)
    
    products_qs = Product.objects.select_related("category").order_by("-id")
    if product_search:
        products_qs = products_qs.filter(Q(name__icontains=product_search) | Q(category__name__icontains=product_search))
    if category_filter:
        products_qs = products_qs.filter(category__id=category_filter)

    categories_all = Category.objects.annotate(prod_count=Count("products")).order_by("name")

    # Admin Charts Data
    admin_months = ["May", "Jun", "Jul", "Aug", "Sep", "Oct"]
    total_rev_val = float(delivered_sales + pending_sales)
    if total_rev_val > 0:
        admin_rev_trend = [
            round(total_rev_val * 0.45, 2),
            round(total_rev_val * 0.58, 2),
            round(total_rev_val * 0.72, 2),
            round(total_rev_val * 0.85, 2),
            round(total_rev_val * 0.94, 2),
            round(total_rev_val, 2),
        ]
    else:
        admin_rev_trend = [12400, 16800, 21500, 26900, 31200, 38500]

    status_labels = ["Delivered", "In-Transit", "Nursery Packed", "Confirmed", "Pending"]
    status_data = [
        Order.objects.filter(status=Order.Status.DELIVERED).count(),
        Order.objects.filter(status=Order.Status.SHIPPED).count(),
        Order.objects.filter(status=Order.Status.PACKED).count(),
        Order.objects.filter(status=Order.Status.CONFIRMED).count(),
        Order.objects.filter(status=Order.Status.PENDING).count(),
    ]

    top_cat_labels = [cat.name for cat in categories_all[:5]]
    top_cat_data = [max(1, cat.prod_count * 3) for cat in categories_all[:5]]
    coupons_all = Coupon.objects.order_by("-active", "-starts_at")
    pending_reviews = Review.objects.filter(approved=False).select_related("product", "user")
    approved_reviews = Review.objects.filter(approved=True).select_related("product", "user").order_by("-created_at")[:15]
    customers_recent = User.objects.filter(is_staff=False).order_by("-date_joined")[:15]
    subscribers_recent = NewsletterSubscriber.objects.order_by("-subscribed_at")[:15]

    return render(request, "store/admin_dashboard.html", {
        "active_tab": tab,
        "order_filter": order_filter,
        "product_search": product_search,
        "category_filter": category_filter,
        "sales": delivered_sales,
        "pending_sales": pending_sales,
        "orders_count": total_orders,
        "pending_orders": pending_orders,
        "products_count": Product.objects.count(),
        "low_stock": low_stock_count,
        "categories_count": categories_all.count(),
        "customers_count": User.objects.filter(is_staff=False).count(),
        "subscribers_count": NewsletterSubscriber.objects.count(),
        "recent_orders": orders_qs[:30],
        "all_products": products_qs,
        "inquiries": ContactInquiry.objects.all().order_by("-created_at"),
        "new_inquiries_count": ContactInquiry.objects.filter(status=ContactInquiry.Status.NEW).count(),
        "categories": categories_all,
        "coupons": coupons_all,
        "pending_reviews": pending_reviews,
        "approved_reviews": approved_reviews,
        "customers": customers_recent,
        "subscribers": subscribers_recent,
        "care_guides": CareGuide.objects.all().order_by("-created_at"),
        "reminders_all": CareReminder.objects.select_related("user", "product").order_by("-id"),
        "subscribers_all": NewsletterSubscriber.objects.all().order_by("-subscribed_at"),
        "users_all": User.objects.all().order_by("-date_joined"),
        "status_choices": Order.Status.choices,
        "admin_url": "/admin/",
        "admin_months_json": json.dumps(admin_months),
        "admin_rev_trend_json": json.dumps(admin_rev_trend),
        "status_labels_json": json.dumps(status_labels),
        "status_data_json": json.dumps(status_data),
        "top_cat_labels_json": json.dumps(top_cat_labels),
        "top_cat_data_json": json.dumps(top_cat_data),
    })


@staff_member_required(login_url="store:login")
def sales_report(request):
    delivered_qs = Order.objects.filter(status=Order.Status.DELIVERED)
    total_sales = delivered_qs.aggregate(total=Sum("total"))["total"] or Decimal("0.00")
    delivered_count = delivered_qs.count()
    aov = (total_sales / delivered_count).quantize(Decimal("0.01")) if delivered_count else Decimal("0.00")

    pipeline_qs = Order.objects.filter(status__in=[Order.Status.CONFIRMED, Order.Status.PACKED, Order.Status.SHIPPED])
    pipeline_revenue = pipeline_qs.aggregate(total=Sum("total"))["total"] or Decimal("0.00")

    total_non_cancelled = Order.objects.exclude(status=Order.Status.CANCELLED).count()

    monthly_sales = (
        delivered_qs.annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(order_count=Count("id"), revenue=Sum("total"))
        .order_by("-month")
    )

    # 6-Month Revenue Trend
    now = timezone.now()
    months_labels = []
    rev_trend = []
    base_samples = [4200.0, 6800.0, 9150.0, 11400.0, 13800.0]
    for i, base_val in enumerate(base_samples):
        m_date = now - timedelta(days=(5 - i) * 30)
        months_labels.append(m_date.strftime("%b %Y"))
        rev_trend.append(base_val)
    # Current month
    months_labels.append(now.strftime("%b %Y"))
    rev_trend.append(float(total_sales) if float(total_sales) > 0 else 1834.0)

    # Payment Breakdown
    cod_rev = float(Order.objects.filter(payment_method="cod").exclude(status=Order.Status.CANCELLED).aggregate(s=Sum("total"))["s"] or Decimal("0.00"))
    online_rev = float(Order.objects.filter(payment_method__in=["razorpay", "online"]).exclude(status=Order.Status.CANCELLED).aggregate(s=Sum("total"))["s"] or Decimal("0.00"))

    # Recent Delivered Orders
    recent_delivered = delivered_qs.prefetch_related("items").order_by("-created_at")[:8]

    return render(request, "store/sales_report.html", {
        "monthly_sales": monthly_sales,
        "total_sales": total_sales,
        "delivered_count": delivered_count,
        "aov": aov,
        "pipeline_revenue": pipeline_revenue,
        "total_orders": total_non_cancelled,
        "chart_months_json": json.dumps(months_labels),
        "chart_rev_json": json.dumps(rev_trend),
        "cod_rev": cod_rev,
        "online_rev": online_rev,
        "recent_delivered": recent_delivered,
    })

def order_email_receipt_view(request, tracking_code):
    """Live in-browser preview of the exact customer email receipt."""
    from django.http import HttpResponse
    from .email_utils import render_order_receipt_html
    order = get_object_or_404(
        Order.objects.prefetch_related("items__product"),
        tracking_code__iexact=tracking_code.strip(),
    )
    html_markup = render_order_receipt_html(order)
    return HttpResponse(html_markup, content_type="text/html")

def inbox_view(request):
    """Interactive In-App Customer Mailbox to see all received order receipts."""
    from .models import CustomerEmailInbox
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            emails = CustomerEmailInbox.objects.all().order_by("-created_at")
        else:
            emails = CustomerEmailInbox.objects.filter(user=request.user).order_by("-created_at")
    else:
        emails = CustomerEmailInbox.objects.all().order_by("-created_at")[:10]

    selected_id = request.GET.get("msg")
    selected_email = None
    if selected_id:
        selected_email = emails.filter(pk=selected_id).first()
    if not selected_email and emails.exists():
        selected_email = emails.first()

    return render(request, "store/inbox.html", {
        "emails": emails,
        "selected_email": selected_email,
    })


def contact_view(request):
    """Customer Contact Us & Custom Plant Requirements page."""
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        subject = request.POST.get("subject", "").strip() or "Plant Requirement / Inquiry"
        message = request.POST.get("message", "").strip()

        if not name or not email or not message:
            messages.error(request, "Please provide your name, email address, and plant requirement message.")
        else:
            inquiry = ContactInquiry.objects.create(
                name=name,
                email=email,
                phone=phone,
                subject=subject,
                message=message,
                status=ContactInquiry.Status.NEW,
            )
            messages.success(request, f"Thank you, {name}! Your plant requirement inquiry has been submitted. Our nursery botanical expert will contact you shortly.")
            return redirect("store:contact")

    return render(request, "store/contact.html")


# ==============================================================================
# Plant Journal (Blog) Module Views
# ==============================================================================

def journal_list(request):
    """Public Plant Journal listing page with search, filters & pagination."""
    now = timezone.now()
    posts_qs = JournalPost.objects.filter(
        status=JournalPost.Status.PUBLISHED,
        published_at__lte=now,
    ).select_related("author", "category", "product").prefetch_related("tags")

    # Search Filter
    query = (request.GET.get("q") or "").strip()
    if query:
        posts_qs = posts_qs.filter(
            Q(title__icontains=query)
            | Q(excerpt__icontains=query)
            | Q(body__icontains=query)
            | Q(tags__name__icontains=query)
            | Q(author__username__icontains=query)
            | Q(author__first_name__icontains=query)
        ).distinct()

    # Category Filter
    category_slug = (request.GET.get("category") or "").strip()
    selected_category = None
    if category_slug:
        posts_qs = posts_qs.filter(category__slug=category_slug)
        selected_category = Category.objects.filter(slug=category_slug).first()

    # Tag Filter
    tag_slug = (request.GET.get("tag") or "").strip()
    selected_tag = None
    if tag_slug:
        posts_qs = posts_qs.filter(tags__slug=tag_slug)
        selected_tag = JournalTag.objects.filter(slug=tag_slug).first()

    # Pagination: 6 posts per page
    paginator = Paginator(posts_qs, 6)
    page_number = request.GET.get("page", 1)
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # All active categories and tags for sidebar pills
    categories = Category.objects.annotate(
        journal_count=Count("journal_posts", filter=Q(journal_posts__status=JournalPost.Status.PUBLISHED, journal_posts__published_at__lte=now))
    ).filter(journal_count__gt=0).order_by("name")

    tags = JournalTag.objects.annotate(
        post_count=Count("posts", filter=Q(posts__status=JournalPost.Status.PUBLISHED, posts__published_at__lte=now))
    ).filter(post_count__gt=0).order_by("name")

    # Featured post (hero article on first page without filters)
    featured_post = None
    if not query and not category_slug and not tag_slug and str(page_number) in ["1", ""]:
        featured_post = posts_qs.first()

    # User's bookmarked post IDs if logged in
    bookmarked_ids = set()
    if request.user.is_authenticated:
        bookmarked_ids = set(
            JournalBookmark.objects.filter(user=request.user).values_list("post_id", flat=True)
        )

    return render(request, "store/journal/list.html", {
        "page_obj": page_obj,
        "posts": page_obj.object_list,
        "query": query,
        "category_slug": category_slug,
        "selected_category": selected_category,
        "tag_slug": tag_slug,
        "selected_tag": selected_tag,
        "categories": categories,
        "tags": tags,
        "featured_post": featured_post,
        "bookmarked_ids": bookmarked_ids,
        "total_posts_count": posts_qs.count(),
    })


def journal_detail(request, slug):
    """Single Journal Post view with reading time, related plants/posts & comments."""
    now = timezone.now()
    if request.user.is_staff:
        post = get_object_or_404(
            JournalPost.objects.select_related("author", "category", "product").prefetch_related("tags"),
            slug=slug,
        )
    else:
        post = get_object_or_404(
            JournalPost.objects.select_related("author", "category", "product").prefetch_related("tags"),
            slug=slug,
            status=JournalPost.Status.PUBLISHED,
            published_at__lte=now,
        )

    # Bookmark state
    is_bookmarked = False
    if request.user.is_authenticated:
        is_bookmarked = JournalBookmark.objects.filter(user=request.user, post=post).exists()

    # Approved comments
    approved_comments = post.comments.filter(is_approved=True).select_related("author").order_by("created_at")
    
    # Customer's pending comments
    user_pending_comments = []
    if request.user.is_authenticated and not request.user.is_staff:
        user_pending_comments = post.comments.filter(author=request.user, is_approved=False).order_by("created_at")

    # Related plants / products
    related_product = post.product
    extra_plants = []
    if post.category:
        extra_plants = Product.objects.filter(category=post.category, active=True)
        if related_product:
            extra_plants = extra_plants.exclude(pk=related_product.pk)
        extra_plants = extra_plants[:3]

    # Related posts (by category or tags)
    related_posts = JournalPost.objects.filter(
        status=JournalPost.Status.PUBLISHED,
        published_at__lte=now,
    ).exclude(pk=post.pk)
    if post.category:
        related_posts = related_posts.filter(category=post.category)
    elif post.tags.exists():
        related_posts = related_posts.filter(tags__in=post.tags.all())
    related_posts = related_posts.distinct().order_by("-published_at")[:3]

    comment_form = JournalCommentForm()

    return render(request, "store/journal/detail.html", {
        "post": post,
        "is_bookmarked": is_bookmarked,
        "comments": approved_comments,
        "pending_comments": user_pending_comments,
        "comments_count": approved_comments.count(),
        "related_product": related_product,
        "extra_plants": extra_plants,
        "related_posts": related_posts,
        "comment_form": comment_form,
    })


@login_required(login_url="store:login")
@require_POST
def journal_add_comment(request, slug):
    """Customer & staff comment submission for journal posts."""
    now = timezone.now()
    if request.user.is_staff:
        post = get_object_or_404(JournalPost, slug=slug)
    else:
        post = get_object_or_404(JournalPost, slug=slug, status=JournalPost.Status.PUBLISHED, published_at__lte=now)

    form = JournalCommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        if request.user.is_staff:
            comment.is_approved = True
            comment.save()
            messages.success(request, "Your botanical staff response has been published directly.")
        else:
            comment.is_approved = False
            comment.save()
            messages.info(request, "Thank you for commenting! Your feedback is pending approval by GreenNest staff.")
    else:
        messages.error(request, "Please enter a valid comment message.")

    return redirect("store:journal_detail", slug=post.slug)


@login_required(login_url="store:login")
@require_POST
def journal_toggle_bookmark(request, slug):
    """Bookmark or unbookmark a journal article."""
    post = get_object_or_404(JournalPost, slug=slug)
    existing = JournalBookmark.objects.filter(user=request.user, post=post).first()
    if existing:
        existing.delete()
        bookmarked = False
        msg = f"Removed '{post.title}' from your saved bookmarks."
    else:
        JournalBookmark.objects.create(user=request.user, post=post)
        bookmarked = True
        msg = f"Saved '{post.title}' to your Plant Journal bookmarks! 🌿"

    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("format") == "json":
        return JsonResponse({"bookmarked": bookmarked, "message": msg})

    messages.success(request, msg)
    next_url = request.POST.get("next") or reverse("store:journal_detail", kwargs={"slug": post.slug})
    return redirect(next_url)


@login_required(login_url="store:login")
def customer_bookmarks(request):
    """Direct route for viewing customer bookmarks, redirects to customer dashboard tab."""
    return redirect(f"{reverse('store:customer_dashboard')}?tab=bookmarks")


# ==============================================================================
# Staff Management Views for Plant Journal
# ==============================================================================

@staff_member_required(login_url="store:login")
def manage_journal(request):
    """Staff Plant Journal dashboard with posts list, quick status toggles, and pending comments moderation."""
    status_filter = request.GET.get("status", "").lower()
    query = request.GET.get("q", "").strip()

    posts_qs = JournalPost.objects.select_related("author", "category", "product").prefetch_related("tags")
    if status_filter in ["draft", "scheduled", "published"]:
        posts_qs = posts_qs.filter(status=status_filter)
    if query:
        posts_qs = posts_qs.filter(Q(title__icontains=query) | Q(author__username__icontains=query))

    pending_comments = JournalComment.objects.filter(is_approved=False).select_related("post", "author").order_by("-created_at")

    return render(request, "store/journal/manage_list.html", {
        "posts": posts_qs,
        "status_filter": status_filter,
        "query": query,
        "total_posts": JournalPost.objects.count(),
        "published_count": JournalPost.objects.filter(status="published").count(),
        "drafts_count": JournalPost.objects.filter(status="draft").count(),
        "scheduled_count": JournalPost.objects.filter(status="scheduled").count(),
        "pending_comments": pending_comments,
        "pending_comments_count": pending_comments.count(),
    })


@staff_member_required(login_url="store:login")
def manage_journal_create(request):
    """Staff view to author and publish a new Journal post."""
    if request.method == "POST":
        form = JournalPostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            if post.status == "published" and not post.published_at:
                post.published_at = timezone.now()
            post.save()
            form.save(commit=True)
            messages.success(request, f"Article '{post.title}' created successfully!")
            return redirect("store:manage_journal")
    else:
        form = JournalPostForm(initial={"status": "published", "published_at": timezone.now()})

    return render(request, "store/journal/manage_form.html", {
        "form": form,
        "is_edit": False,
        "title": "Create Plant Journal Article",
    })


@staff_member_required(login_url="store:login")
def manage_journal_edit(request, post_id):
    """Staff view to edit an existing Journal post."""
    post = get_object_or_404(JournalPost, pk=post_id)
    if request.method == "POST":
        form = JournalPostForm(request.POST, instance=post)
        if form.is_valid():
            p = form.save(commit=False)
            if p.status == "published" and not p.published_at:
                p.published_at = timezone.now()
            p.save()
            form.save(commit=True)
            messages.success(request, f"Article '{post.title}' updated successfully!")
            return redirect("store:manage_journal")
    else:
        form = JournalPostForm(instance=post)

    return render(request, "store/journal/manage_form.html", {
        "form": form,
        "post": post,
        "is_edit": True,
        "title": f"Edit Article: {post.title}",
    })


@staff_member_required(login_url="store:login")
@require_POST
def manage_journal_toggle_publish(request, post_id):
    """Quick toggle publish/unpublish from staff dashboard."""
    post = get_object_or_404(JournalPost, pk=post_id)
    if post.status == "published":
        post.status = "draft"
        messages.info(request, f"Article '{post.title}' is now unpublished (Draft).")
    else:
        post.status = "published"
        if not post.published_at or post.published_at > timezone.now():
            post.published_at = timezone.now()
        messages.success(request, f"Article '{post.title}' is now Published and live!")
    post.save()
    return redirect("store:manage_journal")


@staff_member_required(login_url="store:login")
@require_POST
def manage_journal_comment_moderate(request, comment_id):
    """Approve or delete customer comments."""
    comment = get_object_or_404(JournalComment, pk=comment_id)
    action = request.POST.get("action", "approve")
    post_slug = comment.post.slug
    if action == "approve":
        comment.is_approved = True
        comment.save()
        messages.success(request, f"Comment by {comment.author} has been approved.")
    elif action == "delete":
        comment.delete()
        messages.warning(request, "Comment was deleted.")

    next_url = request.POST.get("next") or reverse("store:manage_journal")
    return redirect(next_url)
