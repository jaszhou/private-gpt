import json
import re
import html
import requests
from bs4 import BeautifulSoup
import boto3
import botocore
import os
from io import BytesIO
import time
from readability import Document

# -------------------------
# 1. Configuration
# -------------------------
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
VOICE_ID = os.environ.get('VOICE_ID', 'Zhiyu')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

# Bedrock configuration
# BEDROCK_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
BEDROCK_MODEL_ID = "amazon.titan-embed-text-v2:0"

MAX_SSML_LEN = 2800
POLLY_ENGINE = "neural"

# Rate limiting configuration
RATE_LIMIT_FILE = '/tmp/last_invoke_time.txt' if os.name != 'nt' else 'last_invoke_time.txt'
RATE_LIMIT_SECONDS = 60  # 1 minute

# -------------------------
# 2. Helper Functions
# -------------------------

def fetch_html(url):
    """Fetch HTML content from a URL"""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)"
    }
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    return r.text


def extract_article_with_readability(html_text):
    """
    Use Readability to extract clean article text
    """
    doc = Document(html_text)
    
    # Get the main content
    content = doc.summary()
    
    # Parse with BeautifulSoup to extract text
    soup = BeautifulSoup(content, 'html.parser')
    
    # Remove any remaining unwanted elements
    for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
        element.decompose()
    
    # Get clean text
    text = soup.get_text(separator=' ', strip=True)
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


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


# -------------------------
# 3. Rate Limiting Functions
# -------------------------
def check_rate_limit():
    """Check if function can be invoked based on rate limiting"""
    try:
        current_time = time.time()

        # Check if rate limit file exists
        if os.path.exists(RATE_LIMIT_FILE):
            with open(RATE_LIMIT_FILE, 'r') as f:
                last_invoke_time = float(f.read().strip())

            # Check if enough time has passed
            time_since_last = current_time - last_invoke_time
            if time_since_last < RATE_LIMIT_SECONDS:
                remaining_time = RATE_LIMIT_SECONDS - time_since_last
                return False, remaining_time

        # Update last invoke time
        with open(RATE_LIMIT_FILE, 'w') as f:
            f.write(str(current_time))

        return True, 0

    except Exception as e:
        print(f"Error checking rate limit: {e}")
        # If there's an error, allow the invoke to proceed
        return True, 0

def get_last_invoke_info():
    """Get information about the last invoke time"""
    try:
        if os.path.exists(RATE_LIMIT_FILE):
            with open(RATE_LIMIT_FILE, 'r') as f:
                last_invoke_time = float(f.read().strip())
            return time.time() - last_invoke_time
    except:
        pass
    return None

# -------------------------
# 4. Scrape latest news
# -------------------------
def scrape_article_content(article_url):
    """Scrape the content of a single article using Readability extraction"""
    try:
        # Ensure URL is absolute
        if article_url.startswith('/'):
            article_url = 'https://www.wenxuecity.com' + article_url
        elif not article_url.startswith('http'):
            article_url = 'https://www.wenxuecity.com/' + article_url

        # Fetch HTML
        html_text = fetch_html(article_url)

        # Use Readability to extract clean article text
        article_text = extract_article_with_readability(html_text)

        if not article_text:
            raise Exception("Readability returned empty article text")

        return article_text[:2000] + "..." if len(article_text) > 2000 else article_text

    except requests.exceptions.RequestException as e:
        print(f"Network error scraping article {article_url}: {e}")
        return "网络连接错误，无法获取文章内容"
    except Exception as e:
        print(f"Error scraping article {article_url}: {e}")
        return f"内容获取失败: {str(e)}"

