from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid

class Shipment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    SHIPMENT_TYPE = [
        ('document', 'Document'),
        ('parcel', 'Parcel'),
        ('freight', 'Freight'),
    ]
    
    shipment_id = models.CharField(max_length=50, unique=True)
    tenant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shipments')
    tracking_number = models.CharField(max_length=100, unique=True)
    shipment_type = models.CharField(max_length=20, choices=SHIPMENT_TYPE, default='parcel')
    description = models.TextField()
    dimensions = models.CharField(max_length=255, blank=True)
    weight = models.DecimalField(max_digits=10, decimal_places=2)
    pickup_address = models.TextField()
    delivery_address = models.TextField()
    pickup_contact = models.CharField(max_length=100)
    delivery_contact = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    current_location = models.CharField(max_length=200, blank=True)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pickup_date = models.DateTimeField(null=True, blank=True)
    estimated_delivery = models.DateTimeField(null=True, blank=True)
    actual_delivery = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'shipments'
    
    def save(self, *args, **kwargs):
        if not self.shipment_id:
            self.shipment_id = f"SH{timezone.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"
        if not self.tracking_number:
            self.tracking_number = f"TRK{uuid.uuid4().hex[:12].upper()}"
        self.total_amount = self.shipping_cost + self.tax_amount
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.shipment_id} - {self.status}"

class TrackingEvent(models.Model):
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='tracking_events')
    event_type = models.CharField(max_length=50)
    description = models.TextField()
    location = models.CharField(max_length=200)
    remarks = models.TextField(blank=True)
    event_time = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'tracking_events'
    
    def __str__(self):
        return f"{self.shipment.shipment_id} - {self.event_type}"

class TokenShift(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='token_shifts')
    original_token = models.TextField()
    shifted_token = models.TextField()
    source_service = models.CharField(max_length=50)
    target_service = models.CharField(max_length=50)
    shift_reason = models.CharField(max_length=200, blank=True)
    token_type = models.CharField(max_length=20, default='access')
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    shifted_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    usage_count = models.IntegerField(default=0)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        db_table = 'token_shifts'
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def __str__(self):
        return f"{self.user.username} - {self.source_service} → {self.target_service}"
    
    