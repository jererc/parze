import time
from urllib.parse import urlparse

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from parze import logger
from parze.parsers.base import BaseParser


class NvidiaGeforceParser(BaseParser):
    id = 'nvidia.geforce'

    @staticmethod
    def can_parse_url(url):
        res = urlparse(url)
        return 'nvidia' in res.netloc.split('.') \
            and res.path.strip('/').endswith('/geforce/news')

    def _wait_for_elements(self, url, poll_frequency=.5, timeout=10):
        self.driver.get(url)
        end_ts = time.time() + timeout
        while time.time() < end_ts:
            try:
                els = self.driver.find_elements(By.XPATH,
                    '//div[contains(@class, "article-title-text")]')
                if not els:
                    raise NoSuchElementException()
                return els
            except NoSuchElementException:
                time.sleep(poll_frequency)
        raise Exception('timeout')

    def _wait_for_item(self, root_el):
        return root_el.find_element(By.XPATH, './/a').text.strip()

    def parse(self, url):
        for el in self._wait_for_elements(url):
            name = WebDriverWait(el, 5).until(self._wait_for_item)
            if not name:
                logger.error(f'failed to get {self.id} item from:\n'
                    f'{el.get_attribute("outerHTML")}')
                continue
            yield name
