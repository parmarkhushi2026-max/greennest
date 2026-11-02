from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True, blank=True)
    description = models.CharField(max_length=240, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=140)
    subtitle = models.CharField(max_length=180, blank=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    price = models.DecimalField(max_digits=9, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    image_url = models.URLField(max_length=500, blank=True)
    alt_text = models.CharField(max_length=200, blank=True)
    tag = models.CharField(max_length=40, blank=True)
    sunlight = models.CharField(max_length=80, blank=True, default="Bright Indirect", help_text="e.g. Full Sun, Bright Indirect, Low Light")
    water_days = models.PositiveSmallIntegerField(default=5, help_text="Watering frequency in days (e.g. 3, 7, 14)")
    pot_type = models.CharField(max_length=80, blank=True, default="Nursery Pot Inc.", help_text="e.g. Self-Watering Ceramic, Terracotta Clay, Nursery Pot Inc.")
    air_purifying = models.CharField(max_length=80, blank=True, default="High Oxygen", help_text="e.g. NASA Certified, High Oxygen, Toxin Filter")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Coupon(models.Model):
    code = models.CharField(max_length=32, unique=True)
    discount_percent = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(90)]
    )
    minimum_order = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField()
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code

    def is_valid_for(self, subtotal):
        now = timezone.now()
        return (
            self.active
            and self.starts_at <= now <= self.ends_at
            and subtotal >= self.minimum_order
        )


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        PACKED = "packed", "Packed"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class PaymentMethod(models.TextChoices):
        COD = "cod", "Cash on Delivery (COD)"
        RAZORPAY = "razorpay", "Razorpay (Online Payment)"
        ONLINE = "online", "Online Payment"

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="store_orders")
    customer_name = models.CharField(max_length=140)
    phone = models.CharField(max_length=30)
    address = models.TextField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    payment_method = models.CharField(max_length=12, choices=PaymentMethod.choices)
    payment_status = models.CharField(max_length=12, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    payment_id = models.CharField(max_length=80, blank=True, default="")
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    tracking_code = models.CharField(max_length=24, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order {self.tracking_code}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    product_name = models.CharField(max_length=140)
    unit_price = models.DecimalField(max_digits=9, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.quantity} × {self.product_name}"


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.email


class CareReminder(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="care_reminders")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    plant_name = models.CharField(max_length=140, blank=True)
    interval_days = models.PositiveSmallIntegerField(default=7, validators=[MinValueValidator(1), MaxValueValidator(90)])
    next_reminder = models.DateField()
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["next_reminder"]

    def __str__(self):
        return f"{self.plant_name} care reminder for {self.user}"


class CareGuide(models.Model):
    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    summary = models.CharField(max_length=280)
    body = models.TextField()
    published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="store_reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(max_length=1200)
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["product", "user"], name="one_review_per_customer_product")
        ]

    def __str__(self):
        return f"{self.rating}/5 for {self.product}"


class CustomerEmailInbox(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="customer_emails", null=True, blank=True)
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=255)
    body_text = models.TextField()
    body_html = models.TextField()
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name="sent_receipt_emails")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Email to {self.recipient_email}: {self.subject}"


class ContactInquiry(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New Inquiry"
        IN_PROGRESS = "in_progress", "In Progress"
        RESOLVED = "resolved", "Resolved"

    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    subject = models.CharField(max_length=200, help_text="Plant Requirement / Inquiry Type")
    message = models.TextField(help_text="Detailed plant requirements or question")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    admin_notes = models.TextField(blank=True, help_text="Internal note by nursery manager")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Contact Inquiry"
        verbose_name_plural = "Contact Inquiries"

    def __str__(self):
        return f"{self.name} - {self.subject} ({self.get_status_display()})"
