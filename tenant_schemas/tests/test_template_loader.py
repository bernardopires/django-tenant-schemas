import os

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase, override_settings

from tenant_schemas.utils import tenant_context

from tenant_schemas.tests.models import Tenant
from tenant_schemas.tests.testcases import BaseTestCase


@override_settings(
    TEMPLATES=[
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [
                os.path.join(os.path.dirname(__file__), "templates")
            ],
            'OPTIONS': {
                'context_processors': [
                    'django.template.context_processors.request',
                ],
                'loaders': [
                    ('tenant_schemas.template_loaders.CachedLoader', (
                        'tenant_schemas.template_loaders.FilesystemLoader',
                        'django.template.loaders.filesystem.Loader'
                    ))
                ]
            },
        }
    ],
    MULTITENANT_TEMPLATE_DIRS=[
        os.path.join(os.path.dirname(__file__), "multitenant")
    ]
)
class LoaderTests(BaseTestCase):
    """Test template loaders."""

    @classmethod
    def setUpTestData(cls):
        """Create a tenant."""
        settings.SHARED_APPS = ('tenant_schemas',
                                'django.contrib.contenttypes', )
        settings.TENANT_APPS = ()
        settings.INSTALLED_APPS = settings.SHARED_APPS + settings.TENANT_APPS
        cls.sync_shared()

        cls.tenant = Tenant(domain_url='localhost', schema_name='public')
        cls.tenant.save(verbosity=BaseTestCase.get_verbosity())

    def test_get_template_no_tenant(self):
        """Test template rendering with no tenant set in context."""
        template = get_template("hello.html")
        self.assertEqual(template.render(), "Hello! (Django templates)\n")

    def test_get_template_with_tenant(self):
        """Test template rendering with tenant set in context."""
        with tenant_context(self.tenant):
            template = get_template("hello.html")
            self.assertEqual(template.render(), "Hello from localhost!\n")
