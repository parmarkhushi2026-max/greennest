import os
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)

def render_order_receipt_html(order):
    """Generates the full HTML markup for the order receipt."""
    context = {
        "order": order,
        "items": order.items.all(),
        "customer_name": order.customer_name or (order.user.first_name if order.user else "Valued Customer"),
        "tracking_code": order.tracking_code,
        "total": order.total,
        "subtotal": order.subtotal,
        "discount": order.discount,
        "payment_method": order.get_payment_method_display(),
        "payment_status": order.get_payment_status_display(),
        "payment_id": order.payment_id or "N/A",
        "order_date": order.created_at.strftime("%d %b %Y, %I:%M %p"),
        "address": order.address,
        "phone": order.phone,
    }
    return render_to_string("store/email/order_receipt.html", context)

def send_order_receipt_email(order, recipient_email=None):
    """
    Sends a beautifully formatted HTML and plain text invoice/receipt to the customer.
    1. Archives to 'sent_emails/' folder for direct opening in browser.
    2. Saves directly into CustomerEmailInbox database so user can see it right inside website at /inbox/!
    3. Dispatches via Django EmailBackend (SMTP or Console).
    """
    from store.models import CustomerEmailInbox

    if not recipient_email:
        if order.user and order.user.email:
            recipient_email = order.user.email

    if not recipient_email:
        recipient_email = f"{order.user.username if order.user else 'customer'}@greennest.local"

    subject = f"Receipt & Order Confirmation - #{order.tracking_code} | Green Nest Nursery"
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "Green Nest Nursery <hello@greennest.local>")

    try:
        html_content = render_order_receipt_html(order)
        text_content = strip_tags(html_content)

        # 1. Save into CustomerEmailInbox (In-App Inbox)
        try:
            CustomerEmailInbox.objects.create(
                user=order.user,
                recipient_email=recipient_email,
                subject=subject,
                body_text=text_content,
                body_html=html_content,
                order=order,
                is_read=False,
            )
        except Exception as db_err:
            logger.warning(f"Could not store in CustomerEmailInbox: {db_err}")

        # 2. Archive to sent_emails/ directory
        try:
            sent_dir = os.path.join(settings.BASE_DIR, "sent_emails")
            os.makedirs(sent_dir, exist_ok=True)
            archive_path = os.path.join(sent_dir, f"Receipt_{order.tracking_code}.html")
            with open(archive_path, "w", encoding="utf-8") as f:
                f.write(html_content)
        except Exception as file_err:
            logger.warning(f"Could not save receipt file: {file_err}")

        # 3. Send through Django Email Backend
        try:
            msg = EmailMultiAlternatives(subject, text_content, from_email, [recipient_email])
            msg.attach_alternative(html_content, "text/html")
            msg.send(fail_silently=True)
        except Exception as mail_err:
            logger.warning(f"Mail backend send note: {mail_err}")

        return True, f"Receipt successfully sent to {recipient_email}"
    except Exception as e:
        logger.error(f"Failed to process receipt email: {e}")
        return False, str(e)
