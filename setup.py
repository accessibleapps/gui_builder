from setuptools import setup, find_packages

__version__ = "0.26"
__doc__ = """Declarative GUIs"""

setup(
    name="gui_builder",
    version=__version__,
    description=__doc__,
    packages=find_packages(),
    install_requires=["six"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries",
    ],
)
