from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import requests

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IpReputationResult:
    is_vpn: bool
    is_proxy: bool
    is_hosting: bool

    @property
    def is_blocked(self) -> bool:
        return self.is_vpn or self.is_proxy or self.is_hosting


def check_ip_reputation(
    ip_address: str, *, timeout_seconds: int = 2
) -> IpReputationResult | None:
    """
    Uses ip-api.com to detect VPN/proxy/hosting.

    Returns None if the check fails (we treat failures as non-blocking).
    """
    try:
        resp = requests.get(
            f"http://ip-api.com/json/{ip_address}?fields=proxy,hosting,vpn",
            timeout=timeout_seconds,
        )
        data: dict[str, Any] = resp.json()
    except Exception as exc:
        logger.info("IP reputation check failed for %s: %s", ip_address, exc)
        return None

    return IpReputationResult(
        is_vpn=bool(data.get("vpn")),
        is_proxy=bool(data.get("proxy")),
        is_hosting=bool(data.get("hosting")),
    )
