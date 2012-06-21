from django import test
from django.db import connection
from django.core.exceptions import ImproperlyConfigured
from django_schemata.postgresql_backend.base import DatabaseError
from django.db.utils import DatabaseError
from django.conf import settings
from django.core.management import call_command
from django.contrib.sites.models import Site

# only run this test if the custom database wrapper is in use.
if hasattr(connection, 'schema_name'):
    # This will fail with Django==1.3.1 AND psycopg2==2.4.2
    # See https://code.djangoproject.com/ticket/16250
    # Either upgrade Django to trunk or use psycopg2==2.4.1
    def set_schematas(domain):
        settings.SCHEMATA_DOMAINS = {
            domain: {
                'schema_name': domain,
            }
        }


    def add_schemata(domain):
        settings.SCHEMATA_DOMAINS.update({
            domain: {
                'schema_name': domain,
            }
        })


    class SchemataTestCase(test.TestCase):
        def setUp(self):
            set_schematas('blank')
            self.c = test.client.Client()

        def tearDown(self):
            connection.set_schemata_off()

        def test_unconfigured_domain(self):
            self.assertRaises(ImproperlyConfigured, self.c.get, '/')

        def test_unmanaged_domain(self):
            add_schemata('not_in_db')
            self.assertRaises(DatabaseError, self.c.get, '/', HTTP_HOST='not_in_db')

        def test_domain_switch(self):
            add_schemata('test1')
            add_schemata('test2')
            call_command('manage_schemata')

            self.c.get('/', HTTP_HOST='test1')
            test1 = Site.objects.get(id=1)
            test1.domain = 'test1'
            test1.save()

            self.c.get('/', HTTP_HOST='test2')
            test2 = Site.objects.get(id=1)
            test2.domain = 'test2'
            test2.save()

            self.c.get('/', HTTP_HOST='test1')
            test = Site.objects.get_current()
            self.assertEqual(test.domain, 'test1', 'Current site should be "test1", not "%s"' % test.domain)
