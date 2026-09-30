"""Cliente HTTP saliente con allowlist anti-SSRF (security-boundaries B9). Sin red."""

import re
import socket
from pathlib import Path
from typing import Any

import pytest
from django.test import override_settings

from core import http

ALLOWED = override_settings(HTTP_ALLOWED_HOSTS=["api.example.com"])


def resolving_to(*ips: str) -> Any:
    def fake(host: str, port: int, *args: Any, **kwargs: Any) -> list[Any]:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port)) for ip in ips]

    return fake


@ALLOWED
@pytest.mark.parametrize(
    "url",
    [
        "http://api.example.com/x",  # sin TLS
        "https://user:pw@api.example.com/x",  # credenciales en la URL
        "https://evil.example.com/x",  # fuera de la allowlist
        "https://api.example.com.evil.test/x",  # sufijo engañoso
        "https://169.254.169.254/latest/meta-data",  # IP literal no permitida
        "file:///etc/passwd",
        "https://api.example.com:22/x",  # otro puerto en un host permitido
    ],
)
def test_urls_outside_the_policy_are_rejected(url: str) -> None:
    with pytest.raises(http.BlockedDestination):
        http.request("GET", url)


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",
        "10.0.0.8",
        "172.16.0.1",
        "192.168.1.1",
        "169.254.169.254",
        "100.64.0.1",
        "0.0.0.0",  # noqa: S104
        "::1",
        "fc00::1",
        "fe80::1",
        "::ffff:127.0.0.1",
        "224.0.0.1",
        "64:ff9b::a9fe:a9fe",  # NAT64 → 169.254.169.254
        "::7f00:1",  # IPv4 compatible
        "::ffff:0:7f00:1",  # SIIT
        "fec0::1",  # site-local
        "192.88.99.1",
        "2002:a9fe:a9fe::1",  # 6to4 → metadata
        "2001:0:4136:e378:8000:63bf:3fff:fdd2",  # Teredo
    ],  # fmt: skip
)
def test_private_and_special_addresses_are_blocked(
    ip: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert not http.is_public(ip)
    monkeypatch.setattr(socket, "getaddrinfo", resolving_to("93.184.216.34", ip))  # mezcla
    with pytest.raises(http.BlockedDestination):
        http.resolve_public("api.example.com", 443)


@ALLOWED
def test_allowlisted_host_resolving_to_metadata_ip_is_blocked_at_connect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", resolving_to("169.254.169.254"))  # rebinding
    with pytest.raises(http.BlockedDestination):
        http.request("GET", "https://api.example.com/v1/x")


def test_public_resolution_pins_the_ip_and_no_redirects_are_followed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", resolving_to("93.184.216.34"))
    assert http.resolve_public("api.example.com", 443) == "93.184.216.34"
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(http._manager, "request", lambda *a, **kw: calls.append(kw))
    with ALLOWED:
        http.request("GET", "https://API.example.com/x")  # el host se compara sin mayúsculas
    assert calls[0]["redirect"] is False and not {"timeout", "retries"} & set(calls[0])
    assert http._manager.pool_classes_by_scheme == {"https": http._GuardedPool}  # sin http


def test_connection_goes_to_the_pinned_ip_but_tls_keeps_the_hostname(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", resolving_to("93.184.216.34"))
    targets: list[Any] = []

    def connect(address: Any, *args: Any, **kwargs: Any) -> socket.socket:
        targets.append(address)
        return socket.socket()

    monkeypatch.setattr("urllib3.connection.connection.create_connection", connect)
    conn = http._GuardedHTTPSConnection("api.example.com", 443)
    conn._new_conn().close()
    assert targets == [("93.184.216.34", 443)]
    assert conn.host == "api.example.com"  # SNI, certificado y cabecera Host


def test_outbound_http_only_through_core_http() -> None:
    """Complementa a import-linter (solo ve lo importado): ningún otro cliente HTTP en el código."""
    pattern = re.compile(
        r"^\s*(import|from)\s+(requests|httpx|urllib3|urllib\.request|http\.client)\b", re.M
    )
    root = Path(__file__).resolve().parents[1]
    offenders = [
        str(path.relative_to(root)) for folder in ("core", "apps", "config")
        for path in (root / folder).rglob("*.py")
        if path != root / "core" / "http.py" and pattern.search(path.read_text())
    ]  # fmt: skip
    assert offenders == []
