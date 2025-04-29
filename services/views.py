from datetime import timezone
from decimal import Decimal
from random import randint
import random
import time
from django.shortcuts import render, redirect
from django.shortcuts import render,redirect,get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import localdate  
from django.utils import timezone
from django.utils.timezone import now, timedelta
from .models import (CustomUser, KNNRecommendation, Notification, 
                     Service_Based_Booking, ServiceProvider, 
                     CustomerInfo,ShopItem, Services,Booking,Payment, BookingItem)
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.http import HttpResponse, JsonResponse
from django.template import loader
import json
import math
from decimal import Decimal 
import numpy as np
from sklearn.neighbors import BallTree
from geopy.geocoders import Nominatim
import re
from django.db import transaction
from django.db.models import Sum, F

def landing_page(request):
    """View for the landing page"""
    return render(request, 'landing_page.html')




def all_booking_history(request):
    grocery_bookings = Booking.objects.select_related('customer', 'vendor').prefetch_related('items').order_by('-booking_time')
    service_bookings = Service_Based_Booking.objects.select_related('customer', 'vendor', 'service').order_by('-booking_time')

    context = {
        'grocery_bookings': grocery_bookings,
        'service_bookings': service_bookings
    }

    return render(request, 'all_booking_history.html', context)

@login_required
def admin_dashboard(request):
    user = request.user

    if not user.is_superuser:
        return redirect('no_access')

    # Count users based on user type
    total_customers = CustomUser.objects.filter(user_type="customer").count()
    total_vendors = CustomUser.objects.filter(user_type="vendor").count()
    customers_registered_today = CustomUser.objects.filter(
        user_type="customer", date_joined__date=localdate()
    ).count()

    # Booking counts
    grocery_booking_count = Booking.objects.count()
    service_booking_count = Service_Based_Booking.objects.filter(vendor__user__category="service_based").count()
    transport_booking_count = Service_Based_Booking.objects.filter(vendor__user__category="ride_service").count()
    total_bookings = grocery_booking_count + service_booking_count + transport_booking_count

    # Reviews

    # Revenue data for the last 7 days
    today = timezone.now().date()
    revenue_dates = []
    revenue_data = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        revenue_dates.append(date.strftime('%Y-%m-%d'))
        
        # Calculate daily revenue from both booking types
        daily_grocery_revenue = Booking.objects.filter(
            booking_time__date=date
        ).aggregate(total=Sum('total_price'))['total'] or 0
        
        daily_service_revenue = Service_Based_Booking.objects.filter(
            booking_date__date=date
        ).aggregate(total=Sum('total_price'))['total'] or 0
        
        total_daily_revenue = float(daily_grocery_revenue) + float(daily_service_revenue)
        revenue_data.append(total_daily_revenue)

    # Booking type distribution
    booking_type_data = [service_booking_count, grocery_booking_count , transport_booking_count]

    # Booking status distribution
    booking_status_labels = ['Pending', 'Confirmed', 'Completed', 'Cancelled']
    booking_status_data = [
        Booking.objects.filter(status='Pending').count() + 
        Service_Based_Booking.objects.filter(status='Pending').count(),
        Booking.objects.filter(status='Confirmed').count() + 
        Service_Based_Booking.objects.filter(status='Confirmed').count(),
        Booking.objects.filter(status='Delivered').count() + 
        Service_Based_Booking.objects.filter(status='Completed').count(),
        Booking.objects.filter(status='Cancelled').count() + 
        Service_Based_Booking.objects.filter(status='Cancelled').count()
    ]

    # Top performing vendors (by revenue)
    vendors = ServiceProvider.objects.all()
    vendor_names = []
    vendor_revenue = []
    
    for vendor in vendors:
        vendor_names.append(vendor.business_name)
        vendor_grocery_revenue = Booking.objects.filter(
            vendor=vendor
        ).aggregate(total=Sum('total_price'))['total'] or 0
        
        vendor_service_revenue = Service_Based_Booking.objects.filter(
            vendor=vendor
        ).aggregate(total=Sum('total_price'))['total'] or 0
        
        total_vendor_revenue = float(vendor_grocery_revenue) + float(vendor_service_revenue)
        vendor_revenue.append(total_vendor_revenue)

    context = {
        'user': user,
        'total_customers': total_customers,
        'total_vendors': total_vendors,
        'customers_registered_today': customers_registered_today,
        'grocery_booking_count': grocery_booking_count,
        'service_booking_count': service_booking_count,
        'transport_booking_count': transport_booking_count,
        'total_bookings': total_bookings,
        'revenue_dates': json.dumps(revenue_dates),
        'revenue_data': json.dumps(revenue_data),
        'booking_type_data': json.dumps(booking_type_data),
        'booking_status_labels': json.dumps(booking_status_labels),
        'booking_status_data': json.dumps(booking_status_data),
        'vendor_names': json.dumps(vendor_names),
        'vendor_revenue': json.dumps(vendor_revenue)
    }

    return render(request, 'user_index.html', context)




# login page
def pages_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        print("data",username,password)
        user  = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if user.user_type == 'admin':
                return redirect('admin_dashboard')
            if user.user_type == 'staff':
                return redirect('staff_dashboard')
            if user.user_type == 'customer':
                return redirect('customer_dashboard')
            if user.user_type == 'vendor':
                return redirect('vendor_dashboard')
        else:
            context = {'error_message': 'Invalid username or password'}
            return render(request, 'login.html',context)
    return render(request,'login.html')

#pages login


# Registration pages below
def admin_register(request):
    if request.method == "POST":   
        username = request.POST["username"]
        first_name = request.POST["first_name"]
        last_name = request.POST["last_name"]
        email = request.POST["email"]
        password = request.POST["password"]
        confirm_password = request.POST["confirm_password"]
        profile_image = request.FILES.get("image")  

        # Email validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            messages.error(request, "Please enter a valid email address!")
            return render(request, "admin_register.html")

        # Password validation
        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long!")
            return render(request, "admin_register.html")
        if not re.search(r'[A-Z]', password):
            messages.error(request, "Password must contain at least one uppercase letter!")
            return render(request, "admin_register.html")
        if not re.search(r'[a-z]', password):
            messages.error(request, "Password must contain at least one lowercase letter!")
            return render(request, "admin_register.html")
        if not re.search(r'[0-9]', password):
            messages.error(request, "Password must contain at least one number!")
            return render(request, "admin_register.html")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            messages.error(request, "Password must contain at least one special character!")
            return render(request, "admin_register.html")

     

        # Check if passwords match
        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return render(request, "admin_register.html")

        # Check if username already exists
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already taken!")
            return render(request, "admin_register.html")

        # Check if email already exists
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email already registered!")
            return render(request, "admin_register.html")

        # Check if phone number already exists
        
        # Create a new user
        user = CustomUser.objects.create_user(
            username=username, 
            first_name=first_name,
            last_name=last_name, 
            email=email, 
            password=password,
        )

        if profile_image:
            user.profile_image = profile_image
            user.save()

        messages.success(request, "Successfully registered! Click here to log in.")
        return redirect("pages_login")

    return render(request, "admin_register.html")



