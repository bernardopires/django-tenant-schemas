import os

from django.template.loader import get_template
from django.test import SimpleTestCase, override_settings


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
    ]
)
class CachedLoaderTests(SimpleTestCase):
    def test_get_template(self):
        template = get_template("hello.html")
        self.assertEqual(template.render(), "Hello! (Django templates)\n")
