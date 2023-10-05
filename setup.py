from setuptools import setup

__version__ = "1.2.0"


def get_long_desc():
    return open('README.rst', 'r').read()


def get_requirements():
    lines = open('requirements.txt', 'r').readlines()
    reqs = [line.strip() for line in lines if line.strip()]
    return reqs


setup(
    name="hikaru",
    version=__version__,
    packages=[],
    description="Hikaru allows you to smoothly move between Kubernetes YAML, "
                "Python objects, and Python source, in any direction",
    long_description=get_long_desc(),
    long_description_content_type="text/x-rst",
    author="Tom Carroll",
    author_email="tcarroll@incisivetech.co.uk",
    url="https://github.com/haxsaw/hikaru",
    download_url=f"https://github.com/haxsaw/hikaru/archive/{__version__}.tar.gz",
    keywords=["Kubernetes", "modelling", "YAML", "JSON", "modeling",
              "translate", "translator", "reformatter", "transform"],
    install_requires=get_requirements(),
    classifiers=["Development Status :: 4 - Beta",
                 "Intended Audience :: Developers",
                 "Intended Audience :: Financial and Insurance Industry",
                 "Intended Audience :: Information Technology",
                 "License :: OSI Approved :: MIT License",
                 "Operating System :: OS Independent",
                 "Programming Language :: Python :: 3 :: Only",
                 "Programming Language :: Python :: 3.7",
                 "Programming Language :: Python :: 3.8",
                 "Programming Language :: Python :: 3.9",
                 "Programming Language :: Python :: 3.10",
                 "Programming Language :: Python :: Implementation",
                 "Topic :: Software Development",
                 "Topic :: Software Development :: Code Generators",
                 "Topic :: Software Development :: Libraries",
                 "Topic :: Software Development :: Libraries :: Python Modules",
                 "Topic :: Text Processing :: Markup",
                 "Topic :: Utilities",
                 "Typing :: Typed"],
    license="MIT"
)
