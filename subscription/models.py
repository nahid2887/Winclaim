from django.db import models
from decimal import Decimal

# Create your models here.
import shortuuid
from django.db import models
from accounts.models import CustomUser

def generate_random_id():
    return shortuuid.uuid()[:4]

class SubscriptionModel(models.Model):
    class PackageType(models.TextChoices):
        One_Time= 'One_Time', 'One_Time'
        MONTHLY = 'Monthly', 'Monthly'
        YEARLY = 'Yearly', 'Yearly'

    class PackageStatus(models.TextChoices):
        ACTIVE = 'Active', 'Active'
        POSTPONE = 'Postpone', 'Postpone'

    id = models.CharField(
        primary_key=True,
        max_length=10,
        default=generate_random_id,
        # editable=False
    )
    package_type = models.CharField(
        max_length=10,
        choices=PackageType.choices,
        default=PackageType.One_Time,
    )
    package_status = models.CharField(
        max_length=10,
        choices=PackageStatus.choices,
        default=PackageStatus.POSTPONE
    )
    package_amount = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"Type: {self.package_type} - Status: {self.package_status}"
    

class UserSubscriptionModel(models.Model):
    class PackageType(models.TextChoices):
        One_Time = 'One_Time', 'One_Time'
        MONTHLY = 'Monthly', 'Monthly'
        YEARLY = 'Yearly', 'Yearly'

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='package')  # Fixed typo
    package_type = models.CharField(
        max_length=10,
        choices=PackageType.choices,
        default=PackageType.One_Time,
    )
    is_active = models.BooleanField(default=False)
    package_start_date = models.DateField(null=True, blank=True)
    package_end_date = models.DateField(null=True, blank=True)
    package_amount = models.PositiveIntegerField(default=0)
    

    def __str__(self):
        return f"{self.user} - package type: {self.package_type}"
    
    @property
    def is_active_status(self):
        """
        Returns True if the subscription is active, False otherwise.
        """
        return self.is_active
    
class Total_revenue(models.Model):
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # USD
    

    @property
    def total_revenue_cad(self):
         return round(self.total_revenue * Decimal('1.37'), 2)

    def __str__(self):
        return f"{self.total_revenue} USD / {self.total_revenue_cad} CAD"