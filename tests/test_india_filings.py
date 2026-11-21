import pytest

from equitymind.india_filings import _is_exchange_host


@pytest.mark.parametrize(
    "host",
    ["nseindia.com", "www.nseindia.com", "nsearchives.nseindia.com",
     "bseindia.com", "www.bseindia.com"],
)
def test_exchange_host_allowlist_accepts_exchange_domains(host):
    assert _is_exchange_host(host)


@pytest.mark.parametrize(
    "host",
    ["sec.gov", "google.com", "nseindia.com.evil.test", "evilnseindia.com", "localhost"],
)
def test_exchange_host_allowlist_rejects_other_domains(host):
    assert not _is_exchange_host(host)
