from django.conf import settings
from django.core.mail import send_mail


def send_welcome_email(request, email, first_name):
    """Send a welcome email after user registration."""
    subject = "Welcome to Yummy Recipes!"
    message = f"Hi {first_name},\n\nWelcome to Yummy Recipes! We're excited to have you join our foodie community."
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [email]
    send_mail(subject, message, from_email, recipient_list, fail_silently=True)
