"""
Django settings for quiz_scheduling project.

Generated by 'django-admin startproject' using Django 5.0.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

from pathlib import Path
import os


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-es*!caedb=hbit^s11o(h6anu7ra_r89mic*u7u+p7#x7d+v2&"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '10.0.2.2']

import requests

def get_public_ip():
    try:
        return requests.get('http://169.254.169.254/latest/meta-data/public-ipv4').text
    except requests.RequestException:
        return None

ALLOWED_HOSTS = ['localhost', '127.0.0.1']
public_ip = get_public_ip()
if public_ip:
    ALLOWED_HOSTS.append(public_ip)

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    
    # Third-party apps
    "rest_framework",                # Django REST framework
    "corsheaders",                   # CORS headers for cross-origin requests
    'django_q',                      # For sheduling automatic vote completion
    
    # Your apps
    "quiz_scheduling_app",           # Your app for quiz scheduling
    # 'users',
    # 'courses',
    # 'votes',
    # 'notifications',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # CORS Middleware for handling CORS
]

ROOT_URLCONF = "quiz_scheduling.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],  # Add paths to your template directories here if needed
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "quiz_scheduling.wsgi.application"

# Database
# Update to use MySQL instead of SQLite
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "quiz_scheduling_db",  # Your database name
        "USER": "root",  # Replace with your MySQL username
        "PASSWORD": "root2810",  # Replace with your MySQL password
        "HOST": "database-1.c1k8kme2oilo.eu-north-1.rds.amazonaws.com",  # Set to your MySQL host (e.g., 'localhost' or IP address)
        "PORT": "3306",  # Default MySQL port
        'OPTIONS': {
            'charset': 'utf8mb4',
        }
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Custom user model (if you have a custom user model in 'users' app)
AUTH_USER_MODEL = 'quiz_scheduling_app.User'

# CORS configuration (optional for allowing cross-origin requests)
CORS_ALLOW_ALL_ORIGINS = True  # For development purposes only, disable for production!

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")  # Save media files like images in this directory

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# REST framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # For JWT authentication
    ],
    # 'DEFAULT_PERMISSION_CLASSES': [
    #     'rest_framework.permissions.IsAuthenticated',  # Set default permission classes to IsAuthenticated
    # ],
}

# Security settings (optional, but recommended for production)
# If you're deploying to production, make sure to configure these properly:
# CSRF_COOKIE_SECURE = True
# SESSION_COOKIE_SECURE = True
# SECURE_BROWSER_XSS_FILTER = True
# SECURE_CONTENT_TYPE_NOSNIFF = True
# SECURE_SSL_REDIRECT = True  # Only if you're using HTTPS


# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # Use your email provider's SMTP server
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'optimizeslot@gmail.com'  # Your email
EMAIL_HOST_PASSWORD = 'lzlg xafz qkmr tens'  # Your app password





from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),  # 1 day
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),    # 1 day
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
    'UPDATE_LAST_LOGIN': False,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',
}


Q_CLUSTER = {
    'name': 'quiz_scheduling',
    'workers': 4,
    'recycle': 500,
    'timeout': 60,
    'compress': True,
    'save_limit': 250,
    'queue_limit': 500,
    'cpu_affinity': 1,
    'label': 'Django Q',
    'redis': {
        'host': '127.0.0.1',
        'port': 6379,
        'db': 0,
    }
}