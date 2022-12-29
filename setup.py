import setuptools
import pathlib

setuptools.setup(
    name="Nova",
    version="0.0.0",
    author="Eve.Familia, Inc. | LobeliaTechnologies™",
    description="WebApplication Framework",
    long_description_content_type="text/markdown",
    url="https://github.com/Eve-Familia-Inc/Nova",
    packages=[
        x.parent.as_posix() for x in pathlib.Path(".").glob("**/__init__.py")
    ],
    python_requires='>=3.7'
)
