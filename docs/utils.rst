=====
Utils
=====

.. function:: schema_context(schema_name)

This is a context manager. Database queries performed inside it will be executed in against the passed ``schema_name``.

.. code-block:: python

	from tenant_schemas.utils import schema_context
	from django.auth.models import User

	with schema_context('some_tenant'):
		users = User.objects.all()
		print(users)


.. function:: tenant_context(tenant)

Same as ``schema_context`` but this time a tenant must be passed.

.. code-block:: python

	from tenant_schemas.utils import tenant_context, get_tenant_model
	from django.auth.models import User

	tenant = get_tenant_model().objects.get(schema_name='some_tenant')

	with tenant_context(tenant):
		users = User.objects.all()
		print(users)


.. function:: get_tenant_model()

Returns the tenant model.

.. code-block:: python

	from tenant_schemas.utils import get_tenant_model

	tenant = get_tenant_model().objects.get(schema_name='some_tenant')
	print(tenant.domain_url)


