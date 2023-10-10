class S3Image:
    """class representing bdrc S3 archive image file"""

    __slots__ = ["name", "download_url", "upload_url", "local_path"]

    def __init__(self, name: str, download_url: str, upload_url: str, local_path: str):
        self.name = name
        self.download_url = download_url
        self.upload_url = upload_url
        self.local_path = local_path

class S3OCROutput:
    """class representing bdrc s3 ocr output file"""

    def __init__(self, name: str, upload_url: str, local_path: str):
        self.name = name
        self.upload_url = upload_url
        self.local_path = local_path



def get_bdrc_images(work):
    for i in range(10):
        yield S3Image(
            name=i,
            download_url=f"({i} download_url",
            upload_url=f"({i}) upload url",
            local_path=f"imagefile({i}).png"
        )