def customer_register(request):
    if request.method == "POST":   
        username = request.POST["username"]
        first_name = request.POST["first_name"]
        last_name = request.POST["last_name"]
        email = request.POST["email"]
        password = request.POST["password"]
        confirm_password = request.POST["confirm_password"]
        profile_image = request.FILES.get("image")  

      
          

        # Email validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            messages.error(request, "Invalid email format! Please enter a valid email address (e.g., example@domain.com)")
            return render(request, "customer_register.html")

        # Password validation
        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long!")
            return render(request, "customer_register.html")
        if not re.search(r'[A-Z]', password):
            messages.error(request, "Password must contain at least one uppercase letter (A-Z)!")
            return render(request, "customer_register.html")
        if not re.search(r'[a-z]', password):
            messages.error(request, "Password must contain at least one lowercase letter (a-z)!")
            return render(request, "customer_register.html")
        if not re.search(r'[0-9]', password):
            messages.error(request, "Password must contain at least one number (0-9)!")
            return render(request, "customer_register.html")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            messages.error(request, "Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>)!")
            return render(request, "customer_register.html")


        # Check if passwords match
        if password != confirm_password:
            messages.error(request, "Passwords do not match! Please make sure both passwords are identical.")
            return render(request, "customer_register.html")

        # Check if username already exists
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' is already taken! Please choose a different username.")
            return render(request, "customer_register.html")

        # Check if email already exists
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, f"Email '{email}' is already registered! Please use a different email address.")
            return render(request, "customer_register.html")

        # Check if phone number already exists (only if provided)


        # Create a new user
        user = CustomUser.objects.create_user(
            username=username, 
            first_name=first_name,
            last_name=last_name, 
            email=email, 
            password=password,
            user_type='customer',
        )

        if profile_image:
            user.profile_image = profile_image
            user.save()

        messages.success(request, "Successfully registered! Click here to log in.")
        return redirect("pages_login")

    return render(request, "customer_register.html")

@login_required
def customer_dashboard(request):
    if request.user.user_type != "customer":
        return redirect("no_access")  

    try:
        customerinfo = CustomerInfo.objects.get(customer=request.user)
        created = False
    except CustomerInfo.DoesNotExist:
        customerinfo = CustomerInfo(
            customer=request.user,
            contact_no="Not provided",
            permanent_address="Not provided"
        )
        customerinfo.save()
        created = True

    if request.method == "POST":
        if request.POST.get("latitude") and request.POST.get("longitude") and not request.POST.get("phone_no"):
            customerinfo.latitude = request.POST.get("latitude")
            customerinfo.longitude = request.POST.get("longitude")
            if request.POST.get("location_name"):
                customerinfo.location_name = request.POST.get("location_name")
            customerinfo.save()
        else:
            if request.POST.get("phone_no"):
                customerinfo.contact_no = request.POST.get("phone_no")
            if request.POST.get("permanent_address"):
                customerinfo.permanent_address = request.POST.get("permanent_address")
            if request.POST.get("latitude"):
                customerinfo.latitude = request.POST.get("latitude")
            if request.POST.get("longitude"):
                customerinfo.longitude = request.POST.get("longitude")
            if request.POST.get("location_name"):
                customerinfo.location_name = request.POST.get("location_name")
            customerinfo.save()

    recent_bookings = Booking.objects.filter(
        customer=customerinfo
    ).exclude(status="Delivered").select_related('customer', 'vendor').prefetch_related('items').order_by('-booking_time')

    recent_service_bookings = Service_Based_Booking.objects.filter(
        customer=customerinfo
    ).exclude(status="Completed").order_by('-booking_time')
    
    # Find nearby vendors using KNN
    nearby_vendors = []
    recommended_vendors = []
    
    if customerinfo.latitude and customerinfo.longitude:
        # Get all vendors with valid coordinates
        all_vendors = ServiceProvider.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
        
        if all_vendors.exists():
            # Convert coordinates to radians for BallTree
            customer_coords = np.array([[float(customerinfo.latitude), float(customerinfo.longitude)]]) * np.pi / 180
            
            # Prepare vendor coordinates and create a mapping of indices to vendors
            vendor_coords = []
            vendor_mapping = []
            for vendor in all_vendors:
                vendor_coords.append([float(vendor.latitude), float(vendor.longitude)])
                vendor_mapping.append(vendor)
            
            if vendor_coords:
                vendor_coords = np.array(vendor_coords) * np.pi / 180
                
                # Create BallTree with Haversine metric
                tree = BallTree(vendor_coords, metric='haversine')
                
                # Find k nearest neighbors within 20km (convert to radians)
                max_distance_km = 20
                max_distance_rad = max_distance_km / 6371.0
                
                # Query the tree for neighbors within the distance
                distances, indices = tree.query(customer_coords, k=len(vendor_coords),
                                             return_distance=True,
                                             sort_results=True)
                
                # Convert distances to kilometers and filter results
                distances = distances[0] * 6371.0  # Convert to kilometers
                indices = indices[0]
                
                # Add vendors within the distance limit
                for idx, distance in zip(indices, distances):
                    if distance <= max_distance_km:
                        vendor = vendor_mapping[idx]
                        vendor.distance_km = round(distance, 2)
                        nearby_vendors.append(vendor)
                
                # Get KNN recommendations
                try:
                    # Get user's past interactions
                    user_bookings = Booking.objects.filter(customer=customerinfo)
                    user_services = Service_Based_Booking.objects.filter(customer=customerinfo)
                    
                    # Create user preferences vector
                    user_preferences = {
                        'grocery': len(user_bookings.filter(service_type='grocery')),
                        'service': len(user_services),
                        'pickup': len(user_bookings.filter(service_type='pickup')),
                        'delivery': len(user_bookings.filter(service_type='delivery'))
                    }
                    
                    # Normalize preferences
                    total_interactions = sum(user_preferences.values())
                    if total_interactions > 0:
                        user_preferences = {k: v/total_interactions for k, v in user_preferences.items()}
                    
                    # Get vendor features
                    vendor_features = []
                    for vendor in vendor_mapping:
                        features = {
                            'grocery': len(ShopItem.objects.filter(vendor=vendor)),
                            'service': len(Services.objects.filter(vendor=vendor)),
                            'pickup': 1 if 'pickup' in vendor.service_type.lower() else 0,
                            'delivery': 1 if 'delivery' in vendor.service_type.lower() else 0,
                            'rating': vendor.average_rating if hasattr(vendor, 'average_rating') else 0
                        }
                        vendor_features.append(features)
                    
                    # Convert to numpy arrays
                    user_vector = np.array([user_preferences.get(k, 0) for k in ['grocery', 'service', 'pickup', 'delivery']])
                    vendor_matrix = np.array([[f.get(k, 0) for k in ['grocery', 'service', 'pickup', 'delivery']] 
                                           for f in vendor_features])
                    
                    # Calculate cosine similarity
                    similarities = np.dot(vendor_matrix, user_vector) / (
                        np.linalg.norm(vendor_matrix, axis=1) * np.linalg.norm(user_vector)
                    )
                    
                    # Update KNN recommendations in database
                    update_knn_recommendations(request.user, vendor_mapping, similarities, distances)
                    
                    # Get top 5 recommendations
                    top_indices = np.argsort(similarities)[-5:][::-1]
                    
                    # Add recommended vendors
                    for idx in top_indices:
                        vendor = vendor_mapping[idx]
                        if vendor not in nearby_vendors:  # Avoid duplicates
                            vendor.recommendation_score = round(similarities[idx], 2)
                            recommended_vendors.append(vendor)
                            
                except Exception as e:
                    print(f"Error generating recommendations: {str(e)}")
    
    # Get notifications for the user
    notifications = Notification.objects.filter(recipient=request.user).order_by('-timestamp')[:5]
    unread_notifications_count = Notification.objects.filter(recipient=request.user, is_read=False).count()

  

    context = {
        "user": request.user,
        "customerinfo": customerinfo,
        "nearby_vendors": nearby_vendors,
        "recommended_vendors": recommended_vendors,
        "recent_bookings": recent_bookings,
        "recent_service_bookings": recent_service_bookings,
        "notifications": notifications,
        "unread_notifications_count": unread_notifications_count,
       
    }
    
    return render(request, "customer_index.html", context)




