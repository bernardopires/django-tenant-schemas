==========================
Frequently Asked Questions
==========================

Authentication & Users
======================

Where should I put ``django.contrib.auth`` -- in ``SHARED_APPS``, ``TENANT_APPS``, or both?
--------------------------------------------------------------------------------------------

It depends on your requirements.

**Both** ``SHARED_APPS`` **and** ``TENANT_APPS`` **(most common):**

Place ``django.contrib.auth`` in both lists. This creates user tables in the
``public`` schema *and* in each tenant schema. The PostgreSQL ``search_path``
means that queries for users from within a tenant context will hit the tenant's
own ``auth_user`` table first. This approach supports per-tenant user isolation
while still allowing shared user records in ``public`` if needed.

.. code-block:: python

    SHARED_APPS = (
        'tenant_schemas',
        'customers',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        # ...
    )

    TENANT_APPS = (
        'django.contrib.auth',
        'django.contrib.contenttypes',
        # ...
    )

``SHARED_APPS`` **only:**

All users live in the ``public`` schema. Every tenant shares the same user
table. You will need your own logic to associate users with tenants (e.g. a
profile model with a ``ForeignKey`` to your tenant model).

``TENANT_APPS`` **only:**

Each tenant has completely isolated users. There is no shared user table. A user
in ``tenant1`` is completely invisible to ``tenant2``.

If you need shared users that also have per-tenant permissions, consider a
pattern where ``django.contrib.auth`` is in both, and you maintain a mapping
model in a shared app that links users to the tenants they can access.


How do I create a superuser for a specific tenant?
--------------------------------------------------

Use the ``tenant_command`` management command to wrap Django's built-in
``createsuperuser``:

.. code-block:: bash

    ./manage.py tenant_command createsuperuser --schema=my_tenant

This sets the database connection to the specified tenant's schema before
running ``createsuperuser``, so the user is created in that tenant's
``auth_user`` table.

.. important::

    If ``django.contrib.auth`` is in both ``SHARED_APPS`` and ``TENANT_APPS``,
    a superuser created this way exists only in that tenant's schema. It does
    *not* exist in the ``public`` schema or in other tenants' schemas.


Why can a superuser from one tenant log into another tenant's admin?
--------------------------------------------------------------------

This happens when ``django.contrib.auth`` is in ``SHARED_APPS`` (or both
``SHARED_APPS`` and ``TENANT_APPS``) and the user record lives in the
``public`` schema. Because ``public`` is always included in the PostgreSQL
``search_path``, authentication will find users in the ``public`` schema from
any tenant context.

To restrict users to a specific tenant:

1. Ensure users are created **in the tenant schema**, not ``public``. Use
   ``tenant_command createsuperuser --schema=the_tenant``.
2. If ``django.contrib.auth`` is only in ``TENANT_APPS``, each tenant's user
   table is fully isolated and this problem does not arise.
3. If you need auth in ``SHARED_APPS`` for a centralised login page, you will
   need custom middleware or a custom authentication backend that checks whether
   the authenticated user is authorised for the current tenant.


How do I implement centralised login that redirects users to their tenant?
--------------------------------------------------------------------------

A common pattern is:

1. Place your login view on the **public** tenant (using
   ``PUBLIC_SCHEMA_URLCONF``).
2. After authentication, look up which tenant the user belongs to.
3. Redirect the user to their tenant's URL.

.. code-block:: python

    from django.contrib.auth import authenticate, login
    from django.shortcuts import redirect, render

    def login_view(request):
        if request.method == 'POST':
            user = authenticate(
                request,
                username=request.POST['username'],
                password=request.POST['password'],
            )
            if user is not None:
                login(request, user)
                tenant = get_tenant_for_user(user)  # your lookup logic
                return redirect(f'https://{tenant.domain_url}/')
        return render(request, 'login.html')

.. warning::

    **Session cookies across subdomains:** if your public tenant and your
    tenants are on different subdomains, the session cookie set during login on
    the public domain will not be sent to the tenant subdomain. You have two
    options:

    * Set ``SESSION_COOKIE_DOMAIN`` to a shared parent domain (e.g.
      ``.example.com``) so the cookie is valid across all subdomains.
    * Implement a token-based redirect where the public login generates a
      one-time token and the tenant endpoint consumes it to establish a local
      session.

    This is the most common cause of "the request's session was deleted before
    the request completed" errors when redirecting after login.


