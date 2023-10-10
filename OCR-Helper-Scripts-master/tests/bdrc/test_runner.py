from img2opf.bdrc.runner import start as ocr_start
from img2opf.bdrc.sync_runner import ocr_bdrc_work


def test_runner_prallel():
    ocr_start(100)

def test_sync_runner():
    ocr_bdrc_work(works=["W22084"], batch_name="test")

if __name__ == "__main__":
    test_runner_prallel()
