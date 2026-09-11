from __future__ import annotations

import os
from types import SimpleNamespace

import pytest
from certbot import errors

from certbot_dns_aliyun_esa import dns_aliyun_esa
from certbot_dns_aliyun_esa.dns_aliyun_esa import Authenticator, _AliCloudESAHelper


def _config(credentials_file: str, *, site_id: int | None = None, ttl: int = 600):
    return SimpleNamespace(
        dns_aliyun_esa_credentials=credentials_file,
        dns_aliyun_esa_site_id=site_id,
        dns_aliyun_esa_ttl=ttl,
        dns_aliyun_esa_propagation_seconds=0,
    )


def _credentials_file(tmp_path, content: str) -> str:
    path = tmp_path / "credentials.ini"
    path.write_text(content, encoding="utf-8")
    os.chmod(path, 0o600)
    return str(path)


@pytest.mark.parametrize(
    ("id_key", "secret_key"),
    [
        ("access_key_id", "access_key_secret"),
        ("access_id", "access_secret"),
    ],
)
def test_credentials_accept_canonical_and_legacy_names(
    tmp_path, id_key: str, secret_key: str
) -> None:
    credentials_file = _credentials_file(
        tmp_path,
        f"dns_aliyun_esa_{id_key} = id\ndns_aliyun_esa_{secret_key} = secret\n",
    )
    authenticator = Authenticator(_config(credentials_file), "dns-aliyun-esa")

    authenticator._setup_credentials()

    assert authenticator.credentials is not None
    assert Authenticator._credential(authenticator.credentials, "access_key_id") == "id"
    assert (
        Authenticator._credential(authenticator.credentials, "access_key_secret")
        == "secret"
    )


def test_credentials_require_both_access_key_values(tmp_path) -> None:
    credentials_file = _credentials_file(
        tmp_path, "dns_aliyun_esa_access_key_id = id\n"
    )
    authenticator = Authenticator(_config(credentials_file), "dns-aliyun-esa")

    with pytest.raises(errors.PluginError, match="access_key_secret"):
        authenticator._setup_credentials()


def test_invalid_site_id_in_credentials_is_rejected(tmp_path) -> None:
    credentials_file = _credentials_file(
        tmp_path,
        "dns_aliyun_esa_access_key_id = id\n"
        "dns_aliyun_esa_access_key_secret = secret\n"
        "dns_aliyun_esa_site_id = not-a-number\n",
    )
    authenticator = Authenticator(_config(credentials_file), "dns-aliyun-esa")

    with pytest.raises(errors.PluginError, match="Invalid ESA site ID"):
        authenticator._setup_credentials()


def test_cli_site_id_takes_precedence_and_helper_is_cached(
    tmp_path, monkeypatch
) -> None:
    credentials_file = _credentials_file(
        tmp_path,
        "dns_aliyun_esa_access_key_id = id\n"
        "dns_aliyun_esa_access_key_secret = secret\n"
        "dns_aliyun_esa_site_id = 111\n",
    )
    created_with: list[tuple[str, str]] = []

    class FakeClient:
        def __init__(self, access_key_id: str, access_key_secret: str) -> None:
            created_with.append((access_key_id, access_key_secret))

    monkeypatch.setattr(dns_aliyun_esa, "AliCloudESAClient", FakeClient)
    authenticator = Authenticator(
        _config(credentials_file, site_id=222), "dns-aliyun-esa"
    )
    authenticator._setup_credentials()

    first = authenticator._get_esa_helper()
    second = authenticator._get_esa_helper()

    assert first is second
    assert first.site_id == 222
    assert created_with == [("id", "secret")]


@pytest.mark.parametrize(("site_id", "ttl"), [(0, 600), (None, 2)])
def test_invalid_numeric_options_fail_before_api_use(
    tmp_path, monkeypatch, site_id: int | None, ttl: int
) -> None:
    credentials_file = _credentials_file(
        tmp_path,
        "dns_aliyun_esa_access_key_id = id\n"
        "dns_aliyun_esa_access_key_secret = secret\n",
    )
    monkeypatch.setattr(dns_aliyun_esa, "AliCloudESAClient", object)
    authenticator = Authenticator(
        _config(credentials_file, site_id=site_id, ttl=ttl), "dns-aliyun-esa"
    )
    authenticator._setup_credentials()

    with pytest.raises(errors.PluginError):
        authenticator._get_esa_helper()


