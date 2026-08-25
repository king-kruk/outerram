from outerram.upstream_contracts import contracts, verify_upstream_contracts


def test_upstream_contract_check_passes_when_all_markers_exist():
    by_url = {contract.url: "\n".join(contract.required_markers) for contract in contracts()}
    result = verify_upstream_contracts(fetcher=lambda url: by_url[url])
    assert result["ok"] is True
    assert all(item["ok"] for item in result["contracts"])


def test_upstream_contract_check_fails_closed_on_missing_marker():
    first = contracts()[0]
    by_url = {contract.url: "\n".join(contract.required_markers) for contract in contracts()}
    by_url[first.url] = "intentionally incomplete"
    result = verify_upstream_contracts(fetcher=lambda url: by_url[url])
    assert result["ok"] is False
    failed = next(item for item in result["contracts"] if item["name"] == first.name)
    assert failed["missing_markers"]


def test_upstream_contract_check_reports_fetch_failure_without_crashing():
    def fetcher(url):
        if "streamlx" in url:
            raise RuntimeError("offline")
        contract = next(c for c in contracts() if c.url == url)
        return "\n".join(contract.required_markers)
    result = verify_upstream_contracts(fetcher=fetcher)
    assert result["ok"] is False
    assert any(item["error"] == "offline" for item in result["contracts"])
