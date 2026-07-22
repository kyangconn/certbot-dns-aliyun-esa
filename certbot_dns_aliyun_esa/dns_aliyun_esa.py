"""Certbot DNS-01 authenticator for Aliyun ESA."""

from __future__ import annotations

import logging
from typing import Any, Callable

import zope.interface
from certbot import errors, interfaces
from certbot.plugins import dns_common

from .esa_client import AliCloudESAClient

logger = logging.getLogger(__name__)

DEFAULT_TTL = 600


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
            "Aliyun ESA API for NS-access sites. It requires an AccessKey ID "
            "and AccessKey Secret."
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
    def _validate_credentials(
        cls, credentials: dns_common.CredentialsConfiguration
    ) -> None:
        access_key_id = cls._credential_value(
            credentials, "access_key_id", "access_id"
        )
        access_key_secret = cls._credential_value(
            credentials, "access_key_secret", "access_secret"
        )

        missing = []
        if not access_key_id:
            missing.append(
                f'"{credentials.mapper("access_key_id")}" '
                f'(legacy: "{credentials.mapper("access_id")}")'
            )
        if not access_key_secret:
            missing.append(
                f'"{credentials.mapper("access_key_secret")}" '
                f'(legacy: "{credentials.mapper("access_secret")}")'
            )
        if missing:
            raise errors.PluginError(
                "Missing credential properties: " + ", ".join(missing)
            )

        site_id = credentials.conf("site_id")
        if site_id:
            cls._parse_site_id(site_id)

    @staticmethod
    def _credential_value(
        credentials: dns_common.CredentialsConfiguration,
        canonical_name: str,
        legacy_name: str,
    ) -> str | None:
        return credentials.conf(canonical_name) or credentials.conf(legacy_name)

    @staticmethod
    def _parse_site_id(value: int | str) -> int:
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

    def _get_esa_helper(self) -> "_AliCloudESAHelper":
        """Create one helper per authenticator run so cleanup retains record IDs."""
        if self._helper is not None:
            return self._helper
        if self.credentials is None:
            raise errors.Error("Credentials have not been configured")

        access_key_id = self._credential_value(
            self.credentials, "access_key_id", "access_id"
        )
        access_key_secret = self._credential_value(
            self.credentials, "access_key_secret", "access_secret"
        )
        if not access_key_id or not access_key_secret:
            self._validate_credentials(self.credentials)
            raise AssertionError("credential validation returned unexpectedly")

        cli_site_id = self.conf("site-id")
        credentials_site_id = self.credentials.conf("site_id")
        site_id_value = (
            cli_site_id if cli_site_id is not None else credentials_site_id
        )
        site_id = (
            None
            if site_id_value is None
            or (isinstance(site_id_value, str) and not site_id_value.strip())
            else self._parse_site_id(site_id_value)
        )
        ttl = self._validate_ttl(self.conf("ttl"))

        logger.debug("Using ESA site ID: %s", site_id or "automatic discovery")
        self._helper = _AliCloudESAHelper(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            site_id=site_id,
            ttl=ttl,
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
        self.ttl = ttl
        self.site_id = site_id
        self._verified_site_id: int | None = None
        self._discovered_site_ids: dict[str, int] = {}
        self._record_ids: dict[tuple[int, str, str], int | None] = {}

    def _ensure_site_id(self, domain: str) -> int:
        """Resolve and, for an explicit ID, verify the ESA site once."""
        if self.site_id is not None:
            if self._verified_site_id is None:
                try:
                    site = self.client.get_site(self.site_id)
                except Exception as exc:
                    raise errors.PluginError(
                        f"ESA site ID {self.site_id} could not be verified: {exc}"
                    ) from exc
                self._validate_site_access(site)
                self._verified_site_id = int(site["site_id"])
            return self._verified_site_id

        domain_key = domain.strip().rstrip(".").lower()
        if domain_key.startswith("*."):
            domain_key = domain_key[2:]
        if domain_key in self._discovered_site_ids:
            return self._discovered_site_ids[domain_key]

        logger.info("Looking up the ESA site for %s", domain)
        site = self.client.find_site_by_domain(domain)
        if not site:
            raise errors.PluginError(
                f"No ESA site matched {domain}. Ensure the domain is configured in ESA, "
                "or pass --dns-aliyun-esa-site-id."
            )

        self._validate_site_access(site)
        discovered_site_id = int(site["site_id"])
        self._discovered_site_ids[domain_key] = discovered_site_id
        logger.info(
            "Using ESA site %s (ID: %s)", site["site_name"], discovered_site_id
        )
        return discovered_site_id

    @staticmethod
    def _validate_site_access(site: dict[str, Any]) -> None:
        """Reject ESA CNAME-access sites, which cannot create TXT records."""
        access_type = str(site.get("access_type") or "").strip().upper()
        if access_type and access_type != "NS":
            site_name = site.get("site_name") or site.get("site_id") or "unknown"
            raise errors.PluginError(
                f"ESA site {site_name!r} uses {access_type} access. DNS-01 TXT "
                "records require an NS-access ESA site."
            )

    def add_txt_record(
        self, domain: str, record_name: str, record_content: str
    ) -> None:
        """Create or reuse an exact TXT challenge record."""
        record_name = record_name.rstrip(".")
        logger.info("Adding ESA TXT record: %s", record_name)

        try:
            site_id = self._ensure_site_id(domain)
            record_key = (site_id, record_name, record_content)
            existing_records = self.client.get_site_records(
                site_id, record_name, "TXT"
            )
            for record in existing_records:
                if self._extract_txt_value(record) == record_content:
                    record_id = int(record["record_id"])
                    logger.info("Reusing existing TXT record ID %s", record_id)
                    # The record was not created by this run, so cleanup must leave it.
                    self._record_ids[record_key] = None
                    return

            record_id = self.client.add_txt_record(
                site_id=site_id,
                record_name=record_name,
                value=record_content,
                ttl=self.ttl,
                comment="Certbot DNS-01 challenge",
            )
            self._record_ids[record_key] = record_id
            logger.info("Created TXT record ID %s", record_id)
        except errors.PluginError:
            raise
        except Exception as exc:
            logger.error("Failed to add ESA TXT record: %s", exc)
            raise errors.PluginError(f"Failed to add ESA TXT record: {exc}") from exc

    def del_txt_record(
        self, domain: str, record_name: str, record_content: str
    ) -> None:
        """Delete only the TXT record matching this challenge value."""
        record_name = record_name.rstrip(".")
        logger.info("Deleting ESA TXT record: %s", record_name)

        try:
            site_id = self._ensure_site_id(domain)
            record_key = (site_id, record_name, record_content)
            if record_key in self._record_ids:
                record_id = self._record_ids.pop(record_key)
                if record_id is None:
                    logger.info(
                        "Leaving pre-existing TXT record unchanged: %s", record_name
                    )
                    return
                self.client.delete_record(record_id)
                logger.info("Deleted cached TXT record ID %s", record_id)
                return

            existing_records = self.client.get_site_records(
                site_id, record_name, "TXT"
            )
            for record in existing_records:
                if self._extract_txt_value(record) == record_content:
                    self.client.delete_record(int(record["record_id"]))
                    logger.info("Deleted discovered TXT record ID %s", record["record_id"])
                    return

            logger.warning("No matching ESA TXT record found for %s", record_name)
        except Exception as exc:  # Cleanup must not mask certificate issuance.
            logger.warning("Could not clean up ESA TXT record %s: %s", record_name, exc)

    @staticmethod
    def _extract_txt_value(record: dict[str, Any]) -> str:
        """Extract a TXT value from ESA SDK record representations."""
        value = record.get("value")
        if value:
            return str(value)

        data = record.get("data")
        if isinstance(data, str):
            return data
        if isinstance(data, dict):
            for key in ("value", "txt", "data", "content", "text"):
                value = data.get(key)
                if value:
                    return str(value)
        elif data is not None:
            for attribute in ("value", "txt", "data", "content", "text"):
                value = getattr(data, attribute, None)
                if value:
                    return str(value)

        for key in ("content", "txt", "text", "record_value"):
            value = record.get(key)
            if value:
                return str(value)

        logger.warning("Could not extract a TXT value from ESA record %r", record)
        return ""
