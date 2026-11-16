"""Regression tests for news_lambda_function's OurSteps scraping kill-switch.

OurSteps' fid=43 forum is login-gated for guests: the server replies HTTP 200 with
a Discuz "提示信息" permission page, so the scraper used to return navigation
boilerplate dressed up as article text. Scraping is therefore disabled by default
and must short-circuit before any network I/O.
"""
import importlib

import pytest

import news_lambda_function as nlf

DISABLED_NOTICE = "OurSteps 抓取已禁用"


@pytest.fixture
def no_network(monkeypatch):
    """Any HTTP attempt raises, proving a code path is fully offline."""

    def _boom(*args, **kwargs):
        raise AssertionError("network I/O attempted while OurSteps scraping is disabled")

    for name in ("get", "post", "Session", "head", "request"):
        monkeypatch.setattr(nlf.requests, name, _boom)


def test_oursteps_scraping_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ENABLE_OURSTEPS_SCRAPE", raising=False)
    module = importlib.reload(nlf)

    assert module.ENABLE_OURSTEPS_SCRAPE is False
    assert module.scrape_oursteps() == DISABLED_NOTICE


def test_disabled_scrape_performs_no_network_calls(no_network):
    # no_network would blow up on any request; returning the notice proves the
    # early return happens before headers/requests are touched.
    assert nlf.scrape_oursteps() == DISABLED_NOTICE


def test_scraping_can_be_re_enabled_by_env(monkeypatch):
    monkeypatch.setenv("ENABLE_OURSTEPS_SCRAPE", "true")
    try:
        assert importlib.reload(nlf).ENABLE_OURSTEPS_SCRAPE is True
    finally:
        monkeypatch.delenv("ENABLE_OURSTEPS_SCRAPE", raising=False)
        importlib.reload(nlf)
