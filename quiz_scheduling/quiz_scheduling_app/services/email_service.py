# quiz_scheduling_app/services/email_service.py
from django.core.mail import send_mail
from django.conf import settings

class EmailService:
    @staticmethod
    def send_otp_email(email, otp):
        subject = 'Quiz Scheduling - OTP Verification'
        message = f'Your OTP code is: {otp}\nThis code will expire in 5 minutes.'
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )

    @staticmethod
    def send_password_reset_email(email, otp):
        subject = 'Quiz Scheduling - Password Reset'
        message = f'Your password reset code is: {otp}\nThis code will expire in 15 minutes.'
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )