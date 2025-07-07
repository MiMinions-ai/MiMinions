from setuptools import setup, find_packages

setup(
    name="miminions",
    version="0.0.1",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        # Add your package dependencies here
    ],
    author="Sheng Xiong Ding",
    author_email="shengxio@miminions.ai",
    description="A Python package for MiMinions",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/MiMinions-ai/miminions",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
) 