import asyncio
import re
import threading

from bs4 import BeautifulSoup
import httpx

from JobSpy.src.jobspy.scrapers.utils import (
    create_session,
)

headers_initial = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-US,en;q=0.9",
    "priority": "u=0, i",
    "referer": "https://www.google.com/",
    "sec-ch-prefers-color-scheme": "dark",
    "sec-ch-ua": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
    "sec-ch-ua-arch": '"arm"',
    "sec-ch-ua-bitness": '"64"',
    "sec-ch-ua-form-factors": '"Desktop"',
    "sec-ch-ua-full-version": '"130.0.6723.58"',
    "sec-ch-ua-full-version-list": '"Chromium";v="130.0.6723.58", "Google Chrome";v="130.0.6723.58", "Not?A_Brand";v="99.0.0.0"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-model": '""',
    "sec-ch-ua-platform": '"macOS"',
    "sec-ch-ua-platform-version": '"15.0.1"',
    "sec-ch-ua-wow64": "?0",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "x-browser-channel": "stable",
    "x-browser-copyright": "Copyright 2024 Google LLC. All rights reserved.",
    "x-browser-year": "2024",
}


class Scraper:

    def __init__(self, method, _url):
        self.method = method
        self._url = _url

    def get_url(self, **kwargs):
        return self._url.format(**kwargs, method=self.method)

    async def get_response(self, client):
        return await client.get(self.get_url())

    async def handle(self, response):
        return response.text

    async def scrape(self, client):
        response = await self.get_response(client)
        proxies = await self.handle(response)
        pattern = re.compile(r"\d{1,3}(?:\.\d{1,3}){3}(?::\d{1,5})?")
        return re.findall(pattern, proxies)


# From spys.me
class SpysMeScraper(Scraper):

    def __init__(self, method):
        super().__init__(method, "https://spys.me/{mode}.txt")

    def get_url(self, **kwargs):
        mode = "proxy" if self.method == "http" else "socks" if self.method == "socks" else "unknown"
        if mode == "unknown":
            raise NotImplementedError
        return super().get_url(mode=mode, **kwargs)


# From proxyscrape.com
class ProxyScrapeScraper(Scraper):

    def __init__(self, method, timeout=1000, country="All"):
        self.timout = timeout
        self.country = country
        super().__init__(method,
                         "https://api.proxyscrape.com/?request=getproxies"
                         "&proxytype={method}"
                         "&timeout={timout}"
                         "&country={country}")

    def get_url(self, **kwargs):
        return super().get_url(timout=self.timout, country=self.country, **kwargs)


# From geonode.com - A little dirty, grab http(s) and socks but use just for socks
class GeoNodeScraper(Scraper):

    def __init__(self, method, limit="500", page="1", sort_by="lastChecked", sort_type="desc"):
        self.limit = limit
        self.page = page
        self.sort_by = sort_by
        self.sort_type = sort_type
        super().__init__(method,
                         "https://proxylist.geonode.com/api/proxy-list?"
                         "&limit={limit}"
                         "&page={page}"
                         "&sort_by={sort_by}"
                         "&sort_type={sort_type}")

    def get_url(self, **kwargs):
        return super().get_url(limit=self.limit, page=self.page, sort_by=self.sort_by, sort_type=self.sort_type,
                               **kwargs)


# From proxy-list.download
class ProxyListDownloadScraper(Scraper):

    def __init__(self, method, anon):
        self.anon = anon
        super().__init__(method, "https://www.proxy-list.download/api/v1/get?type={method}&anon={anon}")

    def get_url(self, **kwargs):
        return super().get_url(anon=self.anon, **kwargs)


# For websites using table in html
class GeneralTableScraper(Scraper):

    async def handle(self, response):
        soup = BeautifulSoup(response.text, "html.parser")
        proxies = set()
        table = soup.find("table", attrs={"class": "table table-striped table-bordered"})
        for row in table.findAll("tr"):
            count = 0
            proxy = ""
            for cell in row.findAll("td"):
                if count == 1:
                    proxy += ":" + cell.text.replace("&nbsp;", "")
                    proxies.add(proxy)
                    break
                proxy += cell.text.replace("&nbsp;", "")
                count += 1
        return "\n".join(proxies)


# For websites using div in html
class GeneralDivScraper(Scraper):

    async def handle(self, response):
        soup = BeautifulSoup(response.text, "html.parser")
        proxies = set()
        table = soup.find("div", attrs={"class": "list"})
        for row in table.findAll("div"):
            count = 0
            proxy = ""
            for cell in row.findAll("div", attrs={"class": "td"}):
                if count == 2:
                    break
                proxy += cell.text + ":"
                count += 1
            proxy = proxy.rstrip(":")
            proxies.add(proxy)
        return "\n".join(proxies)


