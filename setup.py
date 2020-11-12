import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="Nova-EveFamilia",
    version="0.0.1",
    install_requires=[
        "asyncio", "ssl", "glob", "hashlib", "base64"
    ],
    author="Eve.Familia, Inc.",
    author_email="eve@eve.ninja",
    description="WebApplication Framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Eve-Familia-Inc/Nova",
    packages=setuptools.find_packages("src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Programming Language :: Python :: 3.9",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: Japanese",
        "Operating System :: OS Independent",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers"
    ],
    python_requires='>=3.7'
)
