from django.db import models
from accounts.models import CustomUser

class InsuranceClaim(models.Model):
 

    CLAIM_TYPE_CHOICES = [
        # Auto Claim
        ('Car Theft', 'Car Theft'),
        ('Collision (Accident)', 'Collision (Accident)'),
        ('Injury After Accident', 'Injury After Accident'),
        ('Vandalism / Damage While Parked', 'Vandalism / Damage While Parked'),
        # Home Claim
        ('House Fire', 'House Fire'),
        ('Basement Flood / Water Damage', 'Basement Flood / Water Damage'),
        ('Roof Damage / Storm', 'Roof Damage / Storm'),
        ('Vandalism / Forced Entry', 'Vandalism / Forced Entry'),
        ('Broken Appliances / Home Systems', 'Broken Appliances / Home Systems'),
        # Other Property
        ('Personal Contents Stolen', 'Personal Contents Stolen'),
        ('Storage Unit Theft', 'Storage Unit Theft'),
        ('Garage / Shed Damage', 'Garage / Shed Damage'),
    ]

    COUNTRY_CHOICES = [
        ('United States', 'United States'),
        ('Canada', 'Canada'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    type_of_claim = models.CharField(max_length=100, choices=CLAIM_TYPE_CHOICES)
    description = models.TextField()
    date_of_incident = models.DateField()
    country_of_incident = models.CharField(max_length=100, choices=COUNTRY_CHOICES)
    city_of_incident = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.type_of_claim}"
    


class Template(models.Model):
    CATEGORY_CHOICES = [
        ('Submission', 'Submission'),
        ('Follow-Up', 'Follow-Up'),
        ('Negotiation', 'Negotiation'),
        ('Closure', 'Closure'),
        ('Policy', 'Policy'),
    ]

    title = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    last_updated = models.CharField(max_length=20)
    preview = models.TextField()

    subject = models.CharField(max_length=255)
    body = models.TextField()

    def __str__(self):
        return self.title