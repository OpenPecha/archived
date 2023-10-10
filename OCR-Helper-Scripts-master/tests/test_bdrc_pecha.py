from img2opf.pecha import BDRCS3Image, BDRCVolume


def test_get_images():
    volume = BDRCVolume(prefix="bdr:I0886")

    images = volume.get_images()

    assert images

def test_bdrc_s3_image_url():
    image = BDRCS3Image(
        prefix="Works/60/W22084/images/W22084-I0886",
        file={"filename":"08860001.tif"}
    )

    assert image.url == "Works/60/W22084/images/W22084-I0886/08860001.tif"
