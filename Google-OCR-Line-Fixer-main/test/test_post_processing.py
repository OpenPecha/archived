from post_processing_google_ocr import get_page_content, read_json

if __name__ == "__main__":
    page = read_json('./test/test.json')
    page_content = get_page_content(page)