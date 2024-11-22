from glob import glob
import hashlib
import json
import logging
import os
import re
import shutil
import time
from urllib.parse import urlparse, unquote_plus
from uuid import uuid4

from svcutils.service import Notifier, get_file_mtime
from webutils.browser import get_driver

from parze import NAME, WORK_PATH, logger
from parze.parsers.base import iterate_parsers


MAX_NOTIF_PER_URL = 4
MAX_NOTIF_BODY_SIZE = 500
STORAGE_RETENTION_DELTA = 7 * 24 * 3600

logging.getLogger('selenium').setLevel(logging.INFO)
logging.getLogger('urllib3').setLevel(logging.INFO)


def makedirs(x):
    if not os.path.exists(x):
        os.makedirs(x)


def to_json(x):
    return json.dumps(x, indent=4, sort_keys=True)


def clean_item(item):
    res = re.sub(r'\(.*?\)', '', item).strip()
    res = re.sub(r'\[.*?\]', '', res).strip()
    res = re.sub(r'[\(][^\(]*$|[\[][^\[]*$', '', res).strip()
    return res or item


class ItemStorage:
    def __init__(self, base_path):
        self.base_path = os.path.realpath(base_path)

    def _get_dst_dirname(self, url):
        return hashlib.md5(url.encode('utf-8')).hexdigest()

    def _get_dst_path(self, url):
        return os.path.join(self.base_path, self._get_dst_dirname(url))

    def _get_dst_filename(self):
        return f'{uuid4().hex}.json'

    def _iterate_file_and_items(self, url):
        for file in glob(os.path.join(self._get_dst_path(url), '*.json')):
            try:
                with open(file) as fd:
                    items = json.load(fd)
            except Exception:
                logger.exception(f'failed to load file {file}')
                continue
            yield file, items

    def _load_items(self, url):
        res = {}
        for file, items in self._iterate_file_and_items(url):
            res.update(items)
        return res

    def get_new_items(self, url, items):
        stored_items = self._load_items(url)
        return {k: v for k, v in items.items() if k not in stored_items}

    def save(self, url, all_items, new_items):
        all_item_keys = set(all_items.keys())
        for file, items in self._iterate_file_and_items(url):
            if not set(items.keys()) & all_item_keys:
                os.remove(file)
                logger.debug(f'removed old file {file}')

        dst_path = self._get_dst_path(url)
        makedirs(dst_path)
        file = os.path.join(dst_path, self._get_dst_filename())
        with open(file, 'w') as fd:
            fd.write(to_json(new_items))

    def cleanup(self, all_urls):
        dirnames = {self._get_dst_dirname(r) for r in all_urls}
        min_ts = time.time() - STORAGE_RETENTION_DELTA
        for path in glob(os.path.join(self.base_path, '*')):
            if os.path.basename(path) in dirnames:
                continue
            mtimes = [get_file_mtime(r)
                for r in glob(os.path.join(path, '*'))]
            if not mtimes or max(mtimes) < min_ts:
                shutil.rmtree(path)
                logger.info(f'removed old storage path {path}')


class URLItem:
    def __init__(self, url_item):
        if not isinstance(url_item, (list, tuple)):
            url_item = [url_item]
        self.url = url_item[0]
        try:
            self.id = url_item[1]
        except IndexError:
            self.id = self._get_default_id()

    def __repr__(self):
        return f'id: {self.id}, url: {self.url}'

    def _get_default_id(self):
        parsed = urlparse(unquote_plus(self.url))
        words = re.findall(r'\b\w+\b', f'{parsed.path} {parsed.query}')
        tokens = [urlparse(self.url).netloc] + [r for r in words if len(r) > 1]
        return '-'.join(tokens)


class ItemCollector:
    def __init__(self, config, headless=True):
        self.config = config
        self.driver = get_driver(
            browser_id=self.config.BROWSER_ID,
            headless=headless,
            page_load_strategy='eager',
        )
        self.parsers = list(iterate_parsers())
        self.item_storage = ItemStorage(self.config.ITEM_STORAGE_PATH)

    def _notify_new_items(self, url_item, items):
        title = f'{NAME} {url_item.id}'
        asc_names = [clean_item(n) for n, _ in sorted(items.items(),
            key=lambda x: x[1])]
        max_latest = MAX_NOTIF_PER_URL - 1
        latest_names = asc_names[-max_latest:]
        older_names = asc_names[:-max_latest]
        if older_names:
            body = ', '.join(reversed(older_names))
            if len(body) > MAX_NOTIF_BODY_SIZE:
                body = f'{body[:MAX_NOTIF_BODY_SIZE]}...'
            Notifier().send(title=title, body=f'{body}')
        for name in latest_names:
            Notifier().send(title=title, body=name)

    def _iterate_parsers(self, url_item):
        for parser_cls in self.parsers:
            if parser_cls.can_parse_url(url_item.url):
                yield parser_cls(self.driver)

    def _collect_items(self, url_item):
        parsers = list(self._iterate_parsers(url_item))
        if not parsers:
            raise Exception('no parser')
        items = {}
        now = time.time()
        for parser in sorted(parsers, key=lambda x: x.id):
            names = [r for r in parser.parse(url_item.url) if r]
            logger.debug(f'{parser.id} output:\n'
                f'{json.dumps(names, indent=4)}')
            if not names:
                logger.error(f'no result from {parser.id}')
                Notifier().send(title=f'{NAME} error',
                    body=f'no result from {parser.id}')
                continue
            items.update({r: now - i for i, r in enumerate(names)})
        return items

    def _process_url_item(self, url_item):
        items = self._collect_items(url_item)
        if not items:
            raise Exception('no result')
        logger.info(f'parsed {len(items)} items from {url_item.url}')
        new_items = self.item_storage.get_new_items(url_item.url, items)
        if new_items:
            self._notify_new_items(url_item, new_items)
            self.item_storage.save(url_item.url, items, new_items)

    def run(self):
        start_ts = time.time()
        all_urls = set()
        try:
            for url in self.config.URLS:
                url_item = URLItem(url)
                all_urls.add(url_item.url)
                try:
                    self._process_url_item(url_item)
                except Exception as exc:
                    logger.exception(f'failed to process {url_item}')
                    Notifier().send(title=f'{NAME} error',
                        body=f'failed to process {url_item.id}: {exc}')
        finally:
            self.driver.quit()
        self.item_storage.cleanup(all_urls)
        logger.info(f'processed in {time.time() - start_ts:.02f} seconds')


def collect(config, headless=True):
    ItemCollector(config, headless=headless).run()
