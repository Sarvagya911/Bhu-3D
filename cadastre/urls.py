from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('explorer-3d/', views.explorer_3d_view, name='explorer_3d'),
    path('ulpin-generator/', views.ulpin_generator_view, name='ulpin_generator'),
    path('certificate/<str:ulpin_3d>/', views.bhu_aadhaar_card_view, name='bhu_aadhaar_card'),
    path('spatial-audit/', views.spatial_audit_view, name='spatial_audit'),
    path('search/', views.public_search_view, name='public_search'),
    path('parcel-builder/', views.parcel_builder_view, name='parcel_builder'),
    path('officer-login/', views.officer_login_view, name='officer_login'),
    path('officer-logout/', views.officer_logout_view, name='officer_logout'),
    
    # API endpoints
    path('api/parcels/<int:parcel_id>/3d-data/', views.api_parcel_3d_data, name='api_parcel_3d_data'),
    path('api/generate-ulpin-3d/', views.api_generate_ulpin_3d, name='api_generate_ulpin_3d'),
    path('api/verify-ulpin/<str:ulpin_3d>/', views.api_verify_ulpin, name='api_verify_ulpin'),
]