def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    if request.method == "POST":
        notification.is_read = True
        notification.save()
    return redirect('customer_dashboard') 

@login_required
def book_items(request, vendor_id):
    # Verify user is a customer
    if request.user.user_type != "customer":
        messages.error(request, "Only customers can book items.")
        return redirect("no_access")

    # Get vendor
    vendor = get_object_or_404(ServiceProvider, id=vendor_id)
    
    # Get or create customer info
    try:
        customer_info = CustomerInfo.objects.get(customer=request.user)
    except CustomerInfo.DoesNotExist:
        # Create customer info if it doesn't exist
        customer_info = CustomerInfo.objects.create(
            customer=request.user,
            contact_no="Not provided",
            permanent_address="Not provided"
        )
        messages.info(request, "Please complete your profile information.")

    if request.method == "POST":
        service_type = request.POST.get("service_type")
        if not service_type:
            messages.error(request, "Please select a service type.")
            return redirect("customer_dashboard")

        # Get delivery/pickup time if provided
        delivery_time = request.POST.get("delivery_time")
        pickup_time = request.POST.get("pickup_time")
        
        # Get payment method with enhanced UPI handling
        payment_method = request.POST.get("payment_method", "cod")
        if not payment_method:
            messages.error(request, "Please select a payment method.")
            return redirect("customer_dashboard")

        total_price = 0
        booking_items = []

        if request.POST.get("address"):
            address = request.POST.get("address")
        else:
            address = customer_info.location_name if customer_info.location_name else "Not provided"

        for key, value in request.POST.items():
            if key.startswith("quantity_"):  
                item_id = key.split("_")[1]  
                quantity = int(value)

                if quantity > 0:
                    item = get_object_or_404(ShopItem, id=item_id, vendor=vendor)

                    if quantity > item.quantity:
                        messages.error(request, f"Only {item.quantity} available for {item.product_name}.")
                        return redirect("customer_dashboard")

                    cost = item.price * quantity
                    total_price += cost

                    # Create booking item data
                    booking_items.append({
                        'item': item,
                        'quantity': quantity,
                        'price': item.price
                    })

                    # Reduce stock
                    item.quantity -= quantity
                    item.save()

        if booking_items:
            # Create the booking first
            booking = Booking.objects.create(
                customer=customer_info,
                vendor=vendor,
                total_price=total_price,
                service_type=service_type,
                delivery_time=delivery_time if service_type == 'home_delivery' else None,
                pickup_time=pickup_time if service_type == 'pick_up' else None,
                payment_method=payment_method,
                address = address,
                payment_status='completed' if payment_method == 'upi' else 'pending'
            )

            # Create booking items
            for item_data in booking_items:
                BookingItem.objects.create(
                    booking=booking,
                    item=item_data['item'],
                    quantity=item_data['quantity'],
                    price=item_data['price']
                )
                
            # Create payment record with enhanced UPI details
            payment = Payment.objects.create(
                booking=booking,
                customer=customer_info,
                amount=total_price,
                payment_method=payment_method,
                status='completed' if payment_method == 'upi' else 'pending',
                transaction_id=f"UPI{timezone.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}" if payment_method == 'upi' else None
            )

            # Send notification to vendor about the new booking with enhanced payment details
            message = f"New order received from {request.user.get_full_name() or request.user.username}. Total: ₹{total_price} ({service_type.capitalize()})"
            if service_type == 'home_delivery':
                message += f"\nDelivery Time: {delivery_time}"
            else:
                message += f"\nPickup Time: {pickup_time}"
            message += f"\nPayment Method: {payment_method.upper()}"
            if payment_method == 'upi':
                message += f"\nTransaction ID: {payment.transaction_id}"
                message += "\nPayment Status: Completed (UPI)"
            else:
                message += "\nPayment Status: Pending (Please update after receiving payment)"

            Notification.objects.create(
                sender=request.user,
                recipient=vendor.user,
                message=message,
                is_read=False,
                action_type='booking',
                is_responded=False
            )

            # Send payment confirmation to customer for UPI payments
            if payment_method == 'upi':
                customer_message = (
                    f"Your UPI payment of ₹{total_price:.2f} has been processed successfully.\n"
                    f"Transaction ID: {payment.transaction_id}\n"
                    f"Order ID: {booking.id}"
                )
                Notification.objects.create(
                    sender=vendor.user,
                    recipient=request.user,
                    message=customer_message,
                    is_read=False,
                    action_type='payment',
                    is_responded=False
                )

            messages.success(request, f"Booking successful! Total Amount: ₹{total_price} ({service_type.capitalize()})")
            return redirect("customer_dashboard")

    return redirect("customer_dashboard")



