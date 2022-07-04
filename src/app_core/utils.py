#!/usr/bin/env python
# encoding: utf-8
from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import functools
import importlib

from django.apps import apps
from django.db import transaction
from django.utils.encoding import force_text


def serialize_instance(instance):
    """ Serialize Django model instance """
    model_name = force_text(instance._meta)
    return '{}:{}'.format(model_name, instance.pk)


def deserialize_instance(serialized_instance):
    """ Deserialize Django model instance """
    model_name, pk = serialized_instance.split(':')
    model = apps.get_model(model_name)
    return model._default_manager.get(pk=pk)


def serialize_class(cls):
    """ Serialize Python class """
    return '{}:{}'.format(cls.__module__, cls.__name__)


def deserialize_class(serilalized_cls):
    """ Deserialize Python class """
    module_name, cls_name = serilalized_cls.split(':')
    module = importlib.import_module(module_name)
    return getattr(module, cls_name)


def ensure_atomic_transaction(func):
    @functools.wraps(func)
    def wrapped(self, *args, **kwargs):
        with transaction.atomic():
            return func(self, *args, **kwargs)
    return wrapped
