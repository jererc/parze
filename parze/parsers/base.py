import importlib
import inspect
import os

from parze import logger


class BaseParser:
    id = None

    def __init__(self, driver):
        self.driver = driver

    @staticmethod
    def can_parse_url(url):
        raise NotImplementedError()

    def parse(self, url):
        raise NotImplementedError()


def iterate_parsers(package='parze.parsers'):
    for filename in os.listdir(os.path.dirname(os.path.realpath(__file__))):
        basename, ext = os.path.splitext(filename)
        if ext == '.py' and not filename.startswith('__'):
            module_name = f'{package}.{basename}'
            try:
                module = importlib.import_module(module_name)
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseParser) and obj is not BaseParser:
                        yield obj
            except ImportError as exc:
                logger.error(f'failed to import {module_name}: {exc}')