def scrape_wenxuecity():
    url = "https://www.wenxuecity.com/news/"

    # Add proper headers to avoid blocking
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        # Make request with timeout and SSL verification disabled for now
        # Note: In production, consider using proper certificates or verify=True
        r = requests.get(url, headers=headers, timeout=10, verify=False)
        r.raise_for_status()

        soup = BeautifulSoup(r.content, 'html.parser')
        news_articles = []

        # Extract article links with their titles
        article_links = []

        # Try to find news articles with links
        # Look for links that appear to be news articles
        all_links = soup.find_all('a', href=True)

        for link in all_links:
            href = link.get('href', '')
            title = link.get_text(strip=True)

            # Filter for likely news articles
            if (title and len(title) > 15 and len(title) < 200 and
                href and not any(skip in href.lower() for skip in ['javascript:', '#', 'mailto:', 'login', 'register']) and
                not any(skip in title.lower() for skip in ['首页', '登录', '注册', '更多', 'home', 'login', 'register']) and
                any(indicator in href.lower() for indicator in ['news', 'article', '/n/', '/a/'])):

                article_links.append({
                    'title': title,
                    'url': href
                })

                if len(article_links) >= 10:  # Limit to first 10 articles
                    break

        # If no specific news links found, try general approach
        if not article_links:
            for link in all_links[:20]:  # Check first 20 links
                href = link.get('href', '')
                title = link.get_text(strip=True)

                if (title and len(title) > 10 and len(title) < 200 and
                    href and href.startswith('/') and
                    not any(skip in title.lower() for skip in ['首页', '登录', '注册', '更多', 'home', 'login'])):

                    article_links.append({
                        'title': title,
                        'url': href
                    })

                    if len(article_links) >= 10:
                        break

        print(f"Found {len(article_links)} article links to scrape")

        # Scrape content for each article
        for i, article in enumerate(article_links, 1):
            print(f"Scraping article {i}/10: {article['title'][:50]}...")

            content = scrape_article_content(article['url'])

            # Create a summary format
            article_summary = f"""
新闻 {i}: {article['title']}
内容摘要: {content}
---
"""
            news_articles.append(article_summary.strip())

        return "\n\n".join(news_articles) if news_articles else "未能获取到新闻内容"

    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        return "网络连接错误，无法获取新闻"
    except Exception as e:
        print(f"Unexpected error: {e}")
        return "获取新闻时发生未知错误"

# -------------------------
# 5. Convert text to speech using AWS Polly
# -------------------------
def synthesize_with_polly(ssml_chunks):
    """
    Convert SSML chunks to MP3 files
    """
    polly = boto3.client('polly', region_name=AWS_REGION)
    audio_chunks = []

    for i, ssml in enumerate(ssml_chunks):
        response = polly.synthesize_speech(
            Engine=POLLY_ENGINE,
            VoiceId=VOICE_ID,
            OutputFormat="mp3",
            TextType="ssml",
            Text=ssml
        )

        # Read audio data directly into memory
        audio_data = response["AudioStream"].read()
        audio_chunks.append(audio_data)

    return audio_chunks


def text_to_speech(text):
    """Convert text to speech using AWS Polly and return audio bytes"""
    try:
        # Sanitize for SSML
        safe_text = sanitize_for_ssml(text)

        # Build SSML chunks
        ssml_chunks = build_ssml_chunks(safe_text)

        # Polly synthesis
        audio_chunks = synthesize_with_polly(ssml_chunks)

        # If multiple chunks, combine them (simple concatenation for MP3)
        if len(audio_chunks) == 1:
            return audio_chunks[0]
        else:
            # Concatenate all audio chunks into a single audio file
            combined_audio = b''.join(audio_chunks)
            return combined_audio

    except Exception as e:
        print(f"Error in text_to_speech: {e}")
        raise e

# -------------------------
# 6. Send to Telegram
# -------------------------
def send_to_telegram_voice(audio_data):
    """Send audio data as voice message to Telegram"""
    try:
        if not TELEGRAM_TOKEN or not CHAT_ID:
            print("Telegram credentials not configured")
            return False

        # Send voice message using Telegram Bot API
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVoice"

        files = {
            'voice': ('news.mp3', BytesIO(audio_data), 'audio/mpeg')
        }

        data = {
            'chat_id': CHAT_ID,
            'caption': '📰 最新新闻语音'
        }

        response = requests.post(url, files=files, data=data, timeout=30)
        response.raise_for_status()

        result = response.json()
        if result.get('ok'):
            print("Voice message sent successfully to Telegram")
            return True
        else:
            print(f"Telegram API error: {result}")
            return False

    except Exception as e:
        print(f"Error sending to Telegram: {e}")
        return False

