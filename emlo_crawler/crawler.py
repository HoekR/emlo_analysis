from typing import Union, List, Dict
from bs4 import BeautifulSoup
import requests
from requests import Response, RequestException
import re
import time
import random


def get_results_page(results_url: str) -> BeautifulSoup:
    """Input is a URL for an EMLO search results page. Output is a Beautifulsoup object for the results page."""
    response = get_wait_url(results_url)
    if response.status_code != 200:
        raise RequestException(f'Error retrieving results page for url {results_url}')
    page_soup = BeautifulSoup(response.content, 'lxml')
    return page_soup


def get_wait_url(url: str, min_wait: int = 3, random_wait: int = 10) -> Response:
    """Retrieve a page by URL and wait before returning response."""
    # wait at least three seconds plus some random extra seconds
    wait_time = min_wait + random.random() * random_wait
    response = requests.get(url)
    time.sleep(wait_time)
    return response


def clean_cell_content(cell: BeautifulSoup) -> str:
    """Gets the text content of an HTML table cell and returns a stripped text string."""
    return cell.text.replace('•', '').strip()


def parse_results_header(header_row: BeautifulSoup) -> List[str]:
    """Parses the first row from the HTML results table and returns the headers as a list of string."""
    headers = [clean_cell_content(th) for th in header_row.find_all('th')]
    headers[0] = 'Result_num'
    headers[1] = 'Doc_type'
    return headers


class EMLODoc:

    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self.id: Union[None, str] = None
        self.result_num: Union[None, int] = None
        self.type: Union[None, str] = None
        self.date: Union[None, str] = None
        self.author: Union[None, str] = None
        self.origin: Union[None, str] = None
        self.addressee: Union[None, str] = None
        self.destination: Union[None, str] = None
        self.repository: Union[None, str] = None

    def __repr__(self):
        return f"EMLODo('identifier': '{self.id}', 'type': '{self.type}', 'collection_name': '{self.collection_name}')"

    def set_properties(self, doc: Dict[str, Union[str]]):
        """Set properties of EMLODoc based on a dictionary parsed from results page."""
        self.result_num = int(doc['Result_num'])
        self.id = doc['doc_id']
        self.type = doc['Doc_type']
        self.date = doc['Date']
        self.author = doc['Author']
        self.origin = doc['Origin']
        self.addressee = doc['Addressee']
        self.destination = doc['Destination']
        self.repository = doc['Repositories & Versions']

    def json(self) -> Dict[str,Union[str, int]]:
        return {
            'id': self.id,
            'type': self.type,
            'collection': self.collection_name,
            'date': self.date,
            'author': self.author,
            'addressee': self.addressee,
            'origin': self.origin,
            'destination': self.destination,
            'repository': self.repository
        }


class EMLOCrawler:

    def __init__(self):
        self.base_url = 'http://emlo.bodleian.ox.ac.uk/forms/advanced'
        self.collection_name: Union[None, str] = None
        self.search_name: Union[None, str] = None

    def set_collection(self, collection_name: str, search_name: str) -> None:
        self.collection_name = collection_name
        self.search_name = search_name

    def assert_collection_set(self) -> None:
        assert(self.collection_name is not None)
        assert(self.search_name is not None)

    def crawl_collection(self, collection_info: Dict[str, str]) -> List[EMLODoc]:
        """Crawl all results pages for a given EMLO collection."""
        print('crawling collection', collection_info['collection_name'])
        self.set_collection(collection_info['collection_name'], collection_info['search_name'])
        crawl_finished: bool = False
        emlo_docs: List[EMLODoc] = []
        while not crawl_finished:
            start_num = len(emlo_docs)
            print('retrieving results starting from', start_num)
            page_soup = self.get_results_page(start_num=start_num)
            results_data = self.parse_results_page(page_soup)
            emlo_docs += results_data['parsed_results']
            print(len(emlo_docs), 'of', results_data['total_results'], 'retrieved')
            if len(emlo_docs) >= results_data['total_results']:
                crawl_finished = True
        return emlo_docs

    def make_results_page_url(self, start_num: int = 0) -> str:
        """Construct the results page url for a registered collection and a given result start number."""
        self.assert_collection_set()
        params = f"?col_cat={self.search_name}&start={start_num}"
        search_url = self.base_url + params
        return search_url

    def get_results_page(self, start_num: int = 0) -> BeautifulSoup:
        """Gets a results page starting from start_num and returns a BeautifulSoup object."""
        self.assert_collection_set()
        results_url = self.make_results_page_url(start_num=start_num)
        page_soup = get_results_page(results_url)
        return page_soup

    def parse_results_page(self, page_soup: BeautifulSoup) -> Dict[str, Union[int, List[EMLODoc]]]:
        """Parse the results from a page_soup object and return EMLODoc results."""
        results_table = page_soup.find(id='results')
        results_rows = results_table.find_all('tr')
        results = self.parse_results_rows(results_rows)
        try:
            total_results = int(page_soup.find('span', class_='font-18').text.strip().split(' results')[0])
        except ValueError:
            print(page_soup.find('span', class_='font-18').text.strip())
            raise
        return {
            'total_results': total_results,
            'parsed_results': results
        }

    def parse_results_rows(self, results_rows: BeautifulSoup) -> List[EMLODoc]:
        """Input is a list of HTML table rows with EMLO results, output is a list of EMLODoc objects."""
        header_row = results_rows.pop(0)
        headers = parse_results_header(header_row)
        return [self.make_emlo_doc(results_row, headers) for results_row in results_rows]

    def make_emlo_doc(self, results_row: BeautifulSoup, headers: List[str]) -> EMLODoc:
        """Parse a row from the results table of an EMLO results page and return and EMLODoc object."""
        cells = [clean_cell_content(td) for td in results_row.find_all('td')]
        doc = {header: cells[hi] for hi, header in enumerate(headers)}
        doc['doc_id'] = get_result_identifier(results_row)
        emlo_doc = EMLODoc(self.collection_name)
        emlo_doc.set_properties(doc)
        return emlo_doc


def get_result_identifier(results_row: BeautifulSoup) -> str:
    """Extracts the document identifier from the embedded link to the document."""
    link_cell = results_row.find_all('td')[1].find('a')
    url = link_cell['href']
    doc_id = url.split('?')[0].split('/')[3]
    return doc_id


collections = [
    {
        'name': 'Scaliger, Joseph Justus',
        'search_name': 'Scaliger%2C+Joseph+Justus',
        'category': ['classical scholar'],
        'nationality': 'French'
    }
]

