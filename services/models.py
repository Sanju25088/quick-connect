from datetime import timezone
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.timezone import now
from django.utils import timezone  # Correct

from django.core.exceptions import ValidationError  

class CustomUser(AbstractUser):
    USER_TYPES = [
        ('admin', 'Admin'),
        ('vendor', 'Vendor'),
        ('customer', 'Customer'),
    ]
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='customer')
    profile_image = models.ImageField(upload_to='profile_photo/', blank=True, null=True)
    created_at = models.DateTimeField(default=now)
    category = models.CharField(max_length=100,  blank=True)

from django.core.validators import RegexValidator
class CustomerInfo(models.Model):
    customer = models.OneToOneField(CustomUser, on_delete=models.CASCADE, limit_choices_to={'user_type': 'customer'})
    contact_no = models.CharField(max_length=15)
    permanent_address = models.TextField()
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    location_name = models.CharField(max_length=255, null=True, blank=True)  # Store full address




from django.utils.translation import gettext_lazy as _

class ServiceProvider(models.Model):
    class AvailabilityStatus(models.TextChoices):
        AVAILABLE = 'Available', _('Available')
        BUSY = 'Busy', _('Busy')
        OFFLINE = 'Offline', _('Offline')
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    business_name = models.CharField(max_length=255)
    
    category_type = models.CharField(max_length=100, null =True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    location_name = models.CharField(max_length=255, null=True, blank=True)  # Store location name

    contact_number = models.CharField(max_length=15)
    availability_status = models.CharField(
        max_length=10,
        choices=AvailabilityStatus.choices,
        default=AvailabilityStatus.AVAILABLE
    )
    service_type = models.CharField(max_length=100, default='both')
    working_hours = models.IntegerField(null=True, blank=True)
    upi_qr_code = models.ImageField(upload_to='upi_qr_codes/', null=True, blank=True)


class ShopItem(models.Model):
    vendor = models.ForeignKey("ServiceProvider", on_delete=models.CASCADE)
    product_name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

class Booking(models.Model):
    customer = models.ForeignKey(CustomerInfo, on_delete=models.CASCADE)
    vendor = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    booking_time = models.DateTimeField(auto_now_add=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled')
    ], default='Pending')
    service_type = models.CharField(max_length=20, choices=[
        ('pick_up', 'Pick Up'),
        ('home_delivery', 'Home Delivery')
    ], default='home_delivery')
    delivery_time = models.DateTimeField(null=True, blank=True)
    pickup_time = models.DateTimeField(null=True, blank=True)

    # Payment fields
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('credit_card', 'Credit Card'),
            ('debit_card', 'Debit Card'),
            ('upi', 'UPI'),
            ('net_banking', 'Net Banking'),
            ('wallet', 'Digital Wallet'),
            ('cod', 'Cash on Delivery')
        ],
        default='cod'
    )
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('refunded', 'Refunded')
        ],
        default='pending'
    )

    def __str__(self):
        return f"Booking #{self.id} - {self.customer.customer.username} - {self.vendor.business_name}"

class BookingItem(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(ShopItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.item.product_name}"

    class Meta:
        verbose_name = "Booking Item"
        verbose_name_plural = "Booking Items"

class Services(models.Model):
    vendor = models.ForeignKey("ServiceProvider", on_delete=models.CASCADE)  # Service provider reference
    service_name = models.CharField(max_length=255)  # Name of the service
    description = models.TextField(blank=True, null=True)  # Service details
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Service cost
    is_available = models.BooleanField(default=True)  # Availability

class Service_Based_Booking(models.Model):
    customer = models.ForeignKey(CustomerInfo, on_delete=models.CASCADE)
    vendor = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE)
    service = models.ForeignKey(Services, on_delete=models.CASCADE)
    
    service_date = models.DateField()  # Date of service
    service_time = models.TimeField()  # Time of service

    # Location details based on service type
    address = models.CharField(max_length=255, blank=True, null=True)  # For home services
    pickup_location = models.CharField(max_length=255, blank=True, null=True)  # For transport
    dropoff_location = models.CharField(max_length=255, blank=True, null=True)  # For transport
    
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Type of service
    service_type = models.CharField(
        max_length=50, 
        choices=[
            ("pick_up", "Pick Up"),
            ("home_delivery", "Home Delivery"),
            ("in_store", "In-Store Service"),
            ("home_service", "Home Service"),
            ("transport", "Transport Service")
        ]
    )
    
    # Additional field for transport (cab, auto)
    booking_time = models.DateTimeField(auto_now_add=True)  # auto timestamp
    complete_time = models.DateTimeField(null=True, blank=True)  # When service was completed

    booking_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=20,
        choices=[("Pending", "Pending"), ("Confirmed", "Confirmed"), ("Completed", "Completed"), ("Cancelled", "Cancelled")],
        default="Pending"
    )

    pickup_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    pickup_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    dropoff_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    dropoff_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    distance_km = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    # Payment fields
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('credit_card', 'Credit Card'),
            ('debit_card', 'Debit Card'),
            ('upi', 'UPI'),
            ('net_banking', 'Net Banking'),
            ('wallet', 'Digital Wallet'),
            ('cod', 'Cash on Delivery')
        ],
        default='cod'
    )
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('refunded', 'Refunded')
        ],
        default='pending'
    )

class Notification(models.Model):
    ACTION_TYPES = [
        ('booking', 'Booking'),
        ('status_update', 'Status Update'),
        ('payment', 'Payment'),
        ('general', 'General')
    ]
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="sent_notifications")
    recipient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="received_notifications")
    message = models.TextField()
    timestamp = models.DateTimeField(default=now)
    is_read = models.BooleanField(default=False)
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES, default='general')
    is_responded = models.BooleanField(default=False)




class KNNRecommendation(models.Model):
    customer = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE)
    distance_km = models.DecimalField(max_digits=5, decimal_places=2)
    rating_score = models.DecimalField(max_digits=3, decimal_places=2)



class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded')
    ]

    PAYMENT_METHOD_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('upi', 'UPI')
    ]

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, null=True, blank=True)
    service_booking = models.ForeignKey(Service_Based_Booking, on_delete=models.CASCADE, null=True, blank=True)
    customer = models.ForeignKey(CustomerInfo, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, default='cod')
    status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

  