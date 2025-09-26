#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "django-tenant-schemas[psycopg]",
# ]
#
# [tool.uv.sources]
# django-tenant-schemas = { path = "../../", editable = true }
# ///
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tenant_tutorial.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
