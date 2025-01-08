from setuptools import setup, find_packages

setup(
    name="autodocstring",  # Replace with your package name
    version="0.1.2",
    description="A Python package for generating docstrings automatically.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/eduardonery1/autodocstring",  # Your repo URL
    author="Your Name",
    author_email="your_email@example.com",
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(),
    python_requires=">=3.6",
    install_requires=[
        # Add your dependencies here
        "python-dotenv",
        "google-generativeai"
    ],
    entry_points={
        "console_scripts": [
            "autodocstring=autodocstring.autodocstring:main",  # CLI command         
            ]
    },
)

