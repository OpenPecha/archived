import os
import socket
from collections import defaultdict
from pathlib import Path

import boto3
import rdflib
from rdflib.namespace import Namespace, NamespaceManager

os.environ["AWS_SHARED_CREDENTIALS_FILE"] = "~/.aws/credentials"

# S3 config
ARCHIVE_BUCKET = "archive.tbrc.org"
OCR_OUTPUT_BUCKET = "ocr.bdrc.io"
S3 = boto3.resource("s3")
S3_client = boto3.client("s3")
archive_bucket = S3.Bucket(ARCHIVE_BUCKET)
ocr_output_bucket = S3.Bucket(OCR_OUTPUT_BUCKET)

# URI config
BDR = Namespace("http://purl.bdrc.io/resource/")
NSM = NamespaceManager(rdflib.Graph())
NSM.bind("bdr", BDR)

# s3 bucket directory config
SERVICE = "vision"
BATCH_PREFIX = "batch"
IMAGES = "images"
OUTPUT = "output"
INFO_FN = "info.json"

# local directory config
DATA_PATH = Path(os.getenv("BDRC_OCR_DATA_PATH", "./archive"))
IMAGES_BASE_DIR = DATA_PATH / IMAGES
OCR_BASE_DIR = DATA_PATH / OUTPUT
CHECK_POINT_FN = DATA_PATH / "checkpoint.json"

HOSTNAME = socket.gethostname()

# Checkpoint config
CHECK_POINT = defaultdict(list)
COLLECTION = "collection"
WORK = "work"
VOL = "imagegroup"
last_work = None
last_vol = None

# Debug config
DEBUG = {"status": False}
