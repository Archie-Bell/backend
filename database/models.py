from django.db import models

# Create your models here.
class MissingPerson(models.Model):
    name = models.CharField(max_length=255)
    age = models.PositiveIntegerField()
    last_location_seen = models.CharField(max_length=255)
    last_date_time_seen = models.DateTimeField()
    additional_info = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='images/')

    class Meta:
        db_table = "MissingPersonsList"
        verbose_name = "Missing Person"
        verbose_name_plural = "Missing People"