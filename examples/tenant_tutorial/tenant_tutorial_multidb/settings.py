from tenant_tutorial.settings import *

DATABASES = {
    'default':{
        'ENGINE': 'tenant_schemas.postgresql_backend',
        'NAME': 'tenant_tutorial',
        'USER': 'postgres',
        'PASSWORD': 'root',
        'HOST': 'localhost',   
        'PORT': '',
    },
    'db1': {
        'ENGINE': 'tenant_schemas.postgresql_backend',
        'NAME': 'tenant_tutorial1',
        'USER': 'postgres',
        'PASSWORD': 'root',
        'HOST': 'localhost',   
        'PORT': '',
    },
    'db2': {
        'ENGINE': 'tenant_schemas.postgresql_backend',
        'NAME': 'tenant_tutorial2',
        'USER': 'postgres',
        'PASSWORD': 'root',
        'HOST': 'localhost',   
        'PORT': '',
    }
}

WSGI_APPLICATION = 'tenant_tutorial_multidb.wsgi.application'

DATABASE_ROUTERS += ('tenant_schemas.multidb.MultiDBRouter',)


MIDDLEWARE_CLASSES = (
    'tenant_schemas.multidb.MultiDBTenantMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)


ROOT_URLCONF = 'tenant_tutorial_multidb.urls_tenants'
PUBLIC_SCHEMA_URLCONF = 'tenant_tutorial_multidb.urls_public'