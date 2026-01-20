import json
import re
import html
import requests
import boto3

# ---------- AWS CLIENTS ----------
polly = boto3.client("polly")
bedrock = boto3.client("bedrock-runtime")

# ---------- CONFIG ----------
MAX_SSML_LEN = 2800
VOICE_ID = "Zhiyu"
POLLY_ENGINE = "neural"

BEDROCK_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"

# ---------- HELPERS ----------

def fetch_html(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)"
    }
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    return r.text


def extract_article_with_bedrock(html_text):
    """
    Use Bedrock (Claude) to extract clean article text
    """
    prompt = f"""
Extract the main news article from the HTML below.

Rules:
- Ignore ads, navigation, comments, footers
- Keep original language
- Output plain text only
- No HTML tags
- No markdown
- No explanations

HTML:
{html_text[:15000]}
"""

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2048,
        "temperature": 0,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    response = bedrock.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        body=json.dumps(body)
    )

    result = json.loads(response["body"].read())
    return result["content"][0]["text"].strip()


def sanitize_for_ssml(text):
    """
    Make text 100% safe for Amazon Polly SSML
    """
    text = re.sub(r'[\r\n]+', ' ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    text = html.escape(text)
    return text.strip()


def build_ssml_chunks(text):
    """
    Split into Polly-safe SSML chunks
    """
    chunks = [
        text[i:i + MAX_SSML_LEN]
        for i in range(0, len(text), MAX_SSML_LEN)
    ]
    return [f"<speak>{chunk}</speak>" for chunk in chunks]


def synthesize_with_polly(ssml_chunks):
    """
    Convert SSML chunks to MP3 files
    """
    audio_files = []

    for i, ssml in enumerate(ssml_chunks):
        response = polly.synthesize_speech(
            Engine=POLLY_ENGINE,
            VoiceId=VOICE_ID,
            OutputFormat="mp3",
            TextType="ssml",
            Text=ssml
        )

        path = f"/tmp/news_{i}.mp3"
        with open(path, "wb") as f:
            f.write(response["AudioStream"].read())

        audio_files.append(path)

    return audio_files


# ---------- LAMBDA HANDLER ----------

def lambda_handler(event, context):
    """
    Expected event:
    {
        "url": "https://www.wenxuecity.com/news/..."
    }
    """

    try:
        url = event["url"]

        # 1. Fetch HTML
        html_text = fetch_html(url)

        # 2. AI extraction via Bedrock
        article_text = extract_article_with_bedrock(html_text)

        if not article_text:
            raise Exception("Bedrock returned empty article text")

        # 3. Sanitize for SSML
        safe_text = sanitize_for_ssml(article_text)

        # 4. Build SSML chunks
        ssml_chunks = build_ssml_chunks(safe_text)

        # 5. Polly synthesis
        audio_files = synthesize_with_polly(ssml_chunks)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "ok",
                "parts": len(audio_files),
                "files": audio_files
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e)
            })
        }
