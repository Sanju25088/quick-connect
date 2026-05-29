# Quick Connect

A Django-based service marketplace application connecting customers with service providers.

## Features

- **Customer Management**: Registration, dashboard, booking history
- **Vendor Management**: Business profile, service listings, booking management
- **Service Booking**: Browse, filter, and book services
- **Payment Integration**: Secure payment processing
- **Notifications**: Real-time notifications for customers and vendors
- **Authentication**: Secure user authentication and authorization

## Tech Stack

- **Backend**: Django 5.1.7
- **Frontend**: HTML, CSS, JavaScript (Django Templates)
- **Database**: MySQL
- **Deployment**: Vercel
- **Python Version**: 3.12

## Project Structure

```
quick_connect/
├── quick_connect/          # Main Django project settings
│   ├── settings.py         # Production settings (environment-aware)
│   ├── urls.py             # Main URL configuration
│   ├── wsgi.py             # WSGI application for production
│   └── asgi.py             # ASGI configuration
├── services/               # Main Django app
│   ├── models.py           # Database models
│   ├── views.py            # View logic
│   ├── urls.py             # App-specific URLs
│   ├── forms.py            # Django forms
│   ├── migrations/         # Database migrations
│   └── templates/          # HTML templates
├── templates/              # Project-wide templates
├── media/                  # User-uploaded media files
├── staticfiles/            # Collected static files (production)
├── manage.py               # Django management script
├── requirements.txt        # Python dependencies
├── vercel.json             # Vercel deployment configuration
├── build_files.sh          # Build script for Vercel
└── .gitignore              # Git ignore rules
```

## Installation & Setup

### Prerequisites
- Python 3.12+
- pip
- virtual environment

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/quick-connect.git
   cd quick-connect
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # On Windows: .\venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your settings
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Collect static files**
   ```bash
   python manage.py collectstatic --noinput
   ```

8. **Run development server**
   ```bash
   python manage.py runserver
   ```

   Visit http://localhost:8000

## Environment Variables

Create a `.env` file in the project root:

```
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (MySQL)
DATABASE_URL=mysql://user:password@localhost:3306/quick_connect

# Email (Gmail)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Security
CSRF_TRUSTED_ORIGINS=http://localhost:8000
```

## Deployment

### Deploy to Vercel

1. **Push to GitHub**
   ```bash
   git add -A
   git commit -m "Ready for Vercel deployment"
   git push origin main
   ```

2. **Link to Vercel**
   ```bash
   vercel login
   vercel link
   ```

3. **Set environment variables on Vercel**
   ```bash
   vercel env add SECRET_KEY
   vercel env add DEBUG false
   vercel env add DJANGO_ALLOWED_HOSTS quick-connect-phi.vercel.app
   vercel env add DATABASE_URL mysql://...
   ```

4. **Deploy**
   ```bash
   vercel deploy --prod
   ```

## Admin Panel

Access the Django admin panel at `/admin/` after deployment.

## API Endpoints

### Authentication
- `POST /pages_login/` - User login
- `POST /logout/` - User logout
- `POST /forgot_password/` - Initiate password reset
- `POST /verify_otp/` - Verify OTP
- `POST /reset_password/` - Reset password

### Customer Endpoints
- `GET /customer_dashboard/` - Customer dashboard
- `GET /customer_register/` - Customer registration
- `GET /book_items/<vendor_id>/` - Book items from vendor
- `POST /place_order/` - Place order

### Vendor Endpoints
- `GET /vendor_dashboard/` - Vendor dashboard
- `GET /vendor_register/` - Vendor registration
- `GET /booking_history/` - Vendor booking history

### Payment
- `POST /update_payment_status/` - Update payment status
- `POST /update_qr_code/` - Update payment QR code
- `POST /update_order_status/` - Update order status

## Common Issues & Solutions

### 400 Bad Request Error
- Ensure `ALLOWED_HOSTS` includes your domain
- Check `CSRF_TRUSTED_ORIGINS` configuration
- Verify `SECRET_KEY` is set in environment variables

### 404 Not Found Error
- Check URL routing in `urls.py`
- Verify templates folder path in settings
- Ensure all required views exist

### Static Files Not Loading
- Run `python manage.py collectstatic --noinput`
- Check `STATIC_URL` and `STATIC_ROOT` in settings
- Verify WhiteNoise middleware is installed

### Database Connection Failed
- Verify `DATABASE_URL` format: `mysql://user:password@host:port/dbname`
- Check MySQL server is running
- Ensure `PyMySQL` is installed

## Support & Contribution

For issues or contributions, please open a GitHub issue or pull request.

## License

This project is licensed under the MIT License.

## Author

Quick Connect Team

---

**Version**: 1.0.0  
**Last Updated**: May 29, 2026
