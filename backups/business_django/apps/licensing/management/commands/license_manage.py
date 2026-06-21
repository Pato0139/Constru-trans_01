from django.core.management.base import BaseCommand, CommandError

from apps.licensing.services import (
    activate_license,
    get_current_installation,
    trigger_self_destruct,
    validate_installation,
)


class Command(BaseCommand):
    help = "Manage Constru-Trans licenses (activate, revoke, check status, self-destruct)"

    def add_arguments(self, parser):
        parser.add_argument(
            "action",
            choices=["activate", "revoke", "status", "self_destruct"],
            help="Action to perform: activate, revoke, status, self_destruct",
        )
        parser.add_argument("--customer-id", type=str, help="Customer ID for activation")
        parser.add_argument("--days", type=int, help="Number of days the license is valid for")

    def handle(self, *args, **options):
        action = options["action"]

        if action == "activate":
            if not options["customer_id"] or not options["days"]:
                raise CommandError("You must provide --customer-id and --days for activation!")
            self.activate_license(options["customer_id"], options["days"])
        elif action == "revoke":
            self.revoke_license()
        elif action == "status":
            self.check_status()
        elif action == "self_destruct":
            self.confirm_self_destruct()

    def activate_license(self, customer_id, days):
        try:
            inst = activate_license(customer_id, days)
            self.stdout.write(self.style.SUCCESS("Successfully activated license!"))
            self.stdout.write(f"Customer ID: {inst.customer_id}")
            self.stdout.write(f"Instance ID: {inst.instance_id}")
            self.stdout.write(f"Expires at: {inst.expires_at}")
            self.stdout.write(f"Status: {inst.status}")
        except Exception as e:
            raise CommandError(f"Failed to activate license: {e}")

    def revoke_license(self):
        try:
            inst = get_current_installation()
            if not inst:
                raise CommandError("No installation found!")
            inst.license_token = ""
            inst.customer_id = ""
            inst.expires_at = None
            inst.status = "revoked"
            inst.save()
            validate_installation()
            self.stdout.write(self.style.SUCCESS("Successfully revoked license!"))
        except Exception as e:
            raise CommandError(f"Failed to revoke license: {e}")

    def check_status(self):
        try:
            inst = validate_installation()
            if not inst:
                self.stdout.write("No installation found!")
                return
            self.stdout.write(self.style.SUCCESS("License Status:"))
            self.stdout.write(f"Instance ID: {inst.instance_id}")
            self.stdout.write(f"Customer ID: {inst.customer_id}")
            self.stdout.write(f"Status: {inst.status}")
            self.stdout.write(f"Activated at: {inst.activated_at}")
            self.stdout.write(f"Last validated at: {inst.last_validated_at}")
            self.stdout.write(f"Expires at: {inst.expires_at}")
        except Exception as e:
            raise CommandError(f"Failed to check status: {e}")

    def confirm_self_destruct(self):
        self.stdout.write(
            self.style.WARNING("⚠️ WARNING: SELF-DESTRUCT WILL DELETE ALL DATABASE AND MEDIA FILES!")
        )
        self.stdout.write(self.style.WARNING("This action is irreversible!"))
        confirm = input("Type 'CONFIRM' to proceed: ")
        if confirm == "CONFIRM":
            try:
                trigger_self_destruct()
                self.stdout.write(self.style.SUCCESS("Self-destruct executed!"))
            except Exception as e:
                raise CommandError(f"Self-destruct failed: {e}")
        else:
            self.stdout.write("Self-destruct cancelled!")