def test_helper_requires_credentials_before_use(tmp_path) -> None:
    credentials_file = _credentials_file(
        tmp_path, "dns_aliyun_esa_access_key_id = id\n"
    )
    authenticator = Authenticator(_config(credentials_file), "dns-aliyun-esa")

    with pytest.raises(errors.PluginError, match="have not been configured"):
        authenticator._get_esa_helper()


def test_configured_credentials_site_id_is_used(tmp_path, monkeypatch) -> None:
    credentials_file = _credentials_file(
        tmp_path,
        "dns_aliyun_esa_access_key_id = id\n"
        "dns_aliyun_esa_access_key_secret = secret\n"
        "dns_aliyun_esa_site_id = 111\n",
    )
    monkeypatch.setattr(dns_aliyun_esa, "AliCloudESAClient", lambda *_: None)
    authenticator = Authenticator(_config(credentials_file), "dns-aliyun-esa")
    authenticator._setup_credentials()

    assert authenticator._get_esa_helper().site_id == 111


class FakeRecordClient:
    def __init__(self) -> None:
        self.find_domains: list[str] = []
        self.created: list[tuple[int, str, str, int]] = []
        self.deleted: list[int] = []
        self.list_calls: list[str] = []
        self.records: list[dict] = []
        self.site_access_type = "NS"

    def find_site_by_domain(self, domain: str) -> dict:
        self.find_domains.append(domain)
        site_id = 43 if domain.endswith("other.example") else 42
        return {
            "site_id": site_id,
            "site_name": domain,
            "access_type": self.site_access_type,
        }

    def get_site(self, site_id: int) -> dict:
        return {
            "site_id": site_id,
            "site_name": "example.com",
            "access_type": self.site_access_type,
        }

    def list_records(self, site_id: int, record_name: str) -> list[dict]:
        self.list_calls.append(record_name)
        return list(self.records)

    def create_txt_record(
        self, site_id: int, record_name: str, value: str, ttl: int
    ) -> int:
        record_id = len(self.created) + 1
        self.created.append((site_id, record_name, value, ttl))
        return record_id

    def delete_record(self, record_id: int) -> None:
        self.deleted.append(record_id)


def _helper(
    monkeypatch, *, site_id: int | None = None
) -> tuple[_AliCloudESAHelper, FakeRecordClient]:
    fake_client = FakeRecordClient()
    monkeypatch.setattr(
        dns_aliyun_esa, "AliCloudESAClient", lambda _key_id, _secret: fake_client
    )
    return _AliCloudESAHelper("id", "secret", site_id=site_id), fake_client


def test_helper_discovers_site_from_certificate_domain(monkeypatch) -> None:
    helper, client = _helper(monkeypatch)

    helper.add_txt_record(
        "www.example.co.uk", "_acme-challenge.www.example.co.uk.", "value"
    )

    assert client.find_domains == ["www.example.co.uk"]
    assert client.created == [(42, "_acme-challenge.www.example.co.uk", "value", 600)]


def test_site_lookup_is_cached_across_challenges(monkeypatch) -> None:
    helper, client = _helper(monkeypatch)

    helper.add_txt_record("example.com", "_acme-challenge.example.com", "one")
    helper.add_txt_record("example.com", "_acme-challenge.example.com", "two")

    assert client.find_domains == ["example.com"]


@pytest.mark.parametrize("site_id", [None, 42])
def test_helper_rejects_cname_access_sites(monkeypatch, site_id: int | None) -> None:
    helper, client = _helper(monkeypatch, site_id=site_id)
    client.site_access_type = "CNAME"

    with pytest.raises(errors.PluginError, match="require an NS-access ESA site"):
        helper.add_txt_record("example.com", "_acme-challenge.example.com", "value")

    assert client.created == []


