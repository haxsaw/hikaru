from setuptools import setup
from hikaru import __version__


def get_long_desc():
    return open('README.rst', 'r').read()


def get_requirements():
    lines = open('requirements.txt', 'r').readlines()
    reqs = [line.strip() for line in lines if line]
    return reqs


setup(
    name="hikaru",
    version=__version__,
    packages=["hikaru", "hikaru.model"],
    description="Hikaru allows you to smoothly move between Kubernetes YAML "
                "Python objects, and Python source, any direction",
    long_description=get_long_desc(),
    author="Tom Carroll",
    author_email="tcarroll@incisivetech.co.uk",
    url=f"https://github.com/haxsaw/hikaru/archive/{__version__}.tar.gz",
    keywords=["Kubernetes", "modelling", "YAML", "JSON", "modeling",
              "translate", "translator", "reformatter", "transform"],
    install_requires=get_requirements(),
    classifiers=[],
    license="MIT"
)
