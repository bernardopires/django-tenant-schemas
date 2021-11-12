=====
Tests
=====

Running the tests
-----------------
Run these tests from the project ``dts_test_project``, it comes prepacked with the correct settings file and extra apps to enable tests to ensure different apps can exist in ``SHARED_APPS`` and ``TENANT_APPS``.

.. code-block:: bash

    ./manage.py test tenant_schemas.tests

To run the test suite outsite of your application you can use tox_ to test all supported Django versions.

.. code-block:: bash

    tox

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


Running tests faster
--------------------
Running tests using ``TenantTestCase`` can start being a bottleneck once the number of tests grow. ``TenantTestCase`` drops, recreates and executes migrations for the test schema every time for every ``TenantTestCase`` you have. If you do not care that the state between tests is kept, an alternative is to use the class ``FastTenantTestCase``. Unlike ``TenantTestCase``, the test schema and its migrations will only be created and ran once. This is a significant improvement in speed coming at the cost of shared state.

.. code-block:: python

    from tenant_schemas.test.cases import FastTenantTestCase


Updating TestCase for more complicated tenant
---------------------------------------------

If you set your tenant to not automatically create schema by setting ``auto_create_schema = False`` or if you have some fields that have to be filled for the tenant, you can override the provided ``TenantTestCase`` or ``FastTenantTestCase`` and implement the class method ``modify_tenant_instance`` with all the updates you need. Here's a example for tenant which doesn't create schemas automatically and has to have a name set up.

.. code-block:: python

    from tenant_schemas.test import cases

    class TenantTestCase(cases.TenantTestCase):
        @classmethod
        def modify_tenant_instace(cls):
            cls.auto_create_schema = True
            cls.name = "Name of the tenant"


.. _tox: https://tox.readthedocs.io/