def test_explicit_site_id_skips_discovery(monkeypatch) -> None:
    helper, client = _helper(monkeypatch, site_id=42)

    helper.add_txt_record("example.com", "_acme-challenge.example.com", "value")

    assert client.find_domains == []
    assert client.created == [(42, "_acme-challenge.example.com", "value", 600)]


def test_record_cache_distinguishes_parallel_challenge_values(monkeypatch) -> None:
    helper, client = _helper(monkeypatch, site_id=42)

    helper.add_txt_record("example.com", "_acme-challenge.example.com", "first")
    helper.add_txt_record("example.com", "_acme-challenge.example.com", "second")
    helper.del_txt_record("example.com", "_acme-challenge.example.com", "second")
    helper.del_txt_record("example.com", "_acme-challenge.example.com", "first")

    assert client.deleted == [2, 1]


def test_auto_discovery_keeps_separate_site_ids_for_multiple_domains(
    monkeypatch,
) -> None:
    helper, client = _helper(monkeypatch)

    helper.add_txt_record("one.example", "_acme-challenge.one.example", "first")
    helper.add_txt_record(
        "two.other.example", "_acme-challenge.two.other.example", "second"
    )

    assert [created[0] for created in client.created] == [42, 43]
    assert client.find_domains == ["one.example", "two.other.example"]


def test_cleanup_does_not_delete_a_preexisting_matching_record(monkeypatch) -> None:
    helper, client = _helper(monkeypatch, site_id=42)
    client.records = [{"record_id": 99, "data": SimpleNamespace(value="existing")}]

    helper.add_txt_record("example.com", "_acme-challenge.example.com", "existing")
    helper.del_txt_record("example.com", "_acme-challenge.example.com", "existing")

    assert client.created == []
    assert client.deleted == []


def test_cleanup_fallback_deletes_only_matching_value(monkeypatch) -> None:
    helper, client = _helper(monkeypatch, site_id=42)
    client.records = [
        {"record_id": 10, "data": SimpleNamespace(value="other")},
        {"record_id": 11, "data": SimpleNamespace(value="target")},
    ]

    helper.del_txt_record("example.com", "_acme-challenge.example.com", "target")

    assert client.deleted == [11]


def test_cleanup_without_a_matching_record_only_warns(monkeypatch, caplog) -> None:
    helper, _client = _helper(monkeypatch, site_id=42)

    helper.del_txt_record("example.com", "_acme-challenge.example.com", "target")

    assert "No ESA TXT record matched" in caplog.text


def test_add_failure_is_reported_as_plugin_error(monkeypatch) -> None:
    helper, client = _helper(monkeypatch, site_id=42)

    def fail_to_create(*_args, **_kwargs):
        raise RuntimeError("API unavailable")

    client.create_txt_record = fail_to_create

    with pytest.raises(errors.PluginError, match="API unavailable"):
        helper.add_txt_record("example.com", "_acme-challenge.example.com", "value")


def test_cleanup_failure_does_not_mask_certificate_issuance(
    monkeypatch, caplog
) -> None:
    helper, client = _helper(monkeypatch, site_id=42)
    helper.add_txt_record("example.com", "_acme-challenge.example.com", "value")

    def fail_to_delete(_record_id: int) -> None:
        raise RuntimeError("API unavailable")

    client.delete_record = fail_to_delete

    helper.del_txt_record("example.com", "_acme-challenge.example.com", "value")

    assert "Could not clean up ESA TXT record" in caplog.text


def test_cleanup_reuses_the_cached_record_id(monkeypatch) -> None:
    helper, client = _helper(monkeypatch, site_id=42)

    helper.add_txt_record("example.com", "_acme-challenge.example.com", "value")
    helper.del_txt_record("example.com", "_acme-challenge.example.com", "value")

    # One lookup while adding, none while deleting: cleanup reuses the known ID.
    assert client.list_calls == ["_acme-challenge.example.com"]
    assert client.deleted == [1]