Can I have a ``ForeignKey`` from a tenant model to a shared ``User`` model?
---------------------------------------------------------------------------

Yes. If ``django.contrib.auth`` is in ``SHARED_APPS``, the ``auth_user`` table
exists in the ``public`` schema. Because the tenant's ``search_path`` includes
``public``, ``ForeignKey`` references to ``User`` from tenant models work:

.. code-block:: python

    from django.contrib.auth.models import User

    class Invoice(models.Model):
        created_by = models.ForeignKey(User, on_delete=models.PROTECT)
        amount = models.DecimalField(max_digits=10, decimal_places=2)

        class Meta:
            app_label = 'billing'  # a TENANT_APP

PostgreSQL will create a cross-schema foreign key constraint. This pattern is
used in the project's own test suite with the ``ModelWithFkToPublicUser`` model.

.. warning::

    If ``django.contrib.auth`` is in *both* ``SHARED_APPS`` and
    ``TENANT_APPS``, the tenant schema has its own ``auth_user`` table that
    **shadows** the ``public`` one. In this case, the ``ForeignKey`` will point
    to the tenant's local user table, not the shared one. Make sure your
    configuration matches your intent.


How do I access tenant data from the public schema (or from another tenant)?
----------------------------------------------------------------------------

Use :func:`~tenant_schemas.utils.schema_context` or
:func:`~tenant_schemas.utils.tenant_context` to temporarily switch the database
connection:

.. code-block:: python

    from tenant_schemas.utils import schema_context

    # Currently on the public schema
    with schema_context('tenant1'):
        tenant1_users = list(User.objects.all())

    with schema_context('tenant2'):
        tenant2_users = list(User.objects.all())

To iterate across **all** tenants:

.. code-block:: python

    from tenant_schemas.utils import schema_context, get_public_schema_name
    from customers.models import Client

    tenants = Client.objects.exclude(schema_name=get_public_schema_name())
    all_products = []

    for tenant in tenants:
        with schema_context(tenant.schema_name):
            all_products.extend(Product.objects.all())

.. important::

    Querysets are lazy. If you return a queryset from inside a
    ``schema_context`` without evaluating it, it will execute in whatever schema
    is active when it is eventually evaluated. Use ``list()`` to force
    evaluation inside the context manager.


How do I populate a tenant with initial data after creation?
------------------------------------------------------------

Use the ``post_schema_sync`` signal, which fires after a tenant is saved, its
schema is created, and migrations have run:

.. code-block:: python

    from tenant_schemas.signals import post_schema_sync
    from tenant_schemas.models import TenantMixin
    from tenant_schemas.utils import tenant_context

    def setup_new_tenant(sender, tenant, **kwargs):
        with tenant_context(tenant):
            from django.contrib.auth.models import Group
            Group.objects.create(name='Admins')
            Group.objects.create(name='Staff')
            # load fixtures, create default records, etc.

    post_schema_sync.connect(setup_new_tenant, sender=TenantMixin)

For loading fixtures programmatically:

.. code-block:: python

    from django.core.management import call_command
    from tenant_schemas.utils import schema_context

    with schema_context('my_tenant'):
        call_command('loaddata', 'initial_data.json')


How do I get the current tenant or schema name inside a view, signal, or other code?
------------------------------------------------------------------------------------

The current schema and tenant are available on the database connection at any
point during a request:

.. code-block:: python

    from django.db import connection

    # Get the current schema name
    schema_name = connection.schema_name

    # Get the current tenant object (set by middleware)
    tenant = connection.tenant

    # Get the full domain
    domain = connection.tenant.domain_url

In a Django signal such as ``post_save``:

.. code-block:: python

    from django.db.models.signals import post_save
    from django.db import connection

    def my_post_save(sender, instance, **kwargs):
        current_schema = connection.schema_name
        current_tenant = connection.tenant
        # use as needed

    post_save.connect(my_post_save, sender=MyModel)

In templates, the tenant is available on the request object because the
middleware sets ``request.tenant``:

.. code-block:: html+django

    <p>Current tenant: {{ request.tenant.domain_url }}</p>
