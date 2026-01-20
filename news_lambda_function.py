import json
import requests
from bs4 import BeautifulSoup
import boto3
import os
from io import BytesIO
import time

# -------------------------
# 1. Configuration
# -------------------------
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
VOICE_ID = os.environ.get('VOICE_ID', 'Zhiyu')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

# Rate limiting configuration
RATE_LIMIT_FILE = '/tmp/last_invoke_time.txt' if os.name != 'nt' else 'last_invoke_time.txt'
RATE_LIMIT_SECONDS = 60  # 1 minute

# -------------------------
# 2. Rate Limiting Functions
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
# 3. Scrape latest news
# -------------------------
def scrape_article_content(article_url, headers):
    """Scrape the content of a single article"""
    try:
        # Ensure URL is absolute
        if article_url.startswith('/'):
            article_url = 'https://www.wenxuecity.com' + article_url
        elif not article_url.startswith('http'):
            article_url = 'https://www.wenxuecity.com/' + article_url

        response = requests.get(article_url, headers=headers, timeout=15, verify=False)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Try different selectors to find article content
        content_selectors = [
            'div.content', 'div.article-content', 'div.news-content',
            'div[class*="content"]', 'div[class*="article"]',
            'article', 'main', 'div.text'
        ]

        content = ""
        for selector in content_selectors:
            content_div = soup.select_one(selector)
            if content_div:
                # Extract text and clean it
                paragraphs = content_div.find_all(['p', 'div'])
                if paragraphs:
                    content = ' '.join([p.get_text(strip=True) for p in paragraphs[:5]])  # First 5 paragraphs
                else:
                    content = content_div.get_text(strip=True)[:1000]  # First 1000 chars
                break

        # Fallback: get any substantial text content
        if not content or len(content) < 50:
            all_text = soup.get_text(strip=True)
            # Find content after common navigation elements
            start_markers = ['新闻', '报道', '消息', '据']
            for marker in start_markers:
                if marker in all_text:
                    start_idx = all_text.find(marker)
                    content = all_text[start_idx:start_idx+600]
                    break

            if not content:
                content = all_text[:600] if all_text else "无法提取内容"

        return content[:1000] + "..." if len(content) > 1000 else content

    except Exception as e:
        print(f"Error scraping article {article_url}: {e}")
        return "内容获取失败"

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

            content = scrape_article_content(article['url'], headers)

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
# 4. Convert text to speech using AWS Polly
# -------------------------
def text_to_speech(text):
    """Convert text to speech using AWS Polly and return audio bytes"""
    try:
        polly = boto3.client('polly', region_name=AWS_REGION)

        # Split text into chunks if it's too long (Polly has a 3000 character limit)
        max_chars = 2800  # Leave some buffer
        text_chunks = []

        if len(text) <= max_chars:
            text_chunks = [text]
        else:
            # Split by sentences or paragraphs
            sentences = text.split('。')
            current_chunk = ""

            for sentence in sentences:
                if len(current_chunk + sentence + '。') <= max_chars:
                    current_chunk += sentence + '。'
                else:
                    if current_chunk:
                        text_chunks.append(current_chunk)
                    current_chunk = sentence + '。'

            if current_chunk:
                text_chunks.append(current_chunk)

        # Convert each chunk to audio and combine
        audio_chunks = []
        for i, chunk in enumerate(text_chunks):
            print(f"Processing text chunk {i+1}/{len(text_chunks)}")
            ssml_text = "<speak>" + chunk.replace("\n", "<break time='700ms'/>") + "</speak>"

            response = polly.synthesize_speech(
                Text=ssml_text,
                TextType='ssml',
                OutputFormat='mp3',
                VoiceId=VOICE_ID
            )

            audio_chunks.append(response['AudioStream'].read())

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
# 5. Send to Telegram
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
# 6. Lambda handler
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