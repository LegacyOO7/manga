from typing import List, AsyncIterable
from urllib.parse import urlparse, urljoin, quote, quote_plus

from bs4 import BeautifulSoup

from plugins.client import MangaClient, MangaCard, MangaChapter


class TMOClient(MangaClient):

    base_url = urlparse("https://lectortmo.com/")
    search_url = urljoin(base_url.geturl(), "library")
    search_param = 'title'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
    }

    def __init__(self, *args, name="TMO", **kwargs):
        super().__init__(*args, name=name, headers=self.headers, **kwargs)

    def mangas_from_page(self, page: bytes):
        bs = BeautifulSoup(page, "html.parser")

        cards = bs.find_all("div", {"class": "element"})

        mangas = [card.a for card in cards]
        names = [card.findNext("div", {"class": "thumbnail-title"}).h4.get("title").strip() for card in cards]
        url = [manga.get('href').strip() for manga in mangas]

        images = [str(card.style).split("url('")[1].split("')")[0].strip() for card in cards]

        mangas = [MangaCard(self, *tup) for tup in zip(names, url, images)]

        return mangas

    def chapters_from_page(self, page: bytes, manga: MangaCard = None):
        bs = BeautifulSoup(page, "html.parser")

        div = bs.find("div", {"id": "chapters"})

        lis = div.select("li.list-group-item.upload-link")

        texts = [li.findNext("a").text.strip().replace('\xa0', ' ') for li in lis]
        links = [li.findNext("a", {"class": "btn btn-default btn-sm".split()}).get("href").strip() for li in lis]

        return list(map(lambda x: MangaChapter(self, x[0], x[1], manga, []), zip(texts, links)))

    async def pictures_from_chapters(self, content: bytes):
        bs = BeautifulSoup(content, "html.parser")

        url = bs.find("a", {"title": "Cascada"}).get('href')

        content = await self.get_url(url)

        bs = BeautifulSoup(content, "html.parser")

        ul = bs.find('div', {'class': 'viewer-container container'})

        images = ul.find_all('img')

        images_url = [quote(img.get('data-src'), safe=':/') for img in images]

        return images_url

    async def search(self, query: str = "", page: int = 1) -> List[MangaCard]:
        query = quote_plus(query)

        request_url = f'{self.search_url}?_pg={page}'

        if query:
            request_url += f'&{self.search_param}={query}'

        content = await self.get_url(request_url)

        return self.mangas_from_page(content)

    async def get_chapters(self, manga_card: MangaCard, page: int = 1) -> List[MangaChapter]:

        request_url = f'{manga_card.url}'

        content = await self.get_url(request_url)

        return self.chapters_from_page(content, manga_card)[(page - 1) * 20:page * 20]

    async def iter_chapters(self, manga_url: str) -> AsyncIterable[MangaChapter]:
        manga_card = MangaCard(self, 'temp', manga_url, '')

        request_url = f'{manga_card.url}'

        content = await self.get_url(request_url)

        for chapter in self.chapters_from_page(content, manga_card):
            yield chapter

    async def contains_url(self, url: str):
        return url.startswith(self.base_url.geturl())