@login_required
def book_service(request, vendor_id):
    if request.method == "POST":
        vendor = get_object_or_404(ServiceProvider, id=vendor_id)
        service_id = request.POST.get("selected_service")
        service = get_object_or_404(Services, id=service_id)

        customer = request.user.customerinfo
        service_type = request.POST.get("service_type")
        service_date = request.POST.get("service_date")
        service_time = request.POST.get("service_time")
        payment_method = request.POST.get("payment_method", "cod")

   
        if request.POST.get("address"):
            address = request.POST.get("address")
        else:
            address = customer.location_name if customer.location_name else "Not provided"


        pickup_lat = customer.latitude
        pickup_lng = customer.longitude

        pickup_location = request.POST.get("pickup_location")
        dropoff_location = request.POST.get("dropoff_location")

        dropoff_lat = request.POST.get("dropoff_latitude")
        dropoff_lng = request.POST.get("dropoff_longitude")

        # Calculate distance if coordinates provided
        distance_km = None
        if all([pickup_lat, pickup_lng, dropoff_lat, dropoff_lng]):
            pickup_lat = float(pickup_lat)
            pickup_lng = float(pickup_lng)
            dropoff_lat = float(dropoff_lat)
            dropoff_lng = float(dropoff_lng)

            R = 6371  # Earth's radius in km
            dLat = math.radians(dropoff_lat - pickup_lat)
            dLon = math.radians(dropoff_lng - pickup_lng)
            a = math.sin(dLat/2)**2 + \
                math.cos(math.radians(pickup_lat)) * math.cos(math.radians(dropoff_lat)) * \
                math.sin(dLon/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            distance_km = round(R * c, 2)

        # Calculate price
        if distance_km:
            total_price = float(service.price) * distance_km
        else:
            total_price = float(service.price)

        # Create booking
        booking = Service_Based_Booking.objects.create(
            customer=customer,
            vendor=vendor,
            service=service,
            service_date=service_date,
            service_time=service_time,
            service_type=service_type,
            address=address,
            pickup_location=pickup_location,
            dropoff_location=dropoff_location,
            total_price=total_price,
            booking_date=timezone.now(),
            status="Pending",
            pickup_latitude=pickup_lat,
            pickup_longitude=pickup_lng,
            dropoff_latitude=dropoff_lat,
            dropoff_longitude=dropoff_lng,
            distance_km=distance_km,
            payment_method=payment_method,
            payment_status='completed' if payment_method == 'upi' else 'pending'
        )

        # Create payment record with enhanced UPI details
        payment = Payment.objects.create(
            service_booking=booking,
            customer=customer,
            amount=total_price,
            payment_method=payment_method,
            status='completed' if payment_method == 'upi' else 'pending',
            transaction_id=f"UPI{timezone.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}" if payment_method == 'upi' else None
        )

        # Notify vendor with enhanced payment details
        message = (
            f"New service booking from {request.user.get_full_name() or request.user.username}"
            f". Service: {service.service_name}, Date: {service_date}"
        )
        if vendor.category_type == 'ride_service' and distance_km:
            message += f"\nDistance: {distance_km:.2f} km, Price: ₹{total_price:.2f}"
        message += f"\nPayment Method: {payment_method.upper()}"
        if payment_method == 'upi':
            message += f"\nTransaction ID: {payment.transaction_id}"
            message += "\nPayment Status: Completed (UPI)"
        else:
            message += "\nPayment Status: Pending (Please update after receiving payment)"

        Notification.objects.create(
            sender=request.user,
            recipient=vendor.user,
            message=message,
            is_read=False,
            action_type='booking',
            is_responded=False
        )

        # Send payment confirmation to customer
        if payment_method == 'upi':
            customer_message = (
                f"Your UPI payment of ₹{total_price:.2f} has been processed successfully.\n"
                f"Transaction ID: {payment.transaction_id}\n"
                f"Booking ID: {booking.id}"
            )
            Notification.objects.create(
                sender=vendor.user,
                recipient=request.user,
                message=customer_message,
                is_read=False,
                action_type='payment',
                is_responded=False
            )

        messages.success(request, f"Service booking successful! Total Amount: ₹{total_price} (Payment Method: {payment_method.upper()})")
        return redirect("customer_dashboard")
    
    return redirect("customer_dashboard")


def get_coordinates(location):
    """Get coordinates for a location using OpenStreetMap"""
    try:
        # Use OpenStreetMap Nominatim API
        geolocator = Nominatim(user_agent="quick_connect")
        location_data = geolocator.geocode(location)
        if location_data:
            return {
                'lat': location_data.latitude,
                'lon': location_data.longitude
            }
    except Exception as e:
        print(f"Error getting coordinates: {str(e)}")
    return None

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points using Haversine formula"""
    R = 6371  # Earth's radius in kilometers
    
    # Convert coordinates to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Calculate differences
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    # Haversine formula
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    # Calculate distance
    distance = R * c
    return distance

def vendor_register(request):
    if request.method == "POST":   
        category = request.POST["category"]
        username = request.POST["username"]
        first_name = request.POST["first_name"]
        last_name = request.POST["last_name"]
        email = request.POST["email"]
        password = request.POST["password"]
        confirm_password = request.POST["confirm_password"]
        profile_image = request.FILES.get("image")  


        # Email validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            messages.error(request, "Please enter a valid email address!")
            return render(request, "vendor_register.html")

        # Password validation
        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long!")
            return render(request, "vendor_register.html")
        if not re.search(r'[A-Z]', password):
            messages.error(request, "Password must contain at least one uppercase letter!")
            return render(request, "vendor_register.html")
        if not re.search(r'[a-z]', password):
            messages.error(request, "Password must contain at least one lowercase letter!")
            return render(request, "vendor_register.html")
        if not re.search(r'[0-9]', password):
            messages.error(request, "Password must contain at least one number!")
            return render(request, "vendor_register.html")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            messages.error(request, "Password must contain at least one special character!")
            return render(request, "vendor_register.html")

    

        # Check if passwords match
        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return render(request, "vendor_register.html")

        # Check if username already exists
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already taken!")
            return render(request, "vendor_register.html")

        # Check if email already exists
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email already registered!")
            return render(request, "vendor_register.html")

     

        # Create a new user
        user = CustomUser.objects.create_user(
            category=category,
            username=username, 
            first_name=first_name,
            last_name=last_name, 
            email=email, 
            password=password,
            user_type='vendor',
        )

        if profile_image:
            user.profile_image = profile_image
            user.save()

        messages.success(request, "Successfully registered! Click here to log in.")
        return redirect("pages_login")

    return render(request, "vendor_register.html")





@login_required
def vendor_dashboard(request):
    if request.user.user_type != "vendor":
        return redirect("no_access")

    vendor = ServiceProvider.objects.filter(user=request.user).first()
    
    # If vendor profile doesn't exist, redirect to create profile
    if not vendor:
        messages.warning(request, "Please complete your vendor profile first.")
        return redirect("add_business_info")
       
    # Handle POST requests
    if request.method == "POST":
        
        # Add Shop Item
        if "add_item" in request.POST:
            product_name = request.POST.get("product_name")
            price = request.POST.get("price")
            quantity = request.POST.get("quantity")

            if product_name and price and quantity:
                ShopItem.objects.create(
                    vendor=vendor,
                    product_name=product_name,
                    price=price,
                    quantity=quantity
                )
                messages.success(request, "Product added successfully!")
                return redirect("vendor_dashboard")
                
        # Update Shop Item
        elif "update_item" in request.POST:
            item_id = request.POST.get("item_id")
            product_name = request.POST.get("product_name")
            price = request.POST.get("price")
            quantity = request.POST.get("quantity")
            
            if item_id and product_name and price and quantity:
                item = ShopItem.objects.filter(id=item_id, vendor=vendor).first()
                if item:
                    item.product_name = product_name
                    item.price = Decimal(price)
                    item.quantity = int(quantity)
                    item.save()
                    messages.success(request, "Product updated successfully!")
                else:
                    messages.error(request, "Product not found.")
                return redirect("vendor_dashboard")

        # Delete Shop Item
        elif "delete_item" in request.POST:
            item_id = request.POST.get("item_id")
            ShopItem.objects.filter(id=item_id, vendor=vendor).delete()
            messages.success(request, "Product removed successfully!")
            return redirect("vendor_dashboard")

        # Add Service
        elif "add_service" in request.POST:
            service_name = request.POST.get("service_name")
            description = request.POST.get("description")
            price = request.POST.get("price")

            if service_name and price and description:
                Services.objects.create(
                    vendor=vendor,
                    service_name=service_name,
                    description=description,
                    price=price,
                    is_available=True,
                )
                # Update vendor availability status to Available when adding a new service
                vendor.availability_status = "Available"
                vendor.save()
                messages.success(request, "Service added successfully!")
                return redirect("vendor_dashboard")
                
        # Update Service
        elif "update_service" in request.POST:
            service_id = request.POST.get("service_id")
            service_name = request.POST.get("service_name")
            description = request.POST.get("description")
            price = request.POST.get("price")
            availability = request.POST.get("is_available") == "on"
            
            if service_id and service_name and price:
                service = Services.objects.filter(id=service_id, vendor=vendor).first()
                if service:
                    service.service_name = service_name
                    service.description = description
                    service.price = Decimal(price)
                    service.is_available = availability
                    service.save()
                    
                    # Update vendor availability status based on service availability
                    if availability:
                        # If service is available, set vendor to Available
                        vendor.availability_status = "Available"
                    else:
                        # Check if all services are unavailable
                        all_services_unavailable = not Services.objects.filter(
                            vendor=vendor,
                            is_available=True
                        ).exists()
                        
                        if all_services_unavailable:
                            vendor.availability_status = "Busy"
                    
                    vendor.save()
                    
                    messages.success(request, "Service updated successfully!")
                else:
                    messages.error(request, "Service not found.")
                return redirect("vendor_dashboard")

        # Delete Service
        elif "delete_service" in request.POST:
            service_id = request.POST.get("service_id")
            Services.objects.filter(id=service_id, vendor=vendor).delete()
            
            # Check if any services are still available
            has_available_services = Services.objects.filter(
                vendor=vendor,
                is_available=True
            ).exists()
            
            # Update vendor availability status
            if not has_available_services:
                vendor.availability_status = "Busy"
                vendor.save()
            
            messages.success(request, "Service removed successfully!")
            return redirect("vendor_dashboard")

        # Update Booking Status
        elif "update_booking_status" in request.POST:
            booking_id = request.POST.get("booking_id")
            new_status = request.POST.get("status")
            valid_statuses = ["Pending", "Confirmed", "Delivered", "Cancelled"]

            if new_status in valid_statuses:
                booking = Booking.objects.filter(id=booking_id, vendor=vendor).first()
                if booking:
                    booking.status = new_status
                    
                    # Update timing based on status
                    if new_status == "Delivered":
                        booking.delivery_time = timezone.now()
                    elif new_status == "Confirmed" and booking.service_type == "pick_up":
                        booking.pickup_time = timezone.now()
                    
                    booking.save()
                    
                    # Update vendor availability status based on booking status
                    if new_status == "Confirmed":
                        vendor.availability_status = "Busy"
                        vendor.save()
                    elif new_status == "Delivered":
                        vendor.availability_status = "Available"
                        vendor.save()
                    
                    # Send notification to customer about status update
                    message = f"Your order status has been updated to {new_status} by {vendor.business_name}"
                    Notification.objects.create(
                        sender=request.user,
                        recipient=booking.customer.customer,
                        message=message,
                        is_read=False,
                        action_type='booking',
                        is_responded=False
                    )
                    
                    messages.success(request, f"Booking status updated to {new_status}!")
                else:
                    messages.error(request, "Invalid booking or unauthorized access.")
            else:
                messages.error(request, "Invalid status update.")
            return redirect("vendor_dashboard")

        # Update Service Booking Status
        elif "update_service_booking_status" in request.POST:
            service_booking_id = request.POST.get("service_booking_id")
            new_status = request.POST.get("status")
            valid_statuses = ["Pending", "Confirmed", "Completed", "Cancelled"]

            if new_status in valid_statuses:
                service_booking = Service_Based_Booking.objects.filter(id=service_booking_id, vendor=vendor).first()
                if service_booking:
                    service_booking.status = new_status
                    
                    # Update timing based on status
                    if new_status == "Completed":
                        service_booking.complete_time = timezone.now()
                    
                    service_booking.save()
                    
                    # Update vendor availability status based on booking status
                    if new_status == "Confirmed":
                        vendor.availability_status = "Busy"
                        vendor.save()
                    elif new_status == "Completed":
                        vendor.availability_status = "Available"
                        vendor.save()
                    
                    # Send notification to customer about status update
                    message = f"Your service booking status has been updated to {new_status} by {vendor.business_name}"
                    Notification.objects.create(
                        sender=request.user,
                        recipient=service_booking.customer.customer,
                        message=message,
                        is_read=False,
                        action_type='booking',
                        is_responded=False
                    )
                    
                    messages.success(request, f"Service booking status updated to {new_status}!")
                else:
                    messages.error(request, "Invalid service booking or unauthorized access.")
            else:
                messages.error(request, "Invalid status update.")
            return redirect("vendor_dashboard")

        # Update Payment Status
        elif "update_payment_status" in request.POST:
            booking_id = request.POST.get("booking_id")
            new_payment_status = request.POST.get("payment_status")
            valid_payment_statuses = ["pending", "completed", "failed", "refunded"]

            if new_payment_status in valid_payment_statuses:
                # Try to get service booking first
                service_booking = Service_Based_Booking.objects.filter(id=booking_id, vendor=vendor).first()
                grocery_booking = Booking.objects.filter(id=booking_id, vendor=vendor).first()
                
                if service_booking or grocery_booking:
                    # Update payment status in the booking model
                    current_booking = service_booking if service_booking else grocery_booking
                    
                    if service_booking:
                        service_booking.payment_status = new_payment_status
                        service_booking.save()
                    else:
                        grocery_booking.payment_status = new_payment_status
                        grocery_booking.save()
                    
                    # Get or create payment record
                    try:
                        payment = Payment.objects.get(
                            service_booking=service_booking if service_booking else None,
                            booking=grocery_booking if grocery_booking else None
                        )
                    except Payment.DoesNotExist:
                        # Create new payment record if it doesn't exist
                        payment = Payment.objects.create(
                            service_booking=service_booking if service_booking else None,
                            booking=grocery_booking if grocery_booking else None,
                            customer=current_booking.customer,
                            amount=current_booking.total_price,
                            payment_method=current_booking.payment_method,
                            status=new_payment_status
                        )
                    
                    payment.status = new_payment_status
                    payment.save()
                    
                    # Send notification to customer
                    message = f"Payment status updated to {new_payment_status.title()} for your booking #{current_booking.id}"
                    Notification.objects.create(
                        sender=request.user,
                        recipient=current_booking.customer.customer,
                        message=message,
                        is_read=False,
                        action_type='payment',
                        is_responded=False
                    )
                    
                    messages.success(request, f"Payment status updated to {new_payment_status.title()}!")
                else:
                    messages.error(request, "Invalid booking or unauthorized access.")
            else:
                messages.error(request, "Invalid payment status.")
            
            return redirect("vendor_dashboard")

    # For GET requests, render the vendor dashboard template
    context = {
        'user': request.user,
        'vendor': vendor,
        'services': Services.objects.filter(vendor=vendor),
        'shop_items': ShopItem.objects.filter(vendor=vendor),
        'bookings': Booking.objects.filter(vendor=vendor).exclude(status__in=['Delivered', 'Completed']).order_by('-booking_time')[:5],
        'service_bookings': Service_Based_Booking.objects.filter(vendor=vendor).exclude(status__in=['Delivered', 'Completed']).order_by('-booking_date')[:5],
        'notifications': Notification.objects.filter(recipient=request.user).order_by('-timestamp')[:5],
        'unread_notifications_count': Notification.objects.filter(recipient=request.user, is_read=False).count()
    }
    
    return render(request, 'vendor_index.html', context)


@login_required
def booking_history(request):
    if request.user.user_type != "vendor":
        return redirect("no_access")

    # Get vendor profile of logged-in user
    vendor = ServiceProvider.objects.filter(user=request.user).first()

    if not vendor:
        messages.warning(request, "Your vendor profile is incomplete. Please update your details.")
        return redirect("vendor_dashboard")

    # Fetch grocery item bookings (if applicable)
    bookings = Booking.objects.filter(vendor=vendor).select_related("customer", "vendor").prefetch_related("items").order_by("-booking_time")

    # Fetch service-based bookings (if applicable)
    service_bookings = Service_Based_Booking.objects.filter(vendor=vendor).select_related("customer", "service").order_by("-booking_date")

    return render(request, "booking_history.html", {
        "bookings": bookings,
        "service_bookings": service_bookings,
        "vendor": vendor
    })


@login_required
def customer_booking_history(request):
    bookings = []
    service_bookings = []

    if hasattr(request.user, 'customerinfo'):
        customer = request.user.customerinfo
        # Grocery bookings
        bookings = Booking.objects.filter(customer=customer).order_by('-booking_time')
        
        # Service-based bookings
        service_bookings = Service_Based_Booking.objects.filter(customer=customer).order_by('-booking_time')

    context = {
        'bookings': bookings,
        'service_bookings': service_bookings
    }

    return render(request, 'cust_booking_his.html', context)




@login_required
def no_access(request):
    return render(request,'no_access.html')


def custom_logout(request):
    logout(request)
    return redirect("pages_login")








@login_required
def customer_notifications(request):
    if request.user.user_type != "customer":
        return redirect("no_access")

    notifications = Notification.objects.filter(recipient=request.user).order_by('-timestamp')

    context = {
        'notifications': notifications,
        'unread_count': Notification.objects.filter(recipient=request.user, is_read=False).count()
    }

    return render(request, 'customer_notifications.html', context)




@login_required
def add_business_info(request):
    if request.method == "POST":
        business_name = request.POST.get('business_name')
        latitude = request.POST.get('latitude')  
        longitude = request.POST.get('longitude')
        location_name = request.POST.get("location_name")
        service_type = request.POST.get("service_type")  
        contact_number = request.POST.get('contact_number')
        availability_status = request.POST.get('availability_status')
        category_type = request.POST.get('category_type')
        car_type = request.POST.get('car_type')
        working_hours = request.POST.get('working_hours')

        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except ValueError:
            latitude = None
            longitude = None

        # Create vendor with or without profile image
        vendor = ServiceProvider.objects.create(
            user=request.user,
            business_name=business_name,
            car_type=car_type,
            latitude=latitude,
            longitude=longitude,
            location_name=location_name,
            service_type=service_type,
            contact_number=contact_number,
            availability_status=availability_status,
            category_type=category_type,
            working_hours=working_hours,
        )

        return redirect('vendor_dashboard')

    return render(request, 'add_b_info.html')


@login_required
def customerinfo(request):
    # Ensure only customers can access this page
    if request.user.user_type != "customer":
        return redirect("no_access")  

    try:
        customerinfo = CustomerInfo.objects.get(customer=request.user)
    except CustomerInfo.DoesNotExist:
        customerinfo = None

    if request.method == "POST":
        # Retrieve form data
        contact_no = request.POST.get("phone_no")
        permanent_address = request.POST.get("permanent_address")
        latitude = request.POST.get("latitude")
        longitude = request.POST.get("longitude")
        location_name = request.POST.get("location_name")
        

        if customerinfo:
            # Update existing record
            customerinfo.contact_no = contact_no
            customerinfo.permanent_address = permanent_address
            customerinfo.latitude = latitude
            customerinfo.longitude = longitude
            customerinfo.location_name = location_name
           
        else:
            # Create new record
            customerinfo = CustomerInfo(
                customer=request.user,
                contact_no=contact_no,
                permanent_address=permanent_address,
                latitude=latitude,
                longitude=longitude,
                location_name=location_name,
               
            )

        customerinfo.save()
        return redirect("customer_dashboard")  # Redirect to dashboard after saving

    return render(request, "custom_info.html", {"customerinfo": customerinfo})


@login_required
def vendor_notifications(request):
    """Display and manage notifications for vendors"""
    if request.user.is_authenticated and request.user.user_type == "vendor":
        # Fetch notifications received by the vendor, newest first
        notifications = Notification.objects.filter(recipient=request.user).order_by('-timestamp')
        
        # Mark notifications as read if requested
        if request.method == 'POST' and 'mark_all_read' in request.POST:
            unread_notifications = notifications.filter(is_read=False)
            unread_notifications.update(is_read=True)
            messages.success(request, "All notifications marked as read.")
            return redirect('vendor_notifications')
        
        # Count unread notifications
        unread_count = notifications.filter(is_read=False).count()
        
        # Group notifications by type for easier viewing
        booking_notifications = notifications.filter(action_type='booking')
        status_notifications = notifications.filter(action_type='status_update')
        other_notifications = notifications.exclude(action_type__in=[ 'booking', 'status_update'])
        
        context = {
            'notifications': notifications,
            'booking_notifications': booking_notifications,
            'status_notifications': status_notifications,
            'other_notifications': other_notifications,
            'unread_count': unread_count
        }
        
        return render(request, 'vendor_notifications.html', context)
    else:
        return redirect('pages_login')
    


User = get_user_model()
def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "User with this email does not exist.")
            return redirect("forgot_password")

        if "otp" not in request.session:  # Generate OTP only if not already set
            otp = random.randint(100000, 999999)  # Generate 6-digit OTP
            request.session["otp"] = str(otp)  # Store OTP in session
            request.session["user_email"] = email  # Store user email
            request.session.set_expiry(300)  # Expire session in 5 minutes
 
            send_mail(
                "Your OTP Code",
                f"Your OTP for password reset is: {otp}",
                "retailapp123@gmail.com",
                [email],
                fail_silently=False,
            )

        messages.success(request, "OTP has been sent to your email.")
        return redirect("verify_otp")

    return render(request, "forgot_password.html")

def verify_otp(request):
    if request.method == "POST":
        entered_otp = request.POST.get("otp")
        session_otp = request.session.get("otp")
        user_email = request.session.get("user_email")

        if not session_otp or not user_email:
            messages.error(request, "Session expired. Try again.")
            return redirect("forgot_password")

        if str(entered_otp) == str(session_otp):  
            request.session["otp_verified"] = True  
            del request.session["otp"]  
            return redirect("reset_password", email=user_email)  # Pass email argument
        else:
            messages.error(request, "Invalid OTP. Please try again.")

    return render(request, "verify_otp.html")

def reset_password(request,email):
    if not request.session.get("otp_verified"):
        messages.error(request, "OTP verification required.")
        return redirect("verify_otp")  # Ensure user can't bypass OTP

    if request.method == "POST":
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if new_password == confirm_password:
            user_email = request.session.get("user_email")
            if not user_email:
                messages.error(request, "Session expired. Try again.")
                return redirect("forgot_password")

            user = User.objects.get(email=user_email)
            user.set_password(new_password)
            user.save()
            
            messages.success(request, "Password reset successful. Please log in.")
            return redirect("pages_login")  # Redirect to login page
        else:
            messages.error(request, "Passwords do not match.")

    return render(request, "reset_password.html")



@login_required
def new_customer(request):
    if request.method == "POST":   
        username = request.POST["username"]
        first_name = request.POST["first_name"]
        last_name = request.POST["last_name"]
        email = request.POST["email"]
        password = request.POST["password"]
        confirm_password = request.POST["confirm_password"]
        profile_image = request.FILES.get("image")  
        contact_no = request.POST.get("contact_no")

        # Phone number validation
        if contact_no:
            # Remove any non-digit characters
            contact_no = ''.join(filter(str.isdigit, contact_no))
            
            # Check if phone number is valid (10 digits for most countries)
            if len(contact_no) < 10 or len(contact_no) > 15:
                messages.error(request, "Phone number must be between 10 and 15 digits!")
                return render(request, "new_customer.html")
            
            # Check if phone number already exists
            if CustomUser.objects.filter(contact_no=contact_no).exists():
                messages.error(request, "Phone number already registered!")
                return render(request, "new_customer.html")

        # Email validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            messages.error(request, "Please enter a valid email address!")
            return render(request, "new_customer.html")

        # Password validation
        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long!")
            return render(request, "new_customer.html")
        if not re.search(r'[A-Z]', password):
            messages.error(request, "Password must contain at least one uppercase letter!")
            return render(request, "new_customer.html")
        if not re.search(r'[a-z]', password):
            messages.error(request, "Password must contain at least one lowercase letter!")
            return render(request, "new_customer.html")
        if not re.search(r'[0-9]', password):
            messages.error(request, "Password must contain at least one number!")
            return render(request, "new_customer.html")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            messages.error(request, "Password must contain at least one special character!")
            return render(request, "new_customer.html")

        # Check if passwords match
        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return render(request, "new_customer.html")

        # Check if username already exists
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' already taken!")
            return render(request, "new_customer.html")

        # Check if email already exists
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email already registered!")
            return render(request, "new_customer.html")

        # Create a new user
        user = CustomUser.objects.create_user(
            username=username, 
            first_name=first_name,
            last_name=last_name, 
            email=email, 
            password=password,
            user_type='customer',
            contact_no=contact_no
        )

        if profile_image:
            user.profile_image = profile_image
            user.save()

        messages.success(request, f"Customer '{username}' added successfully! Password: {password}")
        return redirect("admin_dashboard")

    return render(request, "new_customer.html")



@login_required
def new_vendor(request):
    if request.method == "POST":   
        category = request.POST["category"]
        username = request.POST["username"]
        first_name = request.POST["first_name"]
        last_name = request.POST["last_name"]
        email = request.POST["email"]
        password = request.POST["password"]
        confirm_password = request.POST["confirm_password"]
        profile_image = request.FILES.get("image")  
        contact_no = request.POST.get("contact_no")

        # Phone number validation
        if contact_no:
            # Remove any non-digit characters
            contact_no = ''.join(filter(str.isdigit, contact_no))
            
            # Check if phone number is valid (10 digits for most countries)
            if len(contact_no) < 10 or len(contact_no) > 15:
                messages.error(request, "Phone number must be between 10 and 15 digits!")
                return render(request, "new_vendor.html")
            
            # Check if phone number already exists
            if CustomUser.objects.filter(contact_no=contact_no).exists():
                messages.error(request, "Phone number already registered!")
                return render(request, "new_vendor.html")

        # Email validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            messages.error(request, "Please enter a valid email address!")
            return render(request, "new_vendor.html")

        # Password validation
        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long!")
            return render(request, "new_vendor.html")
        if not re.search(r'[A-Z]', password):
            messages.error(request, "Password must contain at least one uppercase letter!")
            return render(request, "new_vendor.html")
        if not re.search(r'[a-z]', password):
            messages.error(request, "Password must contain at least one lowercase letter!")
            return render(request, "new_vendor.html")
        if not re.search(r'[0-9]', password):
            messages.error(request, "Password must contain at least one number!")
            return render(request, "new_vendor.html")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            messages.error(request, "Password must contain at least one special character!")
            return render(request, "new_vendor.html")

        
        # Check if passwords match
        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return render(request, "new_vendor.html")

        # Check if username already exists
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' already taken!")
            return render(request, "new_vendor.html")

        # Check if email already exists
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email already registered!")
            return render(request, "new_vendor.html")

        # Create a new user
        user = CustomUser.objects.create_user(
            category=category,
            username=username, 
            first_name=first_name,
            last_name=last_name, 
            email=email, 
            password=password,
            user_type='vendor',
            contact_no=contact_no
        )

        if profile_image:
            user.profile_image = profile_image
            user.save()

        messages.success(request, f"Vendor '{username}' added successfully! Password: {password}")
        return redirect("admin_dashboard")

    return render(request, "new_vendor.html")


@login_required
def search_vendors_services(request):
    if request.user.user_type != "customer":
        return redirect("no_access")
    
    query = request.GET.get('query', '')
    results = {}
    
    if query:
        # Search for vendors
        vendors = ServiceProvider.objects.filter(
            business_name__icontains=query
        ) | ServiceProvider.objects.filter(
            category__icontains=query
        ) | ServiceProvider.objects.filter(
            category_type__icontains=query
        )
        
        # Search for services
        services = Services.objects.filter(
            service_name__icontains=query
        ) | Services.objects.filter(
            description__icontains=query
        )
        
        # Search for products
        products = ShopItem.objects.filter(
            product_name__icontains=query
        )
        
        # For each vendor, get their items and services
        vendor_details = []
        for vendor in vendors:
            vendor_items = ShopItem.objects.filter(vendor=vendor)
            vendor_services = Services.objects.filter(vendor=vendor)
            
            vendor_details.append({
                'vendor': vendor,
                'items': vendor_items,
                'services': vendor_services
            })
        
        # Add to results
        results = {
            'vendor_details': vendor_details,
            'services': services,
            'products': products,
            'query': query
        }
    
    return render(request, 'search_results.html', results)

@login_required
def check_new_notifications(request):
    """API endpoint to check for new notifications and return the count"""
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        # Don't mark as read here - only mark as read when the user views them
        return JsonResponse({
            'unread_count': unread_count,
            'should_refresh': False  # Set to True if you want to force a page refresh
        })
    return JsonResponse({'unread_count': 0, 'should_refresh': False})

def update_knn_recommendations(customer, vendor_mapping, similarities, distances):
    """
    Update KNN recommendations in the database for a customer
    """
    try:
        # Delete existing recommendations for this customer
        KNNRecommendation.objects.filter(customer=customer).delete()
        
        # Create new recommendations
        for idx, (vendor, similarity, distance) in enumerate(zip(vendor_mapping, similarities, distances)):
            KNNRecommendation.objects.create(
                customer=customer,
                provider=vendor,
                distance_km=round(distance, 2),
                rating_score=round(similarity, 2)
            )
            
        return True
    except Exception as e:
        print(f"Error updating KNN recommendations: {str(e)}")
        return False

@login_required
def update_availability(request, vendor_id):
    """Update vendor availability status via AJAX"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            vendor = get_object_or_404(ServiceProvider, id=vendor_id, user=request.user)
            data = json.loads(request.body)
            new_status = data.get('availability_status')
            
            if new_status in ['Available', 'Busy', 'Offline']:
                vendor.availability_status = new_status
                vendor.save()
                
                # Send notification to customers who have active bookings
                active_bookings = Booking.objects.filter(
                    vendor=vendor,
                    status__in=['Pending', 'Confirmed']
                ).select_related('customer__customer')
                
                for booking in active_bookings:
                    Notification.objects.create(
                        sender=request.user,
                        recipient=booking.customer.customer,
                        message=f"Vendor {vendor.business_name} has updated their availability status to {new_status}",
                        action_type='status_update',
                        is_read=False
                    )
                
                return JsonResponse({
                    'success': True,
                    'message': 'Availability status updated successfully'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid availability status'
                }, status=400)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
            
    return JsonResponse({
        'success': False,
        'message': 'Invalid request'
    }, status=400)

@login_required
def update_service_availability(request, service_id):
    """Update service availability status via AJAX"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            service = get_object_or_404(Services, id=service_id, vendor__user=request.user)
            data = json.loads(request.body)
            new_availability = data.get('is_available')
            
            if isinstance(new_availability, bool):
                service.is_available = new_availability
                service.save()
                
                # Update ServiceProvider's availability status based on service availability
                vendor = service.vendor
                if new_availability:
                    # If service is available, set vendor to Available
                    vendor.availability_status = 'Available'
                else:
                    # Check if all services are unavailable
                    all_services_unavailable = not Services.objects.filter(
                        vendor=vendor,
                        is_available=True
                    ).exists()
                    
                    if all_services_unavailable:
                        vendor.availability_status = 'Busy'
                
                vendor.save()
                
                # Send notification to customers with active bookings
                active_bookings = Booking.objects.filter(
                    vendor=vendor,
                    status__in=['Pending', 'Confirmed']
                ).select_related('customer__customer')
                
                for booking in active_bookings:
                    Notification.objects.create(
                        sender=request.user,
                        recipient=booking.customer.customer,
                        message=f"Vendor {vendor.business_name} has updated their availability status to {vendor.availability_status}",
                        action_type='status_update',
                        is_read=False
                    )
                
                return JsonResponse({
                    'success': True,
                    'message': 'Service availability updated successfully',
                    'vendor_status': vendor.availability_status
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid availability value'
                }, status=400)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
            
    return JsonResponse({
        'success': False,
        'message': 'Invalid request'
    }, status=400)

@login_required
def update_qr_code(request):
    if request.method == 'POST':
        try:
            # Get the vendor's ServiceProvider instance
            vendor = ServiceProvider.objects.get(user=request.user)
            
            # Get the uploaded QR code file
            upi_qr_code = request.FILES.get('upi_qr_code')
            
            if upi_qr_code:
                # Update the vendor's UPI QR code
                vendor.upi_qr_code = upi_qr_code
                vendor.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'QR code updated successfully',
                    'qr_code_url': vendor.upi_qr_code.url
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'No QR code file provided'
                })
                
        except ServiceProvider.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Vendor profile not found'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error updating QR code: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    })

@login_required
def update_payment_status(request):
    if request.user.user_type != "vendor":
        return redirect("no_access")

    if request.method == "POST":
        booking_id = request.POST.get("booking_id")
        new_payment_status = request.POST.get("payment_status")
        valid_payment_statuses = ["pending", "completed", "failed", "refunded"]

        if new_payment_status in valid_payment_statuses:
            vendor = ServiceProvider.objects.get(user=request.user)
            
            # Try to get service booking first
            service_booking = Service_Based_Booking.objects.filter(id=booking_id, vendor=vendor).first()
            grocery_booking = Booking.objects.filter(id=booking_id, vendor=vendor).first()
            
            if service_booking or grocery_booking:
                # Update payment status in the booking model
                current_booking = service_booking if service_booking else grocery_booking
                
                if service_booking:
                    service_booking.payment_status = new_payment_status
                    service_booking.save()
                else:
                    grocery_booking.payment_status = new_payment_status
                    grocery_booking.save()
                
                # Get or create payment record
                try:
                    payment = Payment.objects.get(
                        service_booking=service_booking if service_booking else None,
                        booking=grocery_booking if grocery_booking else None
                    )
                except Payment.DoesNotExist:
                    # Create new payment record if it doesn't exist
                    payment = Payment.objects.create(
                        service_booking=service_booking if service_booking else None,
                        booking=grocery_booking if grocery_booking else None,
                        customer=current_booking.customer,
                        amount=current_booking.total_price,
                        payment_method=current_booking.payment_method,
                        status=new_payment_status
                    )
                    
                payment.status = new_payment_status
                payment.save()
                
                # Send notification to customer
                message = f"Payment status updated to {new_payment_status.title()} for your booking #{current_booking.id}"
                Notification.objects.create(
                    sender=request.user,
                    recipient=current_booking.customer.customer,
                    message=message,
                    is_read=False,
                    action_type='payment',
                    is_responded=False
                )
                
                messages.success(request, f"Payment status updated to {new_payment_status.title()}!")
            else:
                messages.error(request, "Invalid booking or unauthorized access.")
        else:
            messages.error(request, "Invalid payment status.")
            
    return redirect("vendor_dashboard")

@login_required
def place_order(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'})
    
    try:
        data = json.loads(request.body)
        vendor_id = data.get('vendor_id')

        

        # Create order instantly with minimal data
        booking = Booking.objects.create(
            vendor_id=vendor_id,
            total_price=0,  # Will update in background
            service_type=data.get('service_type', 'home_delivery'),
            payment_method=data.get('payment_method', 'cod'),
            status='Pending'
        )
        
        # Return success immediately before processing anything else
        response = JsonResponse({
            'success': True,
            'order_id': booking.id,
        })

        # Process everything else after response is sent
        def process_order():
      
             
               
                # Create notifications
                Notification.objects.bulk_create([
                    Notification(
                        sender_id=request.user.id,
                        recipient_id=vendor_id,
                        message=f"Order #{booking.id} received",
                        action_type='order'
                    ),
                    Notification(
                        sender_id=vendor_id,
                        recipient_id=request.user.id,
                        message=f"Order #{booking.id} confirmed",
                        action_type='order'
                    )
                ])



        return response

    except Exception as e:
        print(f"Order creation error: {str(e)}")
        return JsonResponse({'success': False, 'message': 'Error placing order'})

@login_required
def update_order_status(request):
    """Update order status and store completion time for delivered orders"""


   
@login_required
def payment_success(request):
    try:
        # Get the most recent order for the customer
        order = Booking.objects.filter(
            customer__customer=request.user
        ).select_related(
            'customer', 'vendor'
        ).prefetch_related(
            'items__item'
        ).order_by('-booking_time').first()

        if not order:
            messages.error(request, "No order found")
            return redirect('customer_dashboard')

        # Get payment details if available
        payment = Payment.objects.filter(
            booking=order
        ).first()

        context = {
            'order': order,
            'payment': payment,
            'items': order.items.all(),
            'vendor': order.vendor
        }
        return render(request, 'payment_success.html', context)
        
    except Exception as e:
        messages.error(request, "Error retrieving order details")
        return redirect('customer_dashboard')