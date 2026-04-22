from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.conf import settings


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a standard User with the given email.
        """
        if not email:
            raise ValueError("The Email field must be set")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and save a SuperUser with required staff and superuser permissions.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        if not password:
            raise ValueError("Superuser must have a password.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Represents a single user account in the system, customized to use
    email as the primary unique identifier instead of a username.
    """

    username = None
    email = models.EmailField("email address", unique=True)

    sso_provider = models.CharField(max_length=50, blank=True, null=True)
    job_title = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="What is your role?"
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    def __str__(self):
        return self.email


class Plan(models.Model):
    """
    Stores the subscription plan details, defining pricing and session limits.
    """

    plan_id = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=100)
    session_limit = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name


class Organization(models.Model):
    """
    Represents a single organization or company managing sessions.
    """

    name = models.CharField(max_length=255, unique=True)
    domain = models.CharField(max_length=255, unique=False)
    created_at = models.DateTimeField(auto_now_add=True)
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True)
    session_limit = models.IntegerField(default=1)
    sessions_used_current_cycle = models.IntegerField(default=0)

    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="OrganizationMember",
        related_name="organizations",
    )

    def __str__(self):
        return self.name


class OrganizationMember(models.Model):
    """
    The intermediary table connecting a User to an Organization,
    defining their role and membership status.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("active", "Active"),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=50)  # e.g., 'Owner', 'Admin', 'Member'
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="pending")

    class Meta:
        unique_together = ("organization", "user")


class Session(models.Model):
    """
    The main event, class, or meeting being tracked for attendance.
    """

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Null for personal sessions.",
    )
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50)  # 'Scheduled', 'Open', 'Closed'
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class AccessRule(models.Model):
    """
    Stores security and access constraints for a session, such as email domains.
    """

    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    rule_type = models.CharField(max_length=50)
    rule_value = models.CharField(max_length=255)
    is_allow_list = models.BooleanField(default=True)


class AttendanceCode(models.Model):
    """
    Stores the permanent (STATIC) codes and QR strings used for a session.
    """

    session = models.OneToOneField(Session, on_delete=models.CASCADE, primary_key=True)
    static_qr_string = models.CharField(max_length=255, unique=True)
    verification_number = models.CharField(max_length=4, unique=True)


class AttendanceRecord(models.Model):
    """
    The log of a successful check-in by a user for a specific session.
    """

    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    check_in_time = models.DateTimeField(auto_now_add=True)
    check_in_method = models.CharField(
        max_length=10
    )  # 'StaticQR', 'DynamicQR', 'Manual'
    is_verified = models.BooleanField(default=False)
    device_ip = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        unique_together = ("session", "user")


class DeviceLog(models.Model):
    """
    Stores extra data associated with an attendance record, primarily location.
    """

    attendance_record = models.OneToOneField(
        AttendanceRecord, on_delete=models.CASCADE, primary_key=True
    )
    browser = models.CharField(max_length=100, blank=True, null=True)
    os = models.CharField(max_length=100, blank=True, null=True)
    user_agent_string = models.TextField(blank=True, null=True)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )


class DynamicQrToken(models.Model):
    """
    Stores temporary, short-lived tokens and codes for dynamic QR generation.
    """

    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    token = models.CharField(max_length=64)
    verification_code = models.CharField(max_length=4, null=True, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)


class SessionSetting(models.Model):
    """
    Stores all advanced configuration options for a specific session.
    """

    session = models.OneToOneField(Session, on_delete=models.CASCADE, primary_key=True)
    is_dynamic_qr = models.BooleanField(default=False)
    qr_refresh_interval_seconds = models.IntegerField(default=30)
    auto_close_duration_minutes = models.IntegerField(null=True, blank=True)

    is_location_required = models.BooleanField(default=False)

    check_in_window_minutes = models.IntegerField(
        default=0,
        help_text="Time (in minutes) after session start time that check-in is allowed. 0 = No time limit.",
    )


class CertificateTemplate(models.Model):
    """
    Stores the PDF template and configuration for certificate generation.
    """

    session = models.OneToOneField(Session, on_delete=models.CASCADE, primary_key=True)
    template_file = models.FileField(
        upload_to="certificate_templates/",
        help_text="Upload a blank PDF certificate template",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="If unchecked, certificates will NOT be sent automatically.",
    )

    # Text positioning for attendee name
    name_x_position = models.IntegerField(
        default=200, help_text="X coordinate for attendee name (pixels from left)"
    )
    name_y_position = models.IntegerField(
        default=400, help_text="Y coordinate for attendee name (pixels from bottom)"
    )

    # Font settings
    font_name = models.CharField(
        max_length=50,
        default="Helvetica-Bold",
        choices=[
            ("Helvetica", "Helvetica"),
            ("Helvetica-Bold", "Helvetica Bold"),
            ("Times-Roman", "Times Roman"),
            ("Times-Bold", "Times Bold"),
            ("Courier", "Courier"),
        ],
    )
    font_size = models.IntegerField(default=24, help_text="Font size for attendee name")
    font_color = models.CharField(
        max_length=7,
        default="#000000",
        help_text="Hex color code (e.g., #000000 for black)",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Certificate Template for {self.session.title}"


class GeneratedCertificate(models.Model):
    """
    Tracks generated certificates and their email delivery status.
    """

    attendance_record = models.OneToOneField(
        AttendanceRecord, on_delete=models.CASCADE, primary_key=True
    )
    certificate_file = models.FileField(
        upload_to="generated_certificates/", blank=True, null=True
    )

    # Email delivery tracking
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    email_error = models.TextField(
        blank=True, null=True, help_text="Error message if email failed"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Certificate for {self.attendance_record.user.email} - {self.attendance_record.session.title}"
