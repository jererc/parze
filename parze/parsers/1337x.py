import time
from urllib.parse import urlparse

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

from parze import logger
from parze.parsers.base import BaseParser


class X1337xParser(BaseParser):
    id = '1337x'

    @staticmethod
    def can_parse_url(url):
        return '1337x' in urlparse(url).netloc.split('.')

    def _has_no_results(self):
        try:
            return bool(self.driver.find_element(By.XPATH,
                '//p[contains(text(), "No results were returned.")]'))
        except NoSuchElementException:
            return False

    def _wait_for_elements(self, url, poll_frequency=.5, timeout=10):
        self.driver.get(url)
        end_ts = time.time() + timeout
        while time.time() < end_ts:
            try:
                els = self.driver.find_elements(By.XPATH, '//table/tbody/tr')
                if not els:
                    raise NoSuchElementException()
                return els
            except NoSuchElementException:
                if self._has_no_results():
                    logger.debug('no result')
                    return []
                time.sleep(poll_frequency)
        raise Exception('timeout')

    def _get_name(self, text):
        return text.splitlines()[0].strip()

    def parse(self, url):
        for el in self._wait_for_elements(url):
            tds = el.find_elements(By.XPATH, './/td')
            name_el = tds[0]
            name = self._get_name(name_el.text)
            if not name:
                logger.error(f'failed to get {self.id} from:\n'
                    f'{name_el.get_attribute("outerHTML")}')
                continue
            yield name
