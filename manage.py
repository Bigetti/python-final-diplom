#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from django.contrib.auth.management.commands.createsuperuser import Command as CreateSuperuserCommand


# from django.contrib.auth.management.commands.createsuperuser import Command as CreateSuperuserCommand

# class Command(CreateSuperuserCommand):
#     help = "Creates a new superuser."

#     def add_arguments(self, parser):
#         super().add_arguments(parser)
#         parser.remove_argument('username')

#     def handle(self, *args, **options):
#         if 'username' in options:
#             del options['username']
#         return super().handle(*args, **options)


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orders.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
