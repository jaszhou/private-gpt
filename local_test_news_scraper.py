#!/usr/bin/env python3
"""Local test harness for news_lambda_function.py.

Exercises the scraping stages only. No AWS credentials, no Polly, no Telegram.

Usage:
    ./.venv/bin/python local_test_news_scraper.py            # run everything
    ./.venv/bin/python local_test_news_scraper.py oursteps   # single source
    ./.venv/bin/python local_test_news_scraper.py wenxue     # wenxuecity (text)
    ./.venv/bin/python local_test_news_scraper.py detailed   # wenxuecity (structured)
    ./.venv/bin/python local_test_news_scraper.py unit       # offline unit checks only
"""
import sys
import time
import warnings

import news_lambda_function as nlf

warnings.filterwarnings("ignore")  # scrapers use verify=False on purpose
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PASS, FAIL = "\033[32mPASS\033[0m", "\033[31mFAIL\033[0m"
results = []


def record(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"[{PASS if ok else FAIL}] {name}" + (f" — {detail}" if detail else ""))


# ---------------------------------------------------------------- offline units
def test_units():
    print("\n=== Offline unit checks ===")

    bad = [None, "", "   ", "short", "词" * 50]
    for b in bad:
        record(f"_has_significant_words rejects {b!r:.30}", nlf._has_significant_words(b) is False)

    good_zh = "据新华社报道，" + "这是一个关于经济形势和民生问题的详细报道内容。" * 12
    record("_has_significant_words accepts long Chinese text", nlf._has_significant_words(good_zh) is True)

    good_en = "This is a substantial English news article with plenty of words. " * 8
    record("_has_significant_words accepts long English text", nlf._has_significant_words(good_en) is True)

    # SSML sanitising must not leak raw markup characters.
    dirty = '<b>A & B</b>\n\n第二段 & more'
    clean = nlf.sanitize_for_ssml(dirty)
    record(
        "sanitize_for_ssml escapes & strips newlines",
        "&amp;" in clean and "&lt;" in clean and "\n" not in clean and "<b>" not in clean,
        repr(clean),
    )

    record(
        "module config readable without AWS creds",
        isinstance(nlf.AWS_REGION, str) and isinstance(nlf.VOICE_ID, str),
        f"AWS_REGION={nlf.AWS_REGION} VOICE_ID={nlf.VOICE_ID} "
        f"TELEGRAM_TOKEN={'set' if nlf.TELEGRAM_TOKEN else 'unset'}",
    )

    # Rate limiter should allow the first call and block an immediate second one.
    ok1, _ = nlf.check_rate_limit()
    ok2, remaining = nlf.check_rate_limit()
    record(
        "rate limiter blocks second immediate call",
        ok1 is True and ok2 is False and remaining > 0,
        f"first={ok1} second={ok2} remaining={remaining:.0f}s",
    )


# ---------------------------------------------------------------- live sources
def test_oursteps():
    print("\n=== scrape_oursteps() ===")

    if not nlf.ENABLE_OURSTEPS_SCRAPE:
        # Disabled: must return immediately, perform no network I/O, and hand back
        # a clear notice rather than scraped text.
        started = time.time()
        out = nlf.scrape_oursteps()
        elapsed = time.time() - started
        record(
            "scrape_oursteps disabled -> no network, returns notice",
            out == "OurSteps 抓取已禁用" and elapsed < 1.0,
            f"returned {out!r} in {elapsed:.3f}s",
        )
        return True

    started = time.time()
    out = nlf.scrape_oursteps()
    elapsed = time.time() - started

    ok = isinstance(out, str) and "未能获取到足够内容的新闻" not in out and "网路" not in out
    ok = ok and "新闻 1:" in out
    record("scrape_oursteps returns article text", ok, f"{len(out)} chars in {elapsed:.1f}s")
    print("-" * 70)
    print(out[:1500])
    print("-" * 70)
    with open("local_test_oursteps.txt", "w", encoding="utf-8") as f:
        f.write(out)
    return ok


def test_wenxue():
    print("\n=== scrape_wenxuecity() ===")
    started = time.time()
    out = nlf.scrape_wenxuecity()
    elapsed = time.time() - started

    ok = isinstance(out, str) and "新闻 1:" in out
    record("scrape_wenxuecity returns article text", ok, f"{len(out)} chars in {elapsed:.1f}s")
    print("-" * 70)
    print(out[:1500])
    print("-" * 70)
    with open("local_test_wenxuecity.txt", "w", encoding="utf-8") as f:
        f.write(out)
    return ok