# For scraping live proxylist from github
class GitHubScraper(Scraper):

    async def handle(self, response):
        tempproxies = response.text.split("\n")
        proxies = set()
        for prxy in tempproxies:
            if self.method in prxy:
                proxies.add(prxy.split("//")[-1])

        return "\n".join(proxies)


def is_https_working(proxy):
    try:
        params = {"q": "jobs in Texas USA", "udm": "8"}
        response = create_session(proxies=proxy, is_tls=False, ca_cert=None, has_retry=False, clear_cookies=True,
                                  delay=1).get(
            'https://google.com', headers=headers_initial, timeout=5, params=params)
        if response.status_code == 200:
            return True
    except Exception as e:
        return False
    return False


def check(proxies):
    print(f"Checking {len(proxies)} proxies")
    valid_proxies = []

    def check_proxy(proxy):
        valid = is_https_working(proxy)
        valid_proxies.extend([proxy] if valid else [])

    threads = []
    for p_ in proxies:
        t = threading.Thread(target=check_proxy, args=(p_,))
        threads.append(t)

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    print(f"Found {len(valid_proxies)} valid proxies" + " ")
    return valid_proxies


scrapers = [
    SpysMeScraper("http"),
    SpysMeScraper("socks"),
    ProxyScrapeScraper("http"),
    ProxyScrapeScraper("socks5"),
    GeoNodeScraper("socks"),
    ProxyListDownloadScraper("https", "elite"),
    ProxyListDownloadScraper("http", "elite"),
    ProxyListDownloadScraper("http", "transparent"),
    ProxyListDownloadScraper("http", "anonymous"),
    GeneralTableScraper("https", "http://sslproxies.org"),
    GeneralTableScraper("http", "http://free-proxy-list.net"),
    GeneralTableScraper("http", "http://us-proxy.org"),
    GeneralTableScraper("https", "https://proxy-tools.com/proxy/https"),
    GeneralTableScraper("socks", "http://socks-proxy.net"),
    GeneralDivScraper("http", "https://freeproxy.lunaproxy.com/"),
    GitHubScraper("http", "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/all/data.txt"),
    GitHubScraper("socks4", "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/all/data.txt"),
    GitHubScraper("socks5", "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/all/data.txt"),
    GitHubScraper("https",
                  "https://raw.githubusercontent.com/proxifly/free-proxy-list/refs/heads/main/proxies/protocols/https/data.txt"),
    GitHubScraper("http", "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/all.txt"),
    GitHubScraper("socks", "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/all.txt"),
    GitHubScraper("https", "https://raw.githubusercontent.com/zloi-user/hideip.me/main/https.txt"),
    GitHubScraper("http", "https://raw.githubusercontent.com/zloi-user/hideip.me/main/http.txt"),
    GitHubScraper("socks4", "https://raw.githubusercontent.com/zloi-user/hideip.me/main/socks4.txt"),
    GitHubScraper("socks5", "https://raw.githubusercontent.com/zloi-user/hideip.me/main/socks5.txt"),
]


def verbose_print(verbose, message):
    if verbose:
        # print(message)
        pass


async def scrape(methods):
    proxy_scrapers = [s for s in scrapers if s.method in methods]
    if not proxy_scrapers:
        raise ValueError("Method not supported")
    proxies = []

    tasks = []
    client = httpx.AsyncClient(follow_redirects=True)

    async def scrape_scraper(scraper):
        try:
            proxies.extend(await scraper.scrape(client))
        except Exception:
            pass

    for scraper in proxy_scrapers:
        tasks.append(asyncio.ensure_future(scrape_scraper(scraper)))

    await asyncio.gather(*tasks)
    await client.aclose()

    return set(proxies)


def get_valid_proxies(protocols, batch_size, min_valid_size):
    proxies_set = asyncio.run(scrape(protocols))
    all_proxies = list(proxies_set)
    accumulated_valid_proxies = set()

    for start_index in range(0, len(all_proxies), batch_size):
        end_index = start_index + batch_size
        current_batch = all_proxies[start_index:end_index]

        valid_proxies = check(current_batch)
        accumulated_valid_proxies.update(valid_proxies)

        if len(accumulated_valid_proxies) >= min_valid_size:
            return list(accumulated_valid_proxies)

    return []
