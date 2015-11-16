from __future__ import absolute_import

import sys
import types

import django
from django.test import TestCase

from tenant_schemas import utils


class AppLabelsTestCase(TestCase):
    def setUp(self):
        self._modules = set()

    def tearDown(self):
        for name in self._modules:
            sys.modules.pop(name, None)

    def set_up_module(self, whole_name):
        parts = whole_name.split('.')
        name = ''
        for part in parts:
            name += ('.%s' % part) if name else part
            module = types.ModuleType(name)
            module.__path__ = ['/tmp']
            self._modules.add(name)
            sys.modules[name] = module
        return sys.modules[whole_name]

    def test_app_labels_1_7(self):
        """
        Verifies that app_labels handle Django 1.7+ AppConfigs properly.
        https://docs.djangoproject.com/en/1.7/ref/applications/
        """
        if django.VERSION >= (1, 7):
            from django.apps import AppConfig
        else:
            # set up poor man's mock for 1.7/1.8 behaviour.
            from collections import namedtuple

            class AppConfig(object):
                call_count = 0
                ret_map = {
                    'example1': 'example1',
                    'example2.apps.Example2AppConfig': 'example2_app',
                }

                @classmethod
                def create(cls, app):
                    return namedtuple('AppConfig', ['label'])(
                        cls.ret_map[app]
                    )
            dj_apps = self.set_up_module('django.apps')
            dj_apps.AppConfig = AppConfig

            reload(utils)

        self.set_up_module('example1')
        apps = self.set_up_module('example2.apps')

        # set up AppConfig on the `test_app.apps` module
        class Example2AppConfig(AppConfig):
            name = 'example2'
            label = 'example2_app'  # with different name
            path = '/tmp'  # for whatever reason path is required

        apps.Example2AppConfig = Example2AppConfig

        self.assertEqual(
            utils.app_labels([
                'example1',
                'example2.apps.Example2AppConfig'
            ]),
            ['example1', 'example2_app'],
        )

    def test_app_labels_pre_1_7(self):
        if django.VERSION >= (1, 7):
            # set AppConfig to None and reload utils module
            from django import apps
            AppConfig = apps.AppConfig
            apps.AppConfig = None

            reload(utils)

        self.assertEqual(
            utils.app_labels(
                ['example1', 'example2.apps.Example2AppConfig']
            ),
            ['example1', 'Example2AppConfig']
        )

        if django.VERSION >= (1, 7):
            # restore AppConfig
            apps.AppConfig = AppConfig
            reload(utils)
