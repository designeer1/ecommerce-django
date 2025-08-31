from celery import shared_task
from django.contrib.auth.models import User
from .models import CustomerProfile, NewProductNotification, UserNotification
from .sms_utils import send_sms

@shared_task
def send_new_product_notifications(product_notification_id):
    """
    Send SMS notifications to all registered users about new product
    """
    try:
        notification = NewProductNotification.objects.get(id=product_notification_id)
        
        message = f"🚀 New at TaskPro: {notification.product_name} for ₹{notification.product_price}. Shop now!"
        
        # Get all users with phone numbers who want notifications
        users_with_phones = CustomerProfile.objects.exclude(
            phone_number__isnull=True
        ).exclude(
            phone_number=''
        ).filter(
            receive_sms_notifications=True
        )
        
        sent_count = 0
        for profile in users_with_phones:
            # Create user notification
            UserNotification.objects.get_or_create(
                user=profile.user,
                notification=notification
            )
            
            # Send SMS
            if send_sms(profile.phone_number, message):
                sent_count += 1
        
        # Mark notification as processed
        notification.notified = True
        notification.save()
        
        return f"Notifications sent to {sent_count} users"
        
    except NewProductNotification.DoesNotExist:
        return "Notification not found"
    except Exception as e:
        return f"Error: {str(e)}"