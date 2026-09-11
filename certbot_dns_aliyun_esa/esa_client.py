"""Thin wrapper around the Aliyun ESA Python SDK."""

from __future__ import annotations

from typing import Any

from alibabacloud_esa20240910 import models as esa_models
from alibabacloud_esa20240910.client import Client as ESAClient
from alibabacloud_tea_openapi import models as open_api_models
from darabonba.runtime import RuntimeOptions

ESA_ENDPOINT = "esa.cn-hangzhou.aliyuncs.com"
PAGE_SIZE = 500


def normalize_domain(domain: str) -> str:
    """Return a domain in the lowercase, dot-free form the ESA API uses."""
    return domain.strip().rstrip(".").lower()


def _last_page(page: list[Any], fetched: int, total_count: int | None) -> bool:
    """Report whether an ESA list response was the final page."""
    if total_count is not None:
        return fetched >= total_count
    return len(page) < PAGE_SIZE


def _record_fields(record: Any) -> dict[str, Any]:
    return {
        "record_id": record.record_id,
        "record_name": record.record_name,
        "type": record.record_type,
        "data": record.data,
        "ttl": record.ttl,
        "comment": record.comment,
    }


def _site_fields(site: Any) -> dict[str, Any]:
    return {
        "site_id": site.site_id,
        "site_name": site.site_name,
        "status": site.status,
        "coverage": site.coverage,
        "access_type": site.access_type,
    }


def _domain_suffixes(domain: str) -> list[str]:
    """Return ``domain`` and each parent domain, longest first.

    A leading wildcard label is dropped, and the bare public suffix is not a
    candidate because an ESA site is never registered on ``com`` itself.
    """
    normalized = normalize_domain(domain).removeprefix("*.")
    labels = [label for label in normalized.split(".") if label]
    if not labels:
        return []
    return [".".join(labels[index:]) for index in range(max(len(labels) - 1, 1))]


class AliCloudESAClient:
    """Expose the ESA site and DNS record operations the plugin needs."""

    def __init__(self, access_key_id: str, access_key_secret: str) -> None:
        config = open_api_models.Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            endpoint=ESA_ENDPOINT,
        )
        self.client = ESAClient(config)

    def list_sites(self, name: str) -> list[dict[str, Any]]:
        """Return every ESA site whose name matches ``name`` exactly."""
        sites: list[dict[str, Any]] = []
        page_number = 1
        while True:
            request = esa_models.ListSitesRequest(
                site_name=normalize_domain(name),
                site_search_type="exact",
                page_number=page_number,
                page_size=PAGE_SIZE,
            )
            body = self.client.list_sites_with_options(request, RuntimeOptions()).body
            page = list(body.sites or [])
            sites.extend(_site_fields(site) for site in page)
            if _last_page(page, len(sites), getattr(body, "total_count", None)):
                return sites
            page_number += 1

    def get_site(self, site_id: int) -> dict[str, Any]:
        """Return one ESA site by ID."""
        request = esa_models.GetSiteRequest(site_id=site_id)
        body = self.client.get_site_with_options(request, RuntimeOptions()).body
        if body.site_model is None:
            raise RuntimeError(f"ESA returned no site for ID {site_id}")
        return _site_fields(body.site_model)

    def find_site_by_domain(self, domain: str) -> dict[str, Any] | None:
        """Return the ESA site matching the longest suffix of ``domain``."""
        for candidate in _domain_suffixes(domain):
            for site in self.list_sites(candidate):
                if normalize_domain(site["site_name"]) == candidate:
                    return site
        return None

    def list_records(self, site_id: int, record_name: str) -> list[dict[str, Any]]:
        """Return every TXT record stored under ``record_name``."""
        name = normalize_domain(record_name)
        records: list[dict[str, Any]] = []
        page_number = 1
        while True:
            request = esa_models.ListRecordsRequest(
                site_id=site_id,
                record_name=name,
                record_match_type="exact",
                type="TXT",
                page_number=page_number,
                page_size=PAGE_SIZE,
                proxied=False,
            )
            body = self.client.list_records_with_options(request, RuntimeOptions()).body
            page = list(body.records or [])
            records.extend(_record_fields(record) for record in page)
            if _last_page(page, len(records), getattr(body, "total_count", None)):
                return records
            page_number += 1

    def create_txt_record(
        self, site_id: int, record_name: str, value: str, ttl: int
    ) -> int:
        """Create one unproxied TXT record and return its record ID."""
        request = esa_models.CreateRecordRequest(
            site_id=site_id,
            record_name=normalize_domain(record_name),
            type="TXT",
            ttl=ttl,
            comment="Certbot DNS-01 challenge",
            proxied=False,
            data=esa_models.CreateRecordRequestData(value=value),
        )
        body = self.client.create_record_with_options(request, RuntimeOptions()).body
        if body.record_id is None:
            raise RuntimeError("ESA returned no record ID for the created TXT record")
        return int(body.record_id)

    def delete_record(self, record_id: int) -> None:
        """Delete a DNS record by ID."""
        request = esa_models.DeleteRecordRequest(record_id=record_id)
        self.client.delete_record_with_options(request, RuntimeOptions())
