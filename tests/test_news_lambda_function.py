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


# --------------------------------------------------------------------------
# Article extraction: navigation chrome must never leak into article bodies.
# --------------------------------------------------------------------------
# Reproduces the wenxuecity shape: the <article> ships empty <p> placeholders and
# keeps its body in bare text nodes, while nav/breadcrumb/byline chrome sits in
# earlier siblings. The old code joined the empty <p> tags, came up short, and
# fell back to scanning the whole page -- returning the navigation menu.
CHROME_PAGE = """<html><body>
<div class="nav">新闻频道首页新闻读图财经教育家居健康美食时尚旅游影视博客群吧论坛电台焦点新闻</div>
<div class="ad">advertisement</div>
<div class="crumb">您的位置：文学城 » 新闻 » 焦点新闻 » 某标题</div>
<main class="mwrapper new">
  <h1>某标题</h1>
  <div class="byline">文章来源:CDT于2026-11-16 13:54:43 - 新闻取自各大新闻媒体，新闻内容并不代表本网立场！被阅读次数A-AA+</div>
  <article id="articleContent"><p></p><p></p>1948年冬天，蒋介石派飞机接北大校长胡适南下，毛泽东希望他留下。胡适走了，小儿子胡思杜留在北平。</article>
</main>
</body></html>"""

CHROME_MARKERS = ("advertisement", "您的位置", "文章来源", "被阅读次数", "新闻频道首页")


class FakeResponse:
    def __init__(self, html, status_code=200):
        self.content = html.encode("utf-8")
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise nlf.requests.exceptions.HTTPError(f"{self.status_code}", response=self)


def test_article_extraction_drops_page_chrome(monkeypatch):
    monkeypatch.setattr(nlf.requests, "get", lambda *a, **k: FakeResponse(CHROME_PAGE))

    content = nlf.scrape_article_content("/news/2026/11/16/000000001.html", {})

    assert content.startswith("1948年冬天"), content[:120]
    for marker in CHROME_MARKERS:
        assert marker not in content, f"chrome {marker!r} leaked: {content[:120]}"


def test_extract_article_text_ignores_empty_paragraph_placeholders():
    from bs4 import BeautifulSoup

    container = BeautifulSoup(
        '<article id="articleContent"><p></p><p></p>正文内容在裸文本节点里，足够长的一段真实新闻正文。</article>',
        "html.parser",
    ).select_one("article")

    assert nlf._extract_article_text(container).startswith("正文内容")


def test_strip_page_chrome_leaves_body_intact():
    body = "1948年冬天，蒋介石派飞机接北大校长胡适南下，毛泽东希望他留下。"
    chrome = "新闻频道首页新闻advertisement您的位置：文学城 » 新闻 » 焦点新闻 » 文章来源:CDT于2026-11-16被阅读次数A-AA+"

    assert nlf._strip_page_chrome(chrome + body) == body
    # An article that merely mentions a marker far from the start is untouched.
    deep = body * 20 + "本文提到文章来源:这一说法并作出澄清。"
    assert nlf._strip_page_chrome(deep) == deep


def test_fetch_retries_through_a_transient_403(monkeypatch):
    """The site blocks bursts; one retry must recover a transient 403."""
    calls = []

    def flaky(url, **kwargs):
        calls.append(url)
        return FakeResponse("ok", status_code=403 if len(calls) == 1 else 200)

    monkeypatch.setattr(nlf.requests, "get", flaky)
    monkeypatch.setattr(nlf.time, "sleep", lambda _s: None)

    response = nlf._fetch("https://example.test/a", {})

    assert response.status_code == 200
    assert len(calls) == 2


def test_fetch_gives_up_after_retries(monkeypatch):
    calls = []

    def always_403(url, **kwargs):
        calls.append(url)
        return FakeResponse("blocked", status_code=403)

    monkeypatch.setattr(nlf.requests, "get", always_403)
    monkeypatch.setattr(nlf.time, "sleep", lambda _s: None)

    with pytest.raises(nlf.requests.exceptions.HTTPError):
        nlf._fetch("https://example.test/b", {})

    assert len(calls) == 2
