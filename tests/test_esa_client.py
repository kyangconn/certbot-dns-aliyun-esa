from __future__ import annotations

from types import SimpleNamespace

from certbot_dns_aliyun_esa.esa_client import AliCloudESAClient


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
    client.runtime = object()
    return client


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

    records = client.get_site_records(
        42, "_ACME.example.com.", page_size=2
    )

    assert [record["record_id"] for record in records] == [1, 2, 3]
    assert [request.page_number for request in sdk.requests] == [1, 2]
    assert all(request.record_match_type == "exact" for request in sdk.requests)
    assert all(request.record_name == "_acme.example.com" for request in sdk.requests)


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

    sites = client.get_sites(page_size=2)

    assert [site["site_id"] for site in sites] == [1, 2, 3]
    assert [request.page_number for request in sdk.requests] == [1, 2]


def test_find_site_tries_longest_exact_domain_suffix_first() -> None:
    client = _client_with_sdk(object())
    queried: list[tuple[str, str, int]] = []

    def get_sites(*, name, search_mode, page_size):
        queried.append((name, search_mode, page_size))
        if name == "example.co.uk":
            return [{"site_id": 42, "site_name": "example.co.uk"}]
        return []

    client.get_sites = get_sites

    site = client.find_site_by_domain("WWW.Example.CO.UK.")

    assert site == {"site_id": 42, "site_name": "example.co.uk"}
    assert [item[0] for item in queried] == ["www.example.co.uk", "example.co.uk"]
    assert all(item[1] == "exact" for item in queried)


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

    record_id = client.add_txt_record(
        42, "_ACME.Example.com.", "challenge", ttl=300, comment="certbot"
    )
    client.delete_record(record_id)

    assert record_id == 123
    assert sdk.created.site_id == 42
    assert sdk.created.record_name == "_acme.example.com"
    assert sdk.created.type == "TXT"
    assert sdk.created.ttl == 300
    assert sdk.created.proxied is False
    assert sdk.created.data.value == "challenge"
    assert sdk.deleted.record_id == 123
