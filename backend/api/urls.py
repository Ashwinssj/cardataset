from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('upload/', views.upload_file, name='upload_file'),
    path('summary/', views.get_summary, name='summary'),
    path('averages/', views.get_averages, name='averages'),
    path('car_health/', views.get_car_health_over_time, name='car_health'),
    path('driver_behavior/', views.get_driver_behavior_over_time, name='driver_behavior'),
    path('anomalies/', views.get_anomalies, name='anomalies'),
    path('clear/', views.clear_data, name='clear'),
    path('dates/', views.get_available_dates, name='dates'),
]
