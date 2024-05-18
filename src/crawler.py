from concurrent.futures import ThreadPoolExecutor
import logging
import requests
import os
from queue import Queue, Empty

from parser import HtmlDocumentParser


class Crawler:

    def __init__(self):
        self.parser = HtmlDocumentParser()
        self.pool = ThreadPoolExecutor(max_workers=2)
        self.visited_pages = set()
        self.pages_queue = Queue()
        self.headers = [{"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"},
           {"User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"}]


    def parse_links(self, url, response):
        links = self.parser.process_page(url, response)
        for link in links:
            if link not in self.visited_pages:
                self.pages_queue.put(link)

    def parse_results(self, res):
        result = res.result()
        if result and result[1].status_code == 200:
            self.parse_links(result[0], result[1])
        else:
            logging.info(f"Error on getting page for {result[0]}")

    def process_url(self, url):
        try:
            res = requests.get(url, timeout=(3, 30), headers=self.headers[0])
            return url, res
        except Exception as e:
            logging.error(f"Error on getting response for {url}.\n Error message: {e}\n")

    def run(self, init_url):
        self.pages_queue.put(init_url)
        while True:
            try:
                url = self.pages_queue.get(timeout=60)
                if url not in self.visited_pages:
                    self.visited_pages.add(url)
                    job = self.pool.submit(self.process_url, url)
                    job.add_done_callback(self.parse_results)
            except Empty:
                return
            except Exception as e:
                print(e)
                continue


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, filename="logfile", filemode="a+",
                        format="%(asctime)-15s %(levelname)-8s %(message)s")
    crawler = Crawler()
    crawler.run("https://www.hse.ru/sitemap.html")
