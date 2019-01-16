import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="consumer",
    version="0.0.1",
    author="Zeeshan Khan",
    author_email="zkhan1093@gmail.com",
    description="A declative way of specifying and consumer APIs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/zkhan93/consumer",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)