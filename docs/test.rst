==================
Tests
==================

Running the tests using the example app
---------------------------------------
If you are developing ``django-tenant-schemas``
and want to run the tests to make sure they all still pass,
you can use the `./examples/tenant_tutorial` app to run the
tests.

If you have Fig and Docker installed, all you need to do is run

.. code-block:: bash

    fig up

and it will setup and run the tests, including the postgresql instance.


Running the tests in an external project
----------------------------------------
If you're using South, don't forget to set ``SOUTH_TESTS_MIGRATE = False``.

.. code-block:: bash

    ./manage.py test tenant_schemas.tests

Updating your app's tests to work with tenant-schemas
-----------------------------------------------------
Because django will not create tenants for you during your tests, we have packed some custom test cases and other utilities. If you want a test to happen at any of the tenant's domain, you can use the test case ``TenantTestCase``. It will automatically create a tenant for you, set the connection's schema to tenant's schema and make it available at ``self.tenant``. We have also included a ``TenantRequestFactory`` and a ``TenantClient`` so that your requests will all take place at the tenant's domain automatically. Here's an example

.. code-block:: python

    from tenant_schemas.test.cases import TenantTestCase
    from tenant_schemas.test.client import TenantClient

    class BaseSetup(TenantTestCase):
        def setUp(self):
            self.c = TenantClient(self.tenant)

        def test_user_profile_view(self):
            response = self.c.get(reverse('user_profile'))
            self.assertEqual(response.status_code, 200)
