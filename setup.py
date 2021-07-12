import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("src/requirements.txt", "r") as fh:
    requirements = fh.read().split('\n')

setuptools.setup(
    name="python-deploy",
    version="3.0.1",
    author="msm, psrok1",
    author_email="info@cert.pl",
    description="Build, push and deploy k8s services with single "
                "deploy.json file to provide common convention for "
                "multiple production services.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=requirements,
    package_dir={"deploy": "src"},
    url="https://gitlab.com/cert.pl/deploy",
    packages=["deploy"],
    include_package_data=True,
    scripts=["util/kubernetes_use_token"],
    entry_points={
        "console_scripts": ["deploy = deploy:main"]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License"
    ],
)
