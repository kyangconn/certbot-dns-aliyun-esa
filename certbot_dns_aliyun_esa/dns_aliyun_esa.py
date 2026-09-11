"""Certbot DNS-01 authenticator for Aliyun ESA."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import zope.interface
from certbot import errors, interfaces
from certbot.plugins import dns_common

from .esa_client import AliCloudESAClient, normalize_domain

logger = logging.getLogger(__name__)

DEFAULT_TTL = 600

# Marks a challenge record that already existed, so cleanup must leave it alone.
_PREEXISTING = object()


def _txt_value(record: dict[str, Any]) -> str:
    """Return the string value of an ESA TXT record."""
    data = record.get("data")
    return str(getattr(data, "value", data) or "")


@zope.interface.implementer(interfaces.IAuthenticator)
@zope.interface.provider(interfaces.IPluginFactory)
class Authenticator(dns_common.DNSAuthenticator):
    """Use the Aliyun ESA DNS API to solve DNS-01 challenges."""

    description = "Configure DNS records with the Aliyun ESA API"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.credentials: dns_common.CredentialsConfiguration | None = None
        self._helper: _AliCloudESAHelper | None = None

    @classmethod
    def add_parser_arguments(
        cls, add: Callable[..., None], default_propagation_seconds: int = 30
    ) -> None:
        """Register Certbot command-line options."""
        super().add_parser_arguments(add, default_propagation_seconds)
        add("credentials", help="Path to the Aliyun ESA credentials INI file")
        add(
            "site-id",
            type=int,
            help="ESA site ID (optional; discovered from the certificate domain by default)",
        )
        add(
            "ttl",
            type=int,
            default=DEFAULT_TTL,
            help="TTL for temporary TXT records (1 or 30-86400; default: 600)",
        )

    def more_info(self) -> str:
        """Return additional plugin information for ``certbot plugins``."""
        return (
            "This plugin creates and removes DNS-01 TXT records through the "
            "Aliyun ESA API. It requires an AccessKey ID and AccessKey Secret."
        )

    def _setup_credentials(self) -> None:
        """Read and validate the API credentials file."""
        self.credentials = self._configure_credentials(
            "credentials",
            "Aliyun ESA API credentials file",
            validator=self._validate_credentials,
        )
        self._helper = None

    @classmethod
    def _credential(
        cls, credentials: dns_common.CredentialsConfiguration, name: str
    ) -> str | None:
        """Read a credential under its current or its pre-0.1 name."""
        return credentials.conf(name) or credentials.conf(name.replace("_key", ""))

    @classmethod
    def _validate_credentials(
        cls, credentials: dns_common.CredentialsConfiguration
    ) -> None:
        missing = [
            name
            for name in ("access_key_id", "access_key_secret")
            if not cls._credential(credentials, name)
        ]
        if missing:
            names = ", ".join(f'"{credentials.mapper(name)}"' for name in missing)
            raise errors.PluginError(f"Missing credential properties: {names}")
        if credentials.conf("site_id"):
            cls._parse_site_id(credentials.conf("site_id"))

    @staticmethod
    def _parse_site_id(value: Any) -> int:
        try:
            site_id = int(value)
        except (TypeError, ValueError) as exc:
            raise errors.PluginError(
                f"Invalid ESA site ID {value!r}; it must be a positive integer"
            ) from exc
        if site_id <= 0:
            raise errors.PluginError(
                f"Invalid ESA site ID {value!r}; it must be a positive integer"
            )
        return site_id

    @staticmethod
    def _validate_ttl(value: int) -> int:
        if value != 1 and not 30 <= value <= 86400:
            raise errors.PluginError(
                "Invalid ESA TTL; use 1 or an integer between 30 and 86400"
            )
        return value

    def _perform(self, domain: str, validation_name: str, validation: str) -> None:
        self._get_esa_helper().add_txt_record(domain, validation_name, validation)

    def _cleanup(self, domain: str, validation_name: str, validation: str) -> None:
        self._get_esa_helper().del_txt_record(domain, validation_name, validation)

    def _get_esa_helper(self) -> _AliCloudESAHelper:
        """Create one helper per run so cleanup can reuse known record IDs."""
        if self._helper is not None:
            return self._helper
        if self.credentials is None:
            raise errors.PluginError("Credentials have not been configured")

        access_key_id = self._credential(self.credentials, "access_key_id")
        access_key_secret = self._credential(self.credentials, "access_key_secret")
        # An explicit ID wins over the credentials file, but a configured but
        # unusable value must fail loudly instead of silently discovering a site.
        configured_site_id = self.conf("site-id")
        if configured_site_id is None:
            configured_site_id = self.credentials.conf("site_id")
        self._helper = _AliCloudESAHelper(
            access_key_id or "",
            access_key_secret or "",
            site_id=(
                self._parse_site_id(configured_site_id)
                if configured_site_id is not None
                else None
            ),
            ttl=self._validate_ttl(self.conf("ttl")),
        )
        return self._helper


class _AliCloudESAHelper:
    """Translate Certbot challenge operations into ESA API calls."""

    def __init__(
        self,
        access_key_id: str,
        access_key_secret: str,
        site_id: int | None = None,
        ttl: int = DEFAULT_TTL,
    ) -> None:
        self.client = AliCloudESAClient(access_key_id, access_key_secret)
        self.site_id = site_id
        self.ttl = ttl
        self._site_ids: dict[str, int] = {}
        self._record_ids: dict[tuple[int, str, str], Any] = {}

    def add_txt_record(
        self, domain: str, record_name: str, record_content: str
    ) -> None:
        """Create the challenge TXT record, reusing an identical existing one."""
        record_name = normalize_domain(record_name)
        logger.info("Adding ESA TXT record: %s", record_name)
        try:
            site_id = self._site_id_for(domain)
            record_id = self._find_record(site_id, record_name, record_content)
            if record_id is None:
                record_id = self.client.create_txt_record(
                    site_id, record_name, record_content, self.ttl
                )
                logger.info("Created ESA TXT record ID %s", record_id)
            else:
                logger.info("Reusing the existing ESA TXT record ID %s", record_id)
                record_id = _PREEXISTING
            self._record_ids[(site_id, record_name, record_content)] = record_id
        except Exception as exc:
            raise errors.PluginError(f"Failed to add ESA TXT record: {exc}") from exc

    def del_txt_record(
        self, domain: str, record_name: str, record_content: str
    ) -> None:
        """Delete the challenge TXT record unless it predates this run."""
        record_name = normalize_domain(record_name)
        logger.info("Deleting ESA TXT record: %s", record_name)
        try:
            site_id = self._site_id_for(domain)
            key = (site_id, record_name, record_content)
            if key not in self._record_ids:
                # Cleanup without a preceding add, so find the record ourselves.
                self._record_ids[key] = self._find_record(
                    site_id, record_name, record_content
                )
            record_id = self._record_ids.pop(key)
            if record_id is _PREEXISTING:
                logger.info("Leaving pre-existing ESA TXT record in place")
            elif record_id is None:
                logger.warning("No ESA TXT record matched %s", record_name)
            else:
                self.client.delete_record(record_id)
                logger.info("Deleted ESA TXT record ID %s", record_id)
        except Exception as exc:  # noqa: BLE001 - cleanup must never fail issuance
            logger.warning("Could not clean up ESA TXT record %s: %s", record_name, exc)

    def _find_record(
        self, site_id: int, record_name: str, record_content: str
    ) -> int | None:
        """Return the ID of the TXT record holding ``record_content``."""
        for record in self.client.list_records(site_id, record_name):
            if _txt_value(record) == record_content:
                return int(record["record_id"])
        return None

    def _site_id_for(self, domain: str) -> int:
        """Return the ESA site ID for ``domain``, verified as NS access."""
        if self.site_id is not None:
            key = f"id:{self.site_id}"
        else:
            key = normalize_domain(domain).removeprefix("*.")
        if key not in self._site_ids:
            if self.site_id is None:
                site = self.client.find_site_by_domain(domain)
                if not site:
                    raise errors.PluginError(
                        f"No ESA site matched {domain}. Ensure the domain is "
                        "configured in ESA, or pass --dns-aliyun-esa-site-id."
                    )
            else:
                # An explicit ID is only trusted once we have seen the site.
                site = self.client.get_site(self.site_id)
                logger.info("Using ESA site %s", site["site_name"])
            self._validate_site_access(site)
            self._site_ids[key] = int(site["site_id"])
        return self._site_ids[key]

    @staticmethod
    def _validate_site_access(site: dict[str, Any]) -> None:
        """Reject ESA CNAME-access sites, which cannot create TXT records."""
        access_type = str(site.get("access_type") or "").strip().upper()
        if access_type and access_type != "NS":
            raise errors.PluginError(
                f"ESA site {site.get('site_name')!r} uses {access_type} access. "
                "DNS-01 TXT records require an NS-access ESA site."
            )