def test_detailed():
    print("\n=== scrape_wenxuecity_detailed() ===")
    started = time.time()
    out = nlf.scrape_wenxuecity_detailed()
    elapsed = time.time() - started

    ok = isinstance(out, list) and len(out) > 0
    record("scrape_wenxuecity_detailed returns list", ok, f"{len(out) if isinstance(out, list) else 'n/a'} items in {elapsed:.1f}s")

    if ok:
        keys_ok = all({"title", "content", "url"} <= set(a) for a in out)
        record("detailed articles have title/content/url keys", keys_ok)
        extracted = sum(1 for a in out if len(a.get("content", "")) > 100 and a["content"] != "内容获取失败")
        record(
            "detailed articles contain extracted content",
            extracted > 0,
            f"{extracted}/{len(out)} with >100 chars of real content",
        )
        for i, a in enumerate(out[:5], 1):
            print(f"\n  [{i}] {a['title'][:60]}")
            print(f"      url: {a['url']}")
            print(f"      content[{len(a['content'])}]: {a['content'][:220]}...")
        with open("local_test_detailed.txt", "w", encoding="utf-8") as f:
            for a in out:
                f.write(f"TITLE: {a['title']}\nURL: {a['url']}\nCONTENT: {a['content']}\n\n")
    return ok


# ---------------------------------------------------------------- quality gate
JUNK_MARKERS = [
    "无法进行此操作",
    "抱歉，您所在的用户组",
    "请 登录 后使用快捷导航",
    "切换为窄屏",
    "Powered by Discuz",
    "新足迹 - Powered",
]
NAV_PREFIXES = ["新闻汇总国际新闻", "设为首页", "快捷导航"]


def test_quality():
    """Assert the scraper returns real article text, not site boilerplate."""
    print("\n=== content quality gate ===")

    sources = [("wenxuecity", nlf.scrape_wenxuecity)]
    if nlf.ENABLE_OURSTEPS_SCRAPE:
        sources.insert(0, ("oursteps", nlf.scrape_oursteps))
    else:
        print("  SKIP: oursteps quality checks (OurSteps scraping is disabled)")

    for name, fn in sources:
        out = fn()
        if not isinstance(out, str):
            record(f"{name}: returned text", False, f"got {type(out).__name__}")
            continue

        hits = [m for m in JUNK_MARKERS if m in out]
        record(f"{name}: no permission/boilerplate page leaked", not hits, f"found {hits}")

        nav_hits = [p for p in NAV_PREFIXES if p in out]
        record(f"{name}: no navigation menu text leaked", not nav_hits, f"found {nav_hits}")

        bad_titles = [ln for ln in out.splitlines() if "新闻" in ln and "发表于" in ln]
        record(
            f"{name}: no author/timestamp pseudo-titles",
            not bad_titles,
            f"{len(bad_titles)} bad titles, e.g. {bad_titles[:2]}",
        )

        import re as _re

        real = 0
        total = 0
        for block in out.split("---"):
            m = _re.search(r"内容摘要:\s*(.*)", block, _re.S)
            if not m:
                continue
            total += 1
            body = m.group(1).strip()
            if body and not any(x in body for x in JUNK_MARKERS) and not any(body.startswith(p) for p in NAV_PREFIXES):
                real += 1
        record(
            f"{name}: most articles have real content",
            total > 0 and real >= max(1, total * 0.7),
            f"{real}/{total} articles usable",
        )


# ---------------------------------------------------------------- main
if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"

    if which in ("quality", "all"):
        test_quality()

    if which in ("unit", "all"):
        test_units()
    if which in ("oursteps", "all"):
        test_oursteps()
    if which in ("wenxue", "all"):
        test_wenxue()
    if which in ("detailed", "all"):
        test_detailed()

    print("\n" + "=" * 70)
    failed = [r for r in results if not r[1]]
    print(f"SUMMARY: {len(results) - len(failed)}/{len(results)} checks passed")
    for name, _, detail in failed:
        print(f"  FAILED: {name} {detail}")
    sys.exit(1 if failed else 0)
