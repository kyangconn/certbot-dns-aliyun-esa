from __future__ import annotations

from types import SimpleNamespace

import pytest

from certbot_dns_aliyun_esa.esa_client import (
    PAGE_SIZE,
    AliCloudESAClient,
    _domain_suffixes,
    normalize_domain,
)


def _record(record_id: int, name: str):
    return SimpleNamespace(
        record_id=record_id,
        record_name=name,
        record_type="TXT",
        data=SimpleNamespace(value=f"value-{record_id}"),
        ttl=600,
        comment=None,
    )


def _site(site_id: int, name: str):
    return SimpleNamespace(
        site_id=site_id,
        site_name=name,
        status="active",
        coverage="global",
        access_type="NS",
    )


def _client_with_sdk(sdk):
    client = object.__new__(AliCloudESAClient)
    client.client = sdk
    return client


def test_normalize_domain_lowercases_and_strips_dots() -> None:
    assert normalize_domain("  WWW.Example.COM.  ") == "www.example.com"


@pytest.mark.parametrize(
    ("domain", "expected"),
    [
        ("www.example.co.uk", ["www.example.co.uk", "example.co.uk", "co.uk"]),
        ("*.example.com", ["example.com"]),
        ("example.com", ["example.com"]),
        ("localhost", ["localhost"]),
        ("", []),
    ],
)
def test_domain_suffixes_are_listed_longest_first(domain, expected) -> None:
    assert _domain_suffixes(domain) == expected


def test_record_listing_uses_exact_filter_and_follows_pages() -> None:
    class SDK:
        def __init__(self) -> None:
            self.requests = []

        def list_records_with_options(self, request, runtime):
            self.requests.append(request)
            pages = {
                1: [_record(1, "_acme.example.com"), _record(2, "_acme.example.com")],
                2: [_record(3, "_acme.example.com")],
            }
            return SimpleNamespace(
                body=SimpleNamespace(records=pages[request.page_number], total_count=3)
            )

    sdk = SDK()
    client = _client_with_sdk(sdk)

    records = client.list_records(42, "_ACME.example.com.")

    assert [record["record_id"] for record in records] == [1, 2, 3]
    assert [request.page_number for request in sdk.requests] == [1, 2]
    assert all(request.record_match_type == "exact" for request in sdk.requests)
    assert all(request.record_name == "_acme.example.com" for request in sdk.requests)
    assert all(request.type == "TXT" for request in sdk.requests)
    assert all(request.site_id == 42 for request in sdk.requests)


def test_a_short_last_page_ends_pagination() -> None:
    class SDK:
        def __init__(self) -> None:
            self.page_numbers = []

        def list_records_with_options(self, request, runtime):
            self.page_numbers.append(request.page_number)
            pages = {1: [_record(1, "_acme.example.com")], 2: [_record(2, "x")]}
            return SimpleNamespace(
                body=SimpleNamespace(records=pages[request.page_number])
            )

    sdk = SDK()
    client = _client_with_sdk(sdk)
    client.list_records(42, "_acme.example.com")

    # A single record is shorter than PAGE_SIZE, so pagination stops at page 1.
    assert sdk.page_numbers == [1]


def test_site_listing_follows_pages() -> None:
    class SDK:
        def __init__(self) -> None:
            self.requests = []

        def list_sites_with_options(self, request, runtime):
            self.requests.append(request)
            pages = {
                1: [_site(1, "one.example"), _site(2, "two.example")],
                2: [_site(3, "three.example")],
            }
            return SimpleNamespace(
                body=SimpleNamespace(sites=pages[request.page_number], total_count=3)
            )

    sdk = SDK()
    client = _client_with_sdk(sdk)

    sites = client.list_sites("one.example")

    assert [site["site_id"] for site in sites] == [1, 2, 3]
    assert [request.page_number for request in sdk.requests] == [1, 2]
    assert all(request.site_search_type == "exact" for request in sdk.requests)


def test_find_site_tries_longest_exact_domain_suffix_first() -> None:
    client = _client_with_sdk(object())
    queried: list[str] = []

    def list_sites(name):
        queried.append(name)
        if name == "example.co.uk":
            return [{"site_id": 42, "site_name": "example.co.uk"}]
        return []

    client.list_sites = list_sites

    site = client.find_site_by_domain("WWW.Example.CO.UK.")

    assert site == {"site_id": 42, "site_name": "example.co.uk"}
    assert queried == ["www.example.co.uk", "example.co.uk"]


def test_get_site_maps_sdk_response() -> None:
    class SDK:
        def __init__(self) -> None:
            self.request = None

        def get_site_with_options(self, request, runtime):
            self.request = request
            return SimpleNamespace(
                body=SimpleNamespace(site_model=_site(42, "example.com"))
            )

    sdk = SDK()
    client = _client_with_sdk(sdk)

    site = client.get_site(42)

    assert sdk.request.site_id == 42
    assert site == {
        "site_id": 42,
        "site_name": "example.com",
        "status": "active",
        "coverage": "global",
        "access_type": "NS",
    }


def test_get_site_rejects_an_empty_response() -> None:
    class SDK:
        def get_site_with_options(self, request, runtime):
            return SimpleNamespace(body=SimpleNamespace(site_model=None))

    client = _client_with_sdk(SDK())

    with pytest.raises(RuntimeError, match="no site"):
        client.get_site(42)


def test_create_and_delete_record_build_expected_sdk_requests() -> None:
    class SDK:
        def __init__(self) -> None:
            self.created = None
            self.deleted = None

        def create_record_with_options(self, request, runtime):
            self.created = request
            return SimpleNamespace(body=SimpleNamespace(record_id="123"))

        def delete_record_with_options(self, request, runtime):
            self.deleted = request

    sdk = SDK()
    client = _client_with_sdk(sdk)

    record_id = client.create_txt_record(42, "_ACME.Example.com.", "challenge", ttl=300)
    client.delete_record(record_id)

    assert record_id == 123
    assert sdk.created.site_id == 42
    assert sdk.created.record_name == "_acme.example.com"
    assert sdk.created.type == "TXT"
    assert sdk.created.ttl == 300
    assert sdk.created.proxied is False
    assert sdk.created.comment == "Certbot DNS-01 challenge"
    assert sdk.created.data.value == "challenge"
    assert sdk.deleted.record_id == 123


def test_create_record_requires_a_record_id() -> None:
    class SDK:
        def create_record_with_options(self, request, runtime):
            return SimpleNamespace(body=SimpleNamespace(record_id=None))

    client = _client_with_sdk(SDK())

    with pytest.raises(RuntimeError, match="no record ID"):
        client.create_txt_record(42, "_acme.example.com", "challenge", ttl=600)


def test_page_size_is_used_for_requests() -> None:
    class SDK:
        def __init__(self) -> None:
            self.requests = []

        def list_records_with_options(self, request, runtime):
            self.requests.append(request)
            return SimpleNamespace(body=SimpleNamespace(records=[]))

    sdk = SDK()
    _client_with_sdk(sdk).list_records(42, "_acme.example.com")

    assert sdk.requests[0].page_size == PAGE_SIZE
