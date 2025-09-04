===========================
Examples
===========================
Tenant Tutorial
-----------------
This app comes with an interactive tutorial to teach you how to use ``django-tenant-schemas`` and to demonstrate its capabilities. This example project is available under `examples/tenant_tutorial <https://github.com/bernardopires/django-tenant-schemas/blob/master/examples/tenant_tutorial>`_. 

Setup Instructions
~~~~~~~~~~~~~~~~~~

**Prerequisites**: This tutorial requires `uv <https://docs.astral.sh/uv/>`_, a fast Python package manager. Install it by following the `uv installation guide <https://docs.astral.sh/uv/getting-started/installation/>`_.

1. **Install dependencies**: Navigate to the tutorial directory and install the required packages:

.. code-block:: bash

    cd examples/tenant_tutorial
    uv pip sync requirements.txt

2. **Configure the database**: Edit the ``settings.py`` file to configure the ``DATABASES`` variable for your PostgreSQL setup. The default configuration expects a PostgreSQL database named ``tenant_tutorial`` with user ``postgres`` and password ``root`` on localhost.

3. **Run initial migrations**: Use ``migrate_schemas`` instead of the regular ``migrate`` command:

.. code-block:: bash

    uv run python manage.py migrate_schemas

4. **Start the development server**:

.. code-block:: bash

    uv run python manage.py runserver 

All other steps will be explained by following the tutorial, just open ``http://127.0.0.1:8000`` on your browser.

**Important Notes:**

- Always use ``migrate_schemas`` instead of ``migrate`` when working with tenant schemas
- The tutorial uses ``ALLOWED_HOSTS = ['*']`` for development convenience - be more restrictive in production
- Make sure PostgreSQL is installed and running before starting the tutorial
