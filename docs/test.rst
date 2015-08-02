==================
Tests
==================
Running the tests
-----------------
If you're using South, don't forget to set ``SOUTH_TESTS_MIGRATE = False``. Run these tests from the project ``dts_test_project``, it comes prepacked with the correct settings file and extra apps to enable tests to ensure different apps can exist in ``SHARED_APPS`` and ``TENANT_APPS``.

.. code-block:: bash

    ./manage.py test tenant_schemas.tests

Updating your app's tests to work with tenant-schemas
-----------------------------------------------------
Because django will not create tenants for you during your tests, we have packed some custom test cases and other utilities. If you want a test to happen at any of the tenant's domain, you can use the test case ``TenantTestCase``. It will automatically create a tenant for you, set the connection's schema to tenant's schema and make it available at ``self.tenant``. We have also included a ``TenantRequestFactory`` and a ``TenantClient`` so that your requests will all take place at the tenant's domain automatically. Here's an example

.. code-block:: python

    from django.conf import settings
    from tenant_schemas.test.cases import TenantTestCase

    User = settings.AUTH_USER_MODEL

    class BaseSetup(TenantTestCase):
        def setUp(self):
            self.user = User.objects.create_user(
                username='john.doe',
                email='john.doe@nowhere.com',
                password='qwerty'
            )
            
        def test_user_profile_view(self):
            credentials = dict(
                username='john.doe',
                password='qwerty'
            )
            self.client.login(**credentials)
            response = self.client.get(reverse('user_profile'))
            self.assertEqual(response.status_code, 200)
            self.client.logout()

Compared with version 1.5.2, we've specified the ``client_class`` for the ``TenantTestCase`` definition, therefor we have the client accessible from within the test case. Previous constructions where the client was instantiated explicitly should still work.

Using Tom Christie's Django Rest Framework
------------------------------------------
If by any chance you're using Django Rest Framework, then you might want to use the particular unitary test classes from that package. In order to do that, just subclass your test cases from the specialized API class ``APITenantTestCase``. The example from above can be adapted like so

.. code-block:: python

    from django.conf import settings
    from rest_framework import status
    from tenant_schemas.test.drf import APITenantTestCase

    User = settings.AUTH_USER_MODEL

    class BaseSetup(APITenantTestCase):
        def setUp(self):
            self.user = User.objects.create_user(
                username='john.doe',
                email='john.doe@nowhere.com',
                password='qwerty'
            )

        def test_user_profile_view(self):
            self.client.force_authenticate(self.user)
            response = self.client.get(reverse('user_profile'))
            self.assertEqual(response.status_code, status.HTTP_200_OK)

By default, the APITestCase class has the client already embedded inside it's definition.