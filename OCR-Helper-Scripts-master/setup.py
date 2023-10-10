from setuptools import find_packages, setup

setup(
    name="img2opf",
    version="0.0.1",
    packages=find_packages(),
    install_requires=[
        "google-cloud-vision>=2.7.3, <3.0",
        "openpecha>=0.7.62, <1.0",
        "boto3>=1.16.41, <2.0",
        "Pillow>=8.4.0, <9.0",
    ],
)
