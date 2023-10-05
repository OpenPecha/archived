from email import parser

import requests
from pathlib import Path
from bs4 import BeautifulSoup




def scrap_volume(vol_page, vol_num, text_id_walker):
    soup = BeautifulSoup(vol_page, "html.parser")
    toc = soup.find("div", {"class": "volcontent"})
    texts = toc.find_all("dd")
    for text_info in texts:
        if "pp" in text_info.text:
            text_link = text_info.find("a")
            if text_link:
                text_url = f"https://gdamsngagmdzod.tsadra.org{text_link['href']}"
                text_id = f"DNZ-{vol_num}-{text_id_walker:03}"
                text_page = str(requests.get(text_url).text)
                Path(f'./data/dams_ngag_mdzod/{text_id}.html').write_text(text_page, encoding='utf-8')
                text_id_walker += 1
    return text_id_walker

def scrap_wiki_dams_ngag_mdzod():
    text_id_walker = 1
    for vol_num in range(1,19):
        vol_url = f"https://gdamsngagmdzod.tsadra.org/index.php/Gdams_ngag_mdzod_Shechen_Printing/Volume_{vol_num}"
        vol_page = requests.get(vol_url).content
        text_id_walker = scrap_volume(vol_page, vol_num, text_id_walker)
        print(f"{vol_num} scraped..")


if __name__ == "__main__":
    scrap_wiki_dams_ngag_mdzod()
