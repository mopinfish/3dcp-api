from django.db import models
from django.contrib.auth.models import User, Group

# Create your models here.

class pub_message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    project = models.ForeignKey(Group, on_delete=models.CASCADE)
    send_message = models.CharField(max_length=1000)
    send_document = models.FileField(upload_to='documents/')
    send_date = models.DateTimeField(auto_now_add=True)