import os

import django
from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "QRTendify_project.settings")
django.setup()

from core.models import User  # noqa: E402


def main() -> None:
    try:
        user = User.objects.get(email="ali@gmail.com")
        print("User ali@gmail.com exists")
        print(f"  - Is active: {user.is_active}")
        print(f"  - Has usable password: {user.has_usable_password()}")
        print(f"  - First name: {user.first_name}")
        print(f"  - Last name: {user.last_name}")

        is_correct = user.check_password("12345678")
        print(f"  - Password '12345678' is correct: {is_correct}")

        if not is_correct:
            print("\nPassword is not '12345678'. Updating password...")
            user.set_password("12345678")
            user.save()
            print("Password updated to '12345678'")

    except User.DoesNotExist:
        print("User ali@gmail.com does not exist. Creating...")
        user = User.objects.create_user(
            email="ali@gmail.com",
            password="12345678",
            first_name="Ali",
            last_name="Test",
        )
        user.is_active = True
        user.save()
        print("Created user ali@gmail.com with password '12345678'")

    print("\n=== All users in database ===")
    for u in User.objects.all()[:10]:
        print(
            f"- {u.email} (active: {u.is_active}, has_password: {u.has_usable_password()})"
        )


if __name__ == "__main__":
    main()
