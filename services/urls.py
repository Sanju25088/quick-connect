from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [ 
    path("", views.landing_page, name='landing_page'),  # Landing page as home page
    path("pages_login/", views.pages_login, name='pages_login'),

    path("admin_register/", views.admin_register, name='admin_register'),
    path("admin_dashboard/", views.admin_dashboard, name='admin_dashboard'),
    path("new_vendor/", views.new_vendor, name='new_vendor'),
    path("new_customer/", views.new_customer, name='new_customer'),
    path('all_booking_history', views.all_booking_history, name='all_booking_history'),

    path("customer_register/", views.customer_register, name='customer_register'),
    path("customer_dashboard/", views.customer_dashboard, name='customer_dashboard'),
    path("customerinfo/", views.customerinfo, name='customerinfo'),
    path("customer_notifications/", views.customer_notifications, name='customer_notifications'),
    path("book_items/<int:vendor_id>/", views.book_items, name="book_item"),
    path("book-service/<int:vendor_id>/", views.book_service, name="book_service"),
    path('notifications/mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),

    path("customer/customer_booking_history/", views.customer_booking_history, name="customer_booking_history"),

    path("vendor_register/", views.vendor_register, name='vendor_register'),
    path("vendor_dashboard/", views.vendor_dashboard, name='vendor_dashboard'),
    path("vendor_notifications/", views.vendor_notifications, name='vendor_notifications'),
    path("add_business_info/", views.add_business_info, name="add_business_info"),
    path("vendor/booking_history/", views.booking_history, name="booking_history"),

    path("forgot_password/", views.forgot_password, name="forgot_password"),
    path("verify_otp/", views.verify_otp, name="verify_otp"),
    path('reset_password/<str:email>/', views.reset_password, name='reset_password'),

    path("no_access/", views.no_access, name="no_access"),
    path("logout/", views.custom_logout, name="logout"),
    path("search/", views.search_vendors_services, name="search"),
    path("check-new-notifications/", views.check_new_notifications, name="check_new_notifications"),
    
    # Payment URLs
    path("payment-success/", views.payment_success, name="payment_success"),
    path('update_payment_status/', views.update_payment_status, name='update_payment_status'),
    path('update_qr_code/', views.update_qr_code, name='update_qr_code'),
    path('place_order/', views.place_order, name='place_order'),
    path('update_order_status/', views.update_order_status, name='update_order_status'),

    path('update_availability/<int:vendor_id>/', views.update_availability, name='update_availability'),
    path('update-service-availability/<int:service_id>/', views.update_service_availability, name='update_service_availability'),
]

# Add media file handling in development mode
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