# -------------------------
# 7. Lambda handler
# -------------------------
def lambda_handler(event, context):
    """Main Lambda handler function - handles both sync and async processing"""
    try:
        # Check if this is an async processing request
        is_async_processing = event.get('async_processing', False)

        if is_async_processing:
            # This is the async processing invocation
            print("Processing async request - starting news generation...")

            # Process news synchronously in this invocation
            news_text = scrape_wenxuecity()
            if not news_text or news_text.startswith("网络连接错误") or news_text.startswith("获取新闻时发生未知错误"):
                print(f"Failed to scrape news: {news_text}")
                return {
                    "statusCode": 500,
                    "body": json.dumps({
                        "message": "Failed to scrape news in async processing",
                        "error": news_text
                    })
                }

            print(f"Successfully scraped news: {len(news_text)} characters")

            # Convert to speech
            audio_data = text_to_speech(news_text)
            print("Successfully converted text to speech")

            # Send to Telegram if configured
            telegram_sent = False
            if TELEGRAM_TOKEN and CHAT_ID:
                telegram_sent = send_to_telegram_voice(audio_data)

            print(f"Async processing completed. Telegram sent: {telegram_sent}")

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "Async processing completed",
                    "telegram_sent": telegram_sent,
                    "audio_size": len(audio_data)
                })
            }

        else:
            # This is the initial user request
            print("Lambda function invoked - checking rate limit...")

            # Check rate limiting
            can_invoke, remaining_time = check_rate_limit()
            if not can_invoke:
                return {
                    "statusCode": 429,  # Too Many Requests
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*"
                    },
                    "body": json.dumps({
                        "message": "Rate limit exceeded. Please wait before invoking again.",
                        "error": "TOO_MANY_REQUESTS",
                        "remaining_time_seconds": int(remaining_time),
                        "retry_after_seconds": int(remaining_time),
                        "timestamp": time.time()
                    })
                }

            print("Rate limit check passed - triggering async processing...")

            # Trigger async processing by invoking this same Lambda function
            try:
                lambda_client = boto3.client('lambda', region_name=AWS_REGION)

                # Get the current function name from context
                function_name = context.function_name if context else 'news_lambda_function'

                # Invoke this function asynchronously with async flag
                async_payload = {
                    'async_processing': True
                }

                response = lambda_client.invoke(
                    FunctionName=function_name,
                    InvocationType='Event',  # Asynchronous invocation
                    Payload=json.dumps(async_payload)
                )

                print(f"Async Lambda invoked successfully: {response.get('StatusCode')}")

            except Exception as e:
                print(f"Failed to invoke async Lambda: {e}")
                # Fallback to synchronous processing if async fails
                print("Falling back to synchronous processing...")
                return process_news_sync()

            # Return immediate success response
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({
                    "message": "News processing started successfully",
                    "status": "processing",
                    "timestamp": time.time(),
                    "rate_limit_seconds": RATE_LIMIT_SECONDS,
                    "note": "Async processing triggered. Check Telegram for the voice message in 1-2 minutes."
                })
            }

    except Exception as e:
        print(f"Lambda handler error: {e}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "message": "Error processing request",
                "error": str(e),
                "timestamp": time.time()
            })
        }

def process_news_sync():
    """Fallback synchronous processing function"""
    try:
        print("Processing news synchronously...")

        # Scrape news
        news_text = scrape_wenxuecity()
        if not news_text or news_text.startswith("网络连接错误") or news_text.startswith("获取新闻时发生未知错误"):
            return {
                "statusCode": 500,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({
                    "message": "Failed to scrape news",
                    "error": news_text
                })
            }

        print(f"Successfully scraped news: {len(news_text)} characters")

        # Convert to speech
        audio_data = text_to_speech(news_text)
        print("Successfully converted text to speech")

        # Send to Telegram if configured
        telegram_sent = False
        if TELEGRAM_TOKEN and CHAT_ID:
            telegram_sent = send_to_telegram_voice(audio_data)

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "message": "News processing completed successfully",
                "news_length": len(news_text),
                "telegram_sent": telegram_sent,
                "audio_size": len(audio_data)
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "message": "Error processing news",
                "error": str(e)
            })
        }

# For local testing
if __name__ == "__main__":
    import sys
    # Set UTF-8 encoding for console output to handle Chinese characters
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    # Test the function locally
    test_event = {}
    test_context = {}

    result = lambda_handler(test_event, test_context)
    print("Lambda result:", result)

    # scrape_wenxuecity()