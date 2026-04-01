from setuptools import setup, find_packages

setup(
    name="certbot-dns-aliyun-esa",
    version="0.1.0",
    description="Aliyun ESA DNS Authenticator plugin for Certbot",
    author="Kangyang Ji",
    author_email="kyangconn@outlook.com",
    url="https://github.com/kyangconn/certbot-dns-aliyun-esa",
    packages=find_packages(),
    install_requires=[
        "certbot>=1.0.0",
        "alibabacloud_esa20240910>=1.0.0",
        "alibabacloud_tea_openapi>=0.3.0",
        "alibabacloud_credentials>=0.3.0",
    ],
    entry_points={
        "certbot.plugins": [
            "dns-aliyun-esa = certbot_dns_aliyun_esa:Authenticator",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Plugins",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Security",
        "Topic :: System :: Installation/Setup",
        "Topic :: System :: Networking",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
    ],
)
