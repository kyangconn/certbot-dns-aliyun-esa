"""Small, synchronous wrapper around the Aliyun ESA Python SDK."""

from __future__ import annotations

import logging
from typing import Any

from alibabacloud_esa20240910 import models as esa_models
from alibabacloud_esa20240910.client import Client as ESAClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models

logger = logging.getLogger(__name__)

ESA_ENDPOINT = "esa.cn-hangzhou.aliyuncs.com"
MAX_PAGE_SIZE = 500


class AliCloudESAClient:
    """Expose only the ESA site and DNS record operations the plugin needs."""

    def __init__(self, access_key_id: str, access_key_secret: str) -> None:
        config = open_api_models.Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            endpoint=ESA_ENDPOINT,
        )
        self.client = ESAClient(config)
        self.runtime = util_models.RuntimeOptions()

    def get_site_records(
        self,
        site_id: int,
        record_name: str | None = None,
        record_type: str = "TXT",
        page_number: int = 1,
        page_size: int = MAX_PAGE_SIZE,
        proxied: bool = False,
    ) -> list[dict[str, Any]]:
        """Return all matching records, following ESA pagination."""
        records: list[dict[str, Any]] = []
        current_page = page_number
        normalized_name = self._normalize_domain(record_name) if record_name else None

        try:
            while True:
                request = esa_models.ListRecordsRequest(
                    site_id=site_id,
                    record_name=normalized_name,
                    record_match_type="exact" if normalized_name else None,
                    type=record_type,
                    page_number=current_page,
                    page_size=page_size,
                    proxied=proxied,
                )
                response = self.client.list_records_with_options(request, self.runtime)
                body = response.body
                page = list(body.records or [])

                for record in page:
                    records.append(
                        {
                            "record_id": record.record_id,
                            "record_name": record.record_name,
                            "type": record.record_type,
                            "data": record.data,
                            "ttl": record.ttl,
                            "comment": record.comment,
                        }
                    )

                total_count = getattr(body, "total_count", None)
                if (
                    not page
                    or len(page) < page_size
                    or (total_count is not None and len(records) >= total_count)
                ):
                    break
                current_page += 1
        except Exception as exc:
            logger.error("Failed to list ESA DNS records: %s", exc)
            raise

        if normalized_name:
            records = [
                record
                for record in records
                if self._normalize_domain(record["record_name"]) == normalized_name
            ]
        return records

    def add_txt_record(
        self,
        site_id: int,
        record_name: str,
        value: str,
        ttl: int = 600,
        comment: str = "Certbot DNS-01 challenge",
    ) -> int:
        """Create one unproxied TXT record and return its numeric record ID."""
        record_name = self._normalize_domain(record_name)
        try:
            request = esa_models.CreateRecordRequest(
                site_id=site_id,
                record_name=record_name,
                type="TXT",
                ttl=ttl,
                comment=comment,
                proxied=False,
                data=esa_models.CreateRecordRequestData(value=value),
            )
            response = self.client.create_record_with_options(request, self.runtime)
            record_id = response.body.record_id
            if record_id is None:
                raise RuntimeError("ESA did not return a record ID")
            logger.info("Created ESA TXT record %s", record_name)
            return int(record_id)
        except Exception as exc:
            logger.error("Failed to create ESA TXT record: %s", exc)
            raise

    def delete_record(self, record_id: int) -> None:
        """Delete a DNS record by ID."""
        try:
            request = esa_models.DeleteRecordRequest(record_id=record_id)
            self.client.delete_record_with_options(request, self.runtime)
            logger.info("Deleted ESA DNS record %s", record_id)
        except Exception as exc:
            logger.error("Failed to delete ESA DNS record: %s", exc)
            raise

    def get_sites(
        self,
        name: str | None = None,
        search_mode: str = "exact",
        page_number: int = 1,
        page_size: int = MAX_PAGE_SIZE,
        sort_by: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return all matching ESA sites, following ESA pagination."""
        sites: list[dict[str, Any]] = []
        current_page = page_number

        try:
            while True:
                request = esa_models.ListSitesRequest(
                    site_name=name,
                    site_search_type=search_mode,
                    page_number=current_page,
                    page_size=page_size,
                    order_by=sort_by,
                )
                response = self.client.list_sites_with_options(request, self.runtime)
                body = response.body
                page = list(body.sites or [])

                for site in page:
                    sites.append(
                        {
                            "site_id": site.site_id,
                            "site_name": site.site_name,
                            "status": site.status,
                            "coverage": site.coverage,
                            "access_type": site.access_type,
                        }
                    )

                total_count = getattr(body, "total_count", None)
                if (
                    not page
                    or len(page) < page_size
                    or (total_count is not None and len(sites) >= total_count)
                ):
                    break
                current_page += 1
        except Exception as exc:
            logger.error("Failed to list ESA sites: %s", exc)
            raise

        return sites

    def get_site(self, site_id: int) -> dict[str, Any]:
        """Return one ESA site by ID."""
        try:
            request = esa_models.GetSiteRequest(site_id=site_id)
            response = self.client.get_site_with_options(request, self.runtime)
            site = response.body.site_model
            if not site:
                raise RuntimeError(f"No ESA site found for ID {site_id}")
            return {
                "site_id": site.site_id,
                "site_name": site.site_name,
                "status": site.status,
                "coverage": site.coverage,
                "access_type": site.access_type,
            }
        except Exception as exc:
            logger.error("Failed to get ESA site: %s", exc)
            raise

    def find_site_by_domain(self, domain: str) -> dict[str, Any] | None:
        """Find the longest exact ESA site suffix for a certificate domain."""
        for candidate in self._domain_candidates(domain):
            sites = self.get_sites(
                name=candidate,
                search_mode="exact",
                page_size=MAX_PAGE_SIZE,
            )
            for site in sites:
                if self._normalize_domain(site["site_name"]) == candidate:
                    return site
        return None

    @classmethod
    def _domain_candidates(cls, domain: str) -> list[str]:
        normalized = cls._normalize_domain(domain)
        if normalized.startswith("*."):
            normalized = normalized[2:]
        labels = [label for label in normalized.split(".") if label]
        if len(labels) < 2:
            return [normalized] if normalized else []
        return [".".join(labels[index:]) for index in range(len(labels) - 1)]

    @staticmethod
    def _normalize_domain(domain: str) -> str:
        return domain.strip().rstrip(".").lower()
