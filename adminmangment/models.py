from django.db import models
from accounts.models import CustomUser  # or use get_user_model()

class TermsaAndPolicy(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_terms', blank=True)
    updated_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='updated_terms', blank=True)

    def __str__(self):
        return self.title
    


class TermsaAndcondition(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_conditions', blank=True)
    updated_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='updated_conditions', blank=True)

    def __str__(self):
        return self.title