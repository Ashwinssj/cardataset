from django.db import models
from django.contrib.auth.models import User

class ObdMetric(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    driver_behavior = models.CharField(max_length=50)
    car_health = models.CharField(max_length=50)
    engine_rpm = models.FloatField(null=True, blank=True)
    vehicle_speed = models.FloatField(null=True, blank=True)
    throttle = models.FloatField(null=True, blank=True)
    engine_load = models.FloatField(null=True, blank=True)
    coolant_temperature = models.FloatField(null=True, blank=True)
    long_term_fuel_trim_bank_1 = models.FloatField(null=True, blank=True)
    short_term_fuel_trim_bank_1 = models.FloatField(null=True, blank=True)
    intake_manifold_pressure = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = 'obd_metrics'
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.user.username} - {self.timestamp}"
