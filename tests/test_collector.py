import logging
import os
from pprint import pprint
import shutil
import time
import unittest
from unittest.mock import patch

import parze as module
WORK_PATH = os.path.join(os.path.expanduser('~'), '_test_parze')
module.WORK_PATH = WORK_PATH
module.logger.setLevel(logging.DEBUG)
module.logger.handlers.clear()
from parze import collector as module
from parze.parsers import base


def remove_path(path):
    if os.path.isdir(path):
        shutil.rmtree(path)
    elif os.path.isfile(path):
        os.remove(path)


def makedirs(path):
    if not os.path.exists(path):
        os.makedirs(path)


class StorageTestCase(unittest.TestCase):
    def setUp(self):
        remove_path(WORK_PATH)
        makedirs(WORK_PATH)
        self.base_path = os.path.join(WORK_PATH, 'parzed')

    def _gen_items(self, keys):
        return {str(k): 0 for k in keys}

    def test_1(self):
        url1 = 'https://1337x.to/user/1/'
        url2 = 'https://1337x.to/user/2/'

        obj = module.ItemStorage(base_path=self.base_path)
        self.assertTrue(obj._get_dst_path(url1) != obj._get_dst_path(url2))

        all_items = self._gen_items(range(1, 6))
        new_items = obj.get_new_items(url1, all_items)
        self.assertEqual(new_items, all_items)
        obj.save(url1, all_items, new_items)

        all_items = self._gen_items(range(3, 8))
        new_items = obj.get_new_items(url1, all_items)
        self.assertEqual(new_items, self._gen_items(range(6, 8)))
        obj.save(url1, all_items, new_items)

        obj = module.ItemStorage(base_path=self.base_path)
        all_items = self._gen_items(range(7, 11))
        new_items = obj.get_new_items(url1, all_items)
        self.assertEqual(new_items, self._gen_items(range(8, 11)))
        obj.save(url1, all_items, new_items)

        url1_items = obj._load_items(url1)
        self.assertTrue(url1_items)

        all_items = self._gen_items(range(11, 21))
        new_items = obj.get_new_items(url2, all_items)
        self.assertEqual(new_items, all_items)
        obj.save(url2, all_items, new_items)

        all_items = self._gen_items(range(13, 24))
        new_items = obj.get_new_items(url2, all_items)
        self.assertEqual(new_items, self._gen_items(range(21, 24)))
        obj.save(url2, all_items, new_items)

        url1_items2 = obj._load_items(url1)
        self.assertEqual(url1_items2, url1_items)

        with patch.object(module, 'get_file_mtime') as mock_get_file_mtime:
            mock_get_file_mtime.return_value = time.time() - module.STORAGE_RETENTION_DELTA - 1
            obj.cleanup({url2})
        self.assertFalse(obj._load_items(url1))
        self.assertTrue(obj._load_items(url2))


class CleanItemTestCase(unittest.TestCase):
    def test_1(self):
        item = 'L.A. Noire: The Complete Edition (v2675.1 + All DLCs, MULTi6) [FitGirl Repack]'
        self.assertEqual(module.clean_item(item), 'L.A. Noire: The Complete Edition')

    def test_2(self):
        item = 'L.A. Noire: The Complete Edition (v2675.1 + All DLCs, MULTi6) [FitGirl...'
        self.assertEqual(module.clean_item(item), 'L.A. Noire: The Complete Edition')

    def test_3(self):
        item = 'L.A. Noire: The Complete Edition (v2675.1 + All DLCs, ...'
        self.assertEqual(module.clean_item(item), 'L.A. Noire: The Complete Edition')

    def test_4(self):
        item = 'L.A. Noire (The Complete Edition) (v2675.1 + All DLCs, ...'
        self.assertEqual(module.clean_item(item), 'L.A. Noire')

    def test_5(self):
        item = 'L.A. Noire [X] (v2675.1 + All DLCs, MULTi6) [FitGirl Repack]'
        self.assertEqual(module.clean_item(item), 'L.A. Noire')

    def test_6(self):
        item = '[X] L.A. Noire (v2675.1 + All DLCs, MULTi6) [FitGirl Repack]'
        self.assertEqual(module.clean_item(item), 'L.A. Noire')


class URLItemTestCase(unittest.TestCase):
    def test_1(self):
        urls = [
            'https://1337x.to/user/FitGirl/',
            ('https://1337x.to/sort-search/monster%20hunter%20repack/time/desc/1/', 'monster hunter'),
            'https://rutracker.org/forum/tracker.php?f=557',
        ]
        res = [module.URLItem(r) for r in urls]
        pprint(res)
        self.assertTrue(all(bool(r.id) for r in res))
        self.assertTrue(all(bool(r.url) for r in res))


class ParsersTestCase(unittest.TestCase):
    def test_1(self):
        res = list(base.iterate_parsers())
        pprint(res)
        self.assertTrue(res)
        self.assertTrue(all(r.id is not None for r in res))
        self.assertTrue(all(issubclass(r, base.BaseParser) for r in res))
