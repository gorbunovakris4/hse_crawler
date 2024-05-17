from bs4 import BeautifulSoup
from bs4.element import Tag

from copy import deepcopy

import json
import io
import logging
import re
import sys


class Page:
    def __init__(self, url, title, desc):
        self.url = url
        self.title = title
        self.description = desc
        self.data = []
        self.links = []
        self.content = ""


class HeaderSection:
    def __init__(self, level, content):
        self.level = level
        self.content = content
        self.responses = []


class PageEncoder(json.JSONEncoder):
    def default(self, page_obj):
        header_data = []
        for header_obj in page_obj.data:
            header_data.append(
                {
                    "level": header_obj.level,
                    "content": header_obj.content,
                    "responses": header_obj.responses,
                }
            )
        return {
            "url": page_obj.url,
            "title": page_obj.title,
            "description": page_obj.description,
            "data": header_data,
            "links": page_obj.links,
            "content": page_obj.content
        }


class HtmlDocumentParser:
    def __init__(self):
        config = {}
        try:
            with open('crawler_config.json', 'r') as config_file:
                config = json.load(config_file)
        except Exception as e:
            print(f"Invalid crawler_config file. Using default configuration")

        if 'parser' in config and config['parser'] in ['lxml', 'html5lib', 'html.parser']:
            self.parser = config['parser']
        else:
            self.parser = 'lxml'

        if 'header_tags' in config:
            self.header_tags = config['header_tags']
        else:
            self.header_tags = ['h1', 'h2']

        if 'text_tags' in config:
            self.text_tags = config['text_tags']
        else:
            self.text_tags = ['p', 'span', 'li', 'a', 'strong', 'h3', 'h4', 'h5', 'h6']

        if "save_website_content" in config and config["save_website_content"] == 1:
            self.save_website_content = True
        else:
            self.save_website_content = False

        if "save_header_article_pairs" in config and config["save_header_article_pairs"] == 1:
            self.save_header_article_pairs = True
        else:
            self.save_header_article_pairs = False

        if "main_classes" in config:
            self.main_classes = config["main_classes"]
        else:
            self.main_classes = ["main", "content"]

        if "black_list_classes" in config:
            self.black_list_classes = config["black_list_classes"]
        else:
            self.black_list_classes = ["sidebar", "footer"]

        if "black_list_tags" in config:
            self.black_list_tags = config["black_list_tags"]
        else:
            self.black_list_tags = ["footer"]

        if "domain" in config:
            self.url_regexp = f"(https?\:\/\/)([A-Za-z0-9\.\/]*)\.?{config['domain']}\.ru\/?[A-Za-z0-9_\.~\-\/]*"
        else:
            self.url_regexp = "(https?\:\/\/)([A-Za-z0-9\.\/]*)\.?hse\.ru\/?[A-Za-z0-9_\.~\-\/]*"

    @staticmethod
    def find_title(soup):
        title = soup.find("meta", property="title")
        if title is not None:
            title = title["content"].strip()
        if title is None:
            title = soup.title.string
        return title

    @staticmethod
    def find_desc(soup):
        description = soup.find("meta", property="description")
        if description is not None:
            description = description["content"].strip()
        return description

    @staticmethod
    def get_cleared_text(elem):
        return ". ".join([x.strip() for x in elem.get_text(separator='\n').split('\n') if x.strip() != ""])

    def process_elem(self, elem, header_obj):
        for child in elem.children:
            if not isinstance(child, Tag):
                continue
            if child.name in self.header_tags:
                # stop at next header
                break
            if not child.find(self.header_tags):
                header_obj.responses.append(self.get_cleared_text(child))
            else:
                self.process_elem(child, header_obj)
                break

    def process_header(self, header_tag, page):
        header = HeaderSection(header_tag.name[1], self.get_cleared_text(header_tag))
        page.data.append(header)
        for sibling in header_tag.next_siblings:
            if not isinstance(sibling, Tag):
                continue
            if sibling.name in self.header_tags:
                # stop at next header
                break
            if sibling.name in self.text_tags:
                header.responses.append(self.get_cleared_text(sibling))

            else:
                if sibling.find(self.header_tags):
                    self.process_elem(sibling, header)
                    break
                else:
                    header.responses.append(self.get_cleared_text(sibling))

    def find_all_links_by_template(self, main_content):
        urls = set()
        for link in main_content.find_all('a', href=True):
            url = link['href']
            url_without_params = re.match(self.url_regexp, url)
            if url_without_params is not None:
                urls.add(url_without_params.group(0))
        return urls

    def check_classes(self, elem):
        if "class" not in elem:
            return True
        for class_ in self.black_list_classes:
            if class_ in elem["class"]:
                return False
        return True

    def process_main_content(self, soup, page, save_text=False):
        for class_ in self.main_classes:
            for main_content in soup.find_all(class_=class_):
                if save_text:
                    page.content = self.get_cleared_text(main_content)
                page.links = list(self.find_all_links_by_template(main_content))
                break
        if len(page.links) == 0:
            body = soup.find("body")
            links = set()
            content = ""
            for elem in body.children:
                if isinstance(elem, Tag):
                    if self.check_classes(elem):
                        content += self.get_cleared_text(elem)
                        links |= self.find_all_links_by_template(elem)
            if save_text:
                page.content = content
            page.links = list(links)

    @staticmethod
    def save_page_data(page):
        hash_url = hash(page.url)
        hash_url += sys.maxsize + 1
        with io.open(f"pages/{hash_url}.json", "w", encoding='utf-8') as f:
            json.dump(page, f, ensure_ascii=False, cls=PageEncoder)

    def process_page(self, url, response):
        new_links = []
        try:
            soup = BeautifulSoup(response.text, self.parser)
            page = Page(url, self.find_title(soup), self.find_desc(soup))

            if self.save_header_article_pairs:
                for header in soup.find_all(self.header_tags):
                    self.process_header(header, page)

            self.process_main_content(soup, page, save_text=self.save_website_content)
            new_links = deepcopy(page.links)
            self.save_page_data(page)
        except Exception as e:
            logging.error(f"Error on parsing {url}.\n Error message: {e}\n")
        finally:
            return new_links
