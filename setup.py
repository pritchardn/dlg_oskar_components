"""Python setup.py for dlg_oskar_components package"""
import io
import os
from setuptools import find_packages, setup


def read(*paths, **kwargs):
    """Read the contents of a text file safely.
    >>> read("dlg_oskar_components", "VERSION")
    '0.1.0'
    >>> read("README.md")
    ...
    """

    content = ""
    with io.open(
        os.path.join(os.path.dirname(__file__), *paths),
        encoding=kwargs.get("encoding", "utf8"),
    ) as open_file:
        content = open_file.read().strip()
    return content


def read_requirements(path):
    return [
        line.strip()
        for line in read(path).split("\n")
        if not line.startswith(('"', "#", "-", "git+"))
    ]


setup(
    name="dlg_oskar_components",
    version=read("dlg_oskar_components", "VERSION"),
    description="Awesome dlg_oskar_components created by pritchardn",
    url="https://github.com/pritchardn/dlg_oskar_components/",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    author="pritchardn",
    packages=find_packages(exclude=["tests", ".github"]),
    install_requires=read_requirements("requirements.txt"),
    entry_points={
        "console_scripts": ["dlg_oskar_components = dlg_oskar_components.__main__:main"]
    },
    extras_require={"test": read_requirements("requirements-test.txt")},
)
