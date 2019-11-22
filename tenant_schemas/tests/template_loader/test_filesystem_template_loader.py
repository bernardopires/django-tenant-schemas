import os

from django.template.loader import get_template
from django.test import override_settings
from tenant_schemas.test.cases import TenantTestCase

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(os.path.dirname(__file__), "templates")],
        "OPTIONS": {
            "context_processors": ["django.template.context_processors.request"],
            "loaders": [
                "tenant_schemas.template_loaders.FilesystemLoader",
                "django.template.loaders.filesystem.Loader",
            ],
        },
    }
]

MULTITENANT_TEMPLATE_DIRS = [
    os.path.join(os.path.dirname(__file__), "themes/%s/templates")
]


class FilesystemLoaderTenantTests(TenantTestCase):
    @override_settings(
        TEMPLATES=TEMPLATES, MULTITENANT_TEMPLATE_DIRS=MULTITENANT_TEMPLATE_DIRS
    )
    def test_get_template(self):
        template = get_template("hello.html")
        self.assertEqual(template.render(), "Hello, Tenant! (Django templates)\n")
