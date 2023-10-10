from queue import Queue
from threading import Thread

from img2opf.bdrc.functions import download_image, ocr_image, upload_file

from .s3files import get_bdrc_images


class ClosableQueue(Queue):

    SENTINEL = object()

    def close(self):
        self.put(self.SENTINEL)

    def __iter__(self):
        while True:
            item = self.get()
            try:
                if item is self.SENTINEL:
                    return  # Cause the thread to exit
                yield item
            finally:
                self.task_done()

class StoppableWorker(Thread):
    def __init__(self, func, in_queue, out_queue, other_queue=None):
        super().__init__()
        self.func = func
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.other_queue = other_queue

    def run(self):
        for item in self.in_queue:
            result = self.func(item)
            self.out_queue.put(result)

            if self.func.__name__ == "download_image":
                self.other_queue.put(result)


def run(images, download_func, ocr_func, upload_func):
    download_queue = ClosableQueue()
    ocr_queue = ClosableQueue()
    upload_queue = ClosableQueue()
    done_queue = ClosableQueue()

    threads = [
        StoppableWorker(download_func, download_queue, ocr_queue, other_queue=upload_queue),
        StoppableWorker(ocr_func, ocr_queue, upload_queue),
        StoppableWorker(upload_func, upload_queue, done_queue),
    ]

    for thread in threads:
        thread.start()

    for image in images:
        download_queue.put(image)

    download_queue.close()
    download_queue.join()
    ocr_queue.close()
    ocr_queue.join()
    upload_queue.close()
    upload_queue.join()
    print(done_queue.qsize(), 'items finished')
    print(done_queue.queue)


def start(work):
    images = get_bdrc_images(work)

    run(
        images,
        download_func=download_image,
        ocr_func=ocr_image,
        upload_func=upload_file
    )
