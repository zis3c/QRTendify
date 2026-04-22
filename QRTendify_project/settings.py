from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent


# --- CORE DJANGO SETTINGS ---

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-d5ofwj!-ud-qso4j8tzud$7)vg2(ub%44*=!j$wog)y-qcgk_r",
)
DEBUG = True
ALLOWED_HOSTS = []

# --- APPLICATION DEFINITION (INSTALLED_APPS) ---
INSTALLED_APPS = [
    # DJANGO DEFAULT APPS
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "widget_tweaks",
    # NEW FUNCTIONALITY APPS
    "import_export",
    "dbbackup",
    "simple_history",
    "guardian",
    "adminactions",
    # Your Apps
    "core",
    "background_task",
    # Allauth Apps
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.microsoft",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "QRTendify_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "QRTendify_project.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# --- CUSTOM AND ALLAUTH CONFIGURATION ---
AUTH_USER_MODEL = "core.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
    "guardian.backends.ObjectPermissionBackend",
]

SITE_ID = 2

# --- ADMIN PACKAGE CONFIGURATIONS ---

# django-import-export
IMPORT_EXPORT_USE_TRANSACTIONS = True
IMPORT_EXPORT_SKIP_ADMIN_LOG = False

# django-dbbackup
DBBACKUP_STORAGE = "django.core.files.storage.FileSystemStorage"
DBBACKUP_STORAGE_OPTIONS = {"location": os.path.join(BASE_DIR, "backups")}
DBBACKUP_CLEANUP_KEEP = 7

# django-simple-history
SIMPLE_HISTORY_HISTORY_ID_USE_UUID = True
SIMPLE_HISTORY_REVERT_DISABLED = False

# django-guardian
ANONYMOUS_USER_NAME = None

# django-adminactions
ADMINACTIONS_ACTION_LABEL = "Actions"
ADMINACTIONS_PERMISSION_NAME = "admin_actions"

# Admin Security
ADMIN_URL = "secure-admin/"

# --- ALLAUTH & ACCOUNT SETTINGS ---
ACCOUNT_LOGIN_METHODS = ["email"]
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_AUTO_SIGNUP = True

ACCOUNT_SIGNUP_FIELDS = ["email", "first_name", "last_name"]

SOCIALACCOUNT_LOGIN_ON_GET = True
ACCOUNT_FORMS = {
    "signup": "core.forms.CustomSignupForm",
    "login": "allauth.account.forms.LoginForm",
}

ACCOUNT_SIGNUP_REDIRECT_URL = "/manual-signup-redirect/"
ACCOUNT_ADAPTER = "core.adapter.MyAccountAdapter"
ACCOUNT_LOGIN_BY_CODE_ENABLED = False
ACCOUNT_LOGOUT_REDIRECT_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"


# --- INTERNATIONALIZATION & TIME ---
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kuala_Lumpur"
USE_I18N = True
USE_TZ = True

# --- STATIC FILES & MEDIA ---
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
# Keep third-party apps (e.g., background_task) aligned with their shipped migrations.
# Our app (`core`) explicitly opts into BigAutoField via `core.apps.CoreConfig`.
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# --- MEDIA FILES ---
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# --- EMAIL CONFIGURATION ---
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "webmaster@qrtendify.com")

# --- SECURITY & CHECKS ---
SILENCED_SYSTEM_CHECKS = ["account.W001"]

# --- SOCIAL ACCOUNT PROVIDERS ---
SOCIALACCOUNT_PROVIDERS = {
    "google": {"SCOPE": ["profile", "email"], "AUTH_PARAMS": {"access_type": "online"}},
    "microsoft": {"SCOPE": ["User.Read"], "AUTH_PARAMS": {"access_type": "online"}},
}
