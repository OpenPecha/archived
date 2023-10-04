import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="opmodels",
    version="0.0.1",
    author="Tenzin",
    author_email="ten13zin@gmail.com",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "models"},
    packages=setuptools.find_packages(where="models"),
    python_requires=">=3.6",
)