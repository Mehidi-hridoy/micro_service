from django.db import models
from django.conf import settings

class Shipment(models.Model):
    """Shipping management model"""
    SHIPMENT_STATUS = [
        ('pending', 'Pending'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    shipment_number = models.CharField(max_length=50, unique=True)
    tenant_id = models.IntegerField()  # Store tenant reference
    sender_name = models.CharField(max_length=100)
    sender_address = models.TextField()
    receiver_name = models.CharField(max_length=100)
    receiver_address = models.TextField()
    weight = models.DecimalField(max_digits=10, decimal_places=2)
    dimensions = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, choices=SHIPMENT_STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    estimated_delivery = models.DateField(null=True, blank=True)
    actual_delivery = models.DateField(null=True, blank=True)
    
    class Meta:
        db_table = 'shipments'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.shipment_number} - {self.status}"

class TrackingEvent(models.Model):
    """Shipment tracking events"""
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='tracking_events')
    event_type = models.CharField(max_length=50)
    location = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    event_time = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'tracking_events'
        ordering = ['-event_time']
    
    def __str__(self):
        return f"{self.event_type} at {self.location}"

class ShippingRate(models.Model):
    """Shipping rates per tenant"""
    tenant_id = models.IntegerField()
    from_location = models.CharField(max_length=100)
    to_location = models.CharField(max_length=100)
    weight_min = models.DecimalField(max_digits=10, decimal_places=2)
    weight_max = models.DecimalField(max_digits=10, decimal_places=2)
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    
    class Meta:
        db_table = 'shipping_rates'
        unique_together = ['tenant_id', 'from_location', 'to_location', 'weight_min', 'weight_max']


        