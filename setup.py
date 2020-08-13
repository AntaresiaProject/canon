from setuptools import setup, find_packages
setup(
    name="DataMapping",
    version="0.1",
    packages=find_packages(),

    install_requires=["docutils>=0.3"],
    # metadata to display on PyPI
    author="Adam Haskell",
    author_email="a.haskell+pypi@gmail.com",
    description="Readme should go here",
    keywords="hello world example examples",
    url="https://github.com/AntaresiaProject/datamapping",  
    project_urls={
        "Bug Tracker": "https://github.com/AntaresiaProject/datamapping",
        "Documentation": "https://github.com/AntaresiaProject/datamapping",
        "Source Code": "https://github.com/AntaresiaProject/datamapping",
    },
    classifiers=[
        "License :: OSI Approved :: MIT"
    ]

    # could also include long_description, download_url, etc.
)