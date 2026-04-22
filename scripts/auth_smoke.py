import os

import django
from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "QRTendify_project.settings")
django.setup()

from core.models import User  # noqa: E402
from django.contrib.auth import authenticate  # noqa: E402


def main() -> None:
    print("=== Existing Users ===")
    users = User.objects.all()
    print(f"Total users: {users.count()}")
    for user in users[:10]:
        print(
            f"Email: {user.email}, Active: {user.is_active}, "
            f"Has usable password: {user.has_usable_password()}"
        )

    print("\n=== Testing authentication for ali@gmail.com ===")
    user = authenticate(username="ali@gmail.com", password="12345678")
    if user:
        print(f"Authentication successful for {user.email}")
        return

    print("Authentication failed")
    try:
        existing_user = User.objects.get(email="ali@gmail.com")
    except User.DoesNotExist:
        print("User with email ali@gmail.com does not exist")
        return

    print(f"User exists: {existing_user.email}")
    print(f"Is active: {existing_user.is_active}")
    print(f"Has usable password: {existing_user.has_usable_password()}")
    print(f"Password check result: {existing_user.check_password('12345678')}")


if __name__ == "__main__":
    main()
