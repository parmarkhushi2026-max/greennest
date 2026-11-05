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


def send_order_delivery_email(order, recipient_email=None):
    """
    Sends an official Delivery Confirmation email to the customer with botanical unboxing & care tips.
    Dispatches via Brevo SMTP relay and archives in CustomerEmailInbox and sent_emails/.
    """
    from store.models import CustomerEmailInbox

    if not recipient_email:
        if order.user and order.user.email:
            recipient_email = order.user.email
    if not recipient_email:
        recipient_email = getattr(settings, "DEFAULT_FROM_EMAIL", "parmarkhushi2026@gmail.com")

    subject = f"Delivered: Your Green Nest Order #{order.tracking_code} Has Arrived! - Green Nest Nursery"
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "Green Nest Nursery <parmarkhushi2026@gmail.com>")
    customer_name = order.customer_name or (order.user.first_name if order.user else "Plant Parent")

    items_html = ""
    for item in order.items.all():
        pname = item.product_name or (item.product.name if item.product else "Nursery Plant")
        itotal = item.unit_price * item.quantity
        items_html += f"""
        <tr>
            <td style="padding: 10px 12px; border-bottom: 1px solid #edf2ef; font-size: 13.5px; color: #1e293b;">{pname}</td>
            <td style="padding: 10px 12px; border-bottom: 1px solid #edf2ef; font-size: 13.5px; color: #64748b; text-align: center;">x{item.quantity}</td>
            <td style="padding: 10px 12px; border-bottom: 1px solid #edf2ef; font-size: 13.5px; color: #014e37; font-weight: 700; text-align: right;">₹{itotal}</td>
        </tr>
        """

    html_content = f"""<!doctype html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f7faf8; margin: 0; padding: 24px 16px; color: #1e293b;">
  <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 16px; overflow: hidden; border: 1px solid #e2ebe5; box-shadow: 0 10px 30px rgba(1, 78, 55, 0.08);">
    
    <!-- Header -->
    <div style="background: linear-gradient(135deg, #013827 0%, #014e37 100%); color: #ffffff; padding: 32px 24px; text-align: center;">
      <div style="display: inline-block; background: rgba(255,255,255,0.18); color: #a7f3d0; font-size: 11px; font-weight: 800; letter-spacing: 0.12em; text-transform: uppercase; padding: 4px 12px; border-radius: 20px; margin-bottom: 12px;">
        Order Delivered Successfully
      </div>
      <h1 style="margin: 0 0 6px; font-size: 24px; font-weight: 800; color: #ffffff;">Your Plants Have Arrived!</h1>
      <p style="margin: 0; font-size: 14px; color: #d1fae5;">Order #{order.tracking_code} has been delivered to your doorstep.</p>
    </div>

    <!-- Body Content -->
    <div style="padding: 28px 24px;">
      <p style="font-size: 15px; line-height: 1.6; margin: 0 0 18px; color: #334155;">
        Dear <strong>{customer_name}</strong>,<br>
        Great news! Your Green Nest live botanical plants and planters have been successfully delivered to:
      </p>

      <div style="background: #f8faf9; border-left: 4px solid #10b981; padding: 14px 16px; border-radius: 6px; margin-bottom: 22px; font-size: 13.5px; color: #1f2937;">
        <strong>Delivery Address:</strong><br>
        {order.address or 'Registered Customer Address'}<br>
        <span style="color: #64748b;">Phone: {order.phone or 'N/A'}</span>
      </div>

      <!-- Delivered Items -->
      <h3 style="font-size: 15px; font-weight: 700; color: #014e37; margin: 0 0 10px; border-bottom: 2px solid #eaf4ee; padding-bottom: 6px;">
        Delivered Items
      </h3>
      <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px;">
        <thead>
          <tr style="background: #f1f5f3; font-size: 12px; color: #475569; text-transform: uppercase;">
            <th style="padding: 8px 12px; text-align: left;">Plant Item</th>
            <th style="padding: 8px 12px; text-align: center;">Qty</th>
            <th style="padding: 8px 12px; text-align: right;">Amount</th>
          </tr>
        </thead>
        <tbody>
          {items_html}
        </tbody>
      </table>

      <!-- Care Tips Box -->
      <div style="background: #edf7f2; border: 1.5px solid #a7f3d0; border-radius: 12px; padding: 18px; margin-bottom: 24px;">
        <h4 style="margin: 0 0 10px; font-size: 14px; font-weight: 800; color: #014e37;">
          Important First-Week Plant Care Instructions:
        </h4>
        <ul style="margin: 0; padding-left: 20px; font-size: 13px; line-height: 1.7; color: #166534;">
          <li><strong>Unbox Gently:</strong> Open package carefully and remove protective transit netting.</li>
          <li><strong>Acclimate in Shade:</strong> Place plants in bright, indirect sunlight for 48 hours to recover from transit.</li>
          <li><strong>Water Check:</strong> Feel the top inch of soil; if dry, give a gentle drink of water.</li>
          <li><strong>Set Reminders:</strong> Use your Green Nest account to enable automatic watering reminders.</li>
        </ul>
      </div>

      <!-- Actions -->
      <div style="text-align: center; margin-top: 24px;">
        <p style="font-size: 13px; color: #64748b; margin-bottom: 12px;">Need care advice or botanical questions?</p>
        <a href="http://127.0.0.1:8000/guides/" style="display: inline-block; background: #014e37; color: #ffffff; text-decoration: none; padding: 12px 24px; border-radius: 24px; font-size: 13.5px; font-weight: 700; box-shadow: 0 4px 12px rgba(1, 78, 55, 0.2);">
          Browse Expert Care Guides &rarr;
        </a>
      </div>
    </div>

    <!-- Footer -->
    <div style="background: #f8faf9; border-top: 1px solid #edf2ef; padding: 18px 24px; text-align: center; font-size: 12px; color: #64748b;">
      <p style="margin: 0 0 4px;">&copy; Green Nest Nursery Chennai. High-quality nursery plants &amp; care.</p>
      <p style="margin: 0;">Helpline: +91 98765 43210 &bull; Email: hello@greennest.local</p>
    </div>

  </div>
</body>
</html>
"""
    text_content = f"Delivered: Your Green Nest Order #{order.tracking_code} Has Arrived!\n\nDear {customer_name},\nYour plant order has been successfully delivered to: {order.address}.\n\nThank you for choosing Green Nest Nursery!\nhttp://127.0.0.1:8000/orders/"

    # 1. Save in CustomerEmailInbox
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
        logger.warning(f"Could not store delivery in CustomerEmailInbox: {db_err}")

    # 2. Archive in sent_emails/
    try:
        sent_dir = os.path.join(settings.BASE_DIR, "sent_emails")
        os.makedirs(sent_dir, exist_ok=True)
        archive_path = os.path.join(sent_dir, f"Delivered_{order.tracking_code}.html")
        with open(archive_path, "w", encoding="utf-8") as f:
            f.write(html_content)
    except Exception as file_err:
        logger.warning(f"Could not save delivery file: {file_err}")

    # 3. Send through Django Email Backend (Brevo)
    try:
        msg = EmailMultiAlternatives(subject, text_content, from_email, [recipient_email])
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)
        return True, f"Delivery confirmation email sent to {recipient_email}"
    except Exception as mail_err:
        logger.warning(f"Mail backend delivery note: {mail_err}")
        return False, str(mail_err)
