from email import parser

import requests
from pathlib import Path
from bs4 import BeautifulSoup




def scrap_volume(vol_page):
    soup = BeautifulSoup(vol_page, "html.parser")
    toc = soup.find("div", {"class": "volpage-text-list"})
    texts = toc.find_all("li")
    for text in texts:
        text_link = text.find("a")
        text_url = f"https://rtz.tsadra.org/{text_link['href']}"
        text_id = text_link['title']
        text_page = str(requests.get(text_url).text)
        Path(f'./data/rinchen_terzod/{text_id}.html').write_text(text_page, encoding='utf-8')

def scrap_wiki_rinchen_terzod():
    for vol_num in range(1,73):
        vol_url = f"https://rtz.tsadra.org/index.php/RTZ_Volume_{vol_num}"
        vol_page = requests.get(vol_url).content
        scrap_volume(vol_page)
        print(f"{vol_num} scraped..")


if __name__ == "__main__":
    scrap_wiki_rinchen_terzod()
