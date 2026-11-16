#!/usr/bin/env python3
"""Local test of news_lambda_function.lambda_handler wiring.

Everything external is stubbed: Polly (boto3) and Telegram (requests.post).
No AWS credentials, no network.

Run: ./.venv/bin/python local_test_lambda_handler.py
"""
import io
import json
import os
import sys
import warnings

import news_lambda_function as nlf

warnings.filterwarnings("ignore")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PASS, FAIL = "\033[32mPASS\033[0m", "\033[31mFAIL\033[0m"
results = []


def record(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"[{PASS if ok else FAIL}] {name}" + (f" — {detail}" if detail else ""))


def reset_rate_limit():
    try:
        os.remove(nlf.RATE_LIMIT_FILE)
    except FileNotFoundError:
        pass


# ---------------------------------------------------------------- stubs
class FakePolly:
    def __init__(self):
        self.calls = []

    def synthesize_speech(self, **kwargs):
        self.calls.append(kwargs)
        return {"AudioStream": io.BytesIO(b"ID3fake-mp3-bytes")}


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


polly = FakePolly()
telegram_calls = []


def fake_boto3_client(service, **kwargs):
    assert service == "polly", f"unexpected service {service}"
    return polly


def fake_post(url, **kwargs):
    telegram_calls.append(url)
    return FakeResponse({"ok": True, "result": {"message_id": 1}})


FIXTURE = [
    {"title": "测试文章一", "content": "这是第一篇测试文章的内容。" * 20, "url": "/news/1.html"},
    {"title": "测试文章二", "content": "第二篇文章，& 带特殊 <字符> 需要转义。" * 20, "url": "/news/2.html"},
]


def main():
    nlf.boto3.client = fake_boto3_client
    nlf.requests.post = fake_post
    nlf.TELEGRAM_TOKEN = "TEST_TOKEN"
    nlf.CHAT_ID = "TEST_CHAT"

    # --- 1. text_to_speech chunking -------------------------------------
    print("\n=== text_to_speech ===")
    polly.calls.clear()
    short = nlf.text_to_speech("短文本。")
    record("text_to_speech single chunk", short == b"ID3fake-mp3-bytes" and len(polly.calls) == 1)

    polly.calls.clear()
    long_text = "这是一个很长的句子用于测试分块逻辑。" * 300  # > 2800 chars
    nlf.text_to_speech(long_text)
    record(
        "text_to_speech splits long text into chunks",
        len(polly.calls) > 1,
        f"{len(long_text)} chars -> {len(polly.calls)} Polly calls",
    )
    record(
        "text_to_speech respects Polly 3000-char limit",
        all(len(c["Text"]) <= 3000 for c in polly.calls),
        f"max chunk={max(len(c['Text']) for c in polly.calls)} chars",
    )
    record("text_to_speech sends SSML", all(c["TextType"] == "ssml" for c in polly.calls))

    # --- 2. happy path ---------------------------------------------------
    print("\n=== lambda_handler happy path ===")
    reset_rate_limit()
    polly.calls.clear()
    telegram_calls.clear()
    nlf.scrape_wenxuecity_detailed = lambda: FIXTURE

    resp = nlf.lambda_handler({}, None)
    body = json.loads(resp["body"])
    record("status 200", resp["statusCode"] == 200, str(body))
    record("both articles sent to Telegram", body.get("successful_articles") == 2, str(body))
    record("one voice upload per article", len(telegram_calls) == 2, f"{len(telegram_calls)} calls")
    record("Polly called per article", len(polly.calls) == 2)

    # --- 3. rate limiting -------------------------------------------------
    print("\n=== rate limiting ===")
    resp2 = nlf.lambda_handler({}, None)
    body2 = json.loads(resp2["body"])
    record(
        "second immediate invoke returns 429",
        resp2["statusCode"] == 429 and body2.get("error") == "TOO_MANY_REQUESTS",
        f"retry_after={body2.get('retry_after_seconds')}s",
    )

    # --- 4. scrape failure path ------------------------------------------
    print("\n=== scrape failure path ===")
    reset_rate_limit()
    nlf.scrape_wenxuecity_detailed = lambda: "网络连接错误，无法获取新闻"
    resp3 = nlf.lambda_handler({}, None)
    record("scrape error returns 500", resp3["statusCode"] == 500, str(json.loads(resp3["body"])))

    # --- 5. Polly failure is per-article, not fatal ----------------------
    print("\n=== per-article error isolation ===")
    reset_rate_limit()
    nlf.scrape_wenxuecity_detailed = lambda: FIXTURE

    calls = {"n": 0}

    def flaky_tts(text):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("simulated Polly throttling")
        return b"ID3ok"

    nlf.text_to_speech = flaky_tts
    telegram_calls.clear()
    resp4 = nlf.lambda_handler({}, None)
    body4 = json.loads(resp4["body"])
    record(
        "one Polly failure does not abort the run",
        resp4["statusCode"] == 200 and body4.get("successful_articles") == 1,
        str(body4),
    )

    # --- 6. Telegram unconfigured ----------------------------------------
    print("\n=== Telegram not configured ===")
    reset_rate_limit()
    nlf.text_to_speech = lambda text: b"ID3ok"
    nlf.TELEGRAM_TOKEN = None
    nlf.CHAT_ID = None
    telegram_calls.clear()
    resp5 = nlf.lambda_handler({}, None)
    body5 = json.loads(resp5["body"])
    record(
        "no Telegram creds -> no upload, 0 successful",
        resp5["statusCode"] == 200 and body5.get("successful_articles") == 0 and not telegram_calls,
        str(body5),
    )

    print("\n" + "=" * 70)
    failed = [r for r in results if not r[1]]
    print(f"SUMMARY: {len(results) - len(failed)}/{len(results)} checks passed")
    for name, _, detail in failed:
        print(f"  FAILED: {name} {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
