import json
import re
import html
import requests
from bs4 import BeautifulSoup
import boto3
import os
from io import BytesIO
import time
from urllib.parse import urljoin

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

# OurSteps scraping is disabled by default.
# The fid=43 (新闻汇总) forum is login-gated for guests: the site answers HTTP 200
# with a Discuz "提示信息" permission page instead of the article, so the scraper
# only ever returned navigation boilerplate. Set ENABLE_OURSTEPS_SCRAPE=true to
# opt back in (requires a valid session cookie to be useful).
ENABLE_OURSTEPS_SCRAPE = os.environ.get('ENABLE_OURSTEPS_SCRAPE', 'false').lower() in ('1', 'true', 'yes')

oursteps_url = "https://www.oursteps.com.au/bbs/forum.php?mod=forumdisplay&fid=43&page=1"
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
# Markers of site chrome (nav, breadcrumb, byline) that can precede the body.
_PAGE_CHROME_MARKERS = ('advertisement', '您的位置：', '文章来源:', '被阅读次数')


def _strip_page_chrome(text):
    """Drop leading navigation/breadcrumb/byline chrome from extracted text.

    Only the first 600 characters are inspected, so a marker appearing deeper in
    a genuine article cannot truncate it.
    """
    if not text:
        return text

    head = text[:600]
    cut = 0
    for marker in _PAGE_CHROME_MARKERS:
        idx = head.find(marker)
        if idx == -1:
            continue
        # The byline block ends with the read-counter controls; prefer that
        # boundary, otherwise stop just past the marker itself.
        end = head.find('A-AA+', idx)
        cut = max(cut, end + len('A-AA+') if end != -1 else idx + len(marker))

    return text[cut:].lstrip('|-: ') if cut else text


def _extract_article_text(container):
    """Text of a container, preferring real paragraphs over empty wrappers.

    Many templates ship placeholder ``<p>`` elements and keep the body in bare
    text nodes, so the paragraph text is only used when it covers most of the
    container; otherwise the container's own text wins.
    """
    whole = container.get_text(' ', strip=True)
    paragraphs = [p.get_text(' ', strip=True) for p in container.find_all('p')]
    paragraphs = [p for p in paragraphs if len(p) > 20]
    joined = ' '.join(paragraphs)

    return joined if len(joined) >= max(50, len(whole) * 0.5) else whole


# The source site throttles bursts: a run that fetches ~11 pages in a few
# seconds gets 403 on the later ones, from a cloud IP especially.
BROWSER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}
RETRY_STATUS = {403, 429, 500, 502, 503, 504}
RETRY_DELAYS = (1, 3)
ARTICLE_DELAY_SECONDS = 0.7


def _fetch(url, headers, timeout=10, attempts=2):
    """GET a URL, retrying the transient blocks the source site returns."""
    last_error = None
    for attempt in range(attempts):
        try:
            response = requests.get(url, headers=headers, timeout=timeout, verify=False)
            if response.status_code not in RETRY_STATUS:
                response.raise_for_status()
                return response
            last_error = requests.exceptions.HTTPError(
                f"{response.status_code} Client Error for url: {url}", response=response)
        except requests.exceptions.RequestException as e:
            last_error = e

        if attempt < attempts - 1:
            delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
            print(f"Retrying in {delay}s after {last_error}")
            time.sleep(delay)

    raise last_error


def scrape_article_content(article_url, headers, base_url='https://www.wenxuecity.com'):
    """Scrape the content of a single article"""
    try:
        # Ensure URL is absolute for the given source site
        article_url = urljoin(base_url, article_url)

        response = _fetch(article_url, headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Try different selectors to find article content, most specific first:
        # generic class* matches come last because they can wrap navigation.
        content_selectors = [
            'article#articleContent', '#articleContent',
            'div.article-content', 'div.news-content', 'div.content',
            'article', 'main', 'div.text',
            # Forum-style selectors (e.g., OurSteps/Discuz)
            'td.t_f', 'div.t_fsz', 'div.pcb', 'div.postmessage',
            'div[class*="article"]', 'div[class*="content"]'
        ]

        content = ""
        for selector in content_selectors:
            content_div = soup.select_one(selector)
            if not content_div:
                continue
            candidate = _extract_article_text(content_div)
            if len(candidate) >= 50:
                content = candidate
                break

        # Fallback: the whole page, minus its chrome
        if len(content) < 50:
            all_text = soup.get_text(' ', strip=True)
            content = _strip_page_chrome(all_text) or all_text
            if len(content) < 50:
                content = all_text[:2000] if all_text else "无法提取内容"

        content = re.sub(r'\s+', ' ', _strip_page_chrome(content)).strip()
        return content[:2000] + "..." if len(content) > 2000 else content

    except Exception as e:
        print(f"Error scraping article {article_url}: {e}")
        return "内容获取失败"

def scrape_wenxuecity():
    url = "https://www.wenxuecity.com/news/"

    # Add proper headers to avoid blocking
    headers = dict(BROWSER_HEADERS)

    try:
        # Make request with timeout and SSL verification disabled for now
        # Note: In production, consider using proper certificates or verify=True
        r = _fetch(url, headers, timeout=10)
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

            content = scrape_article_content(article['url'], headers, base_url=url)

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

def _has_significant_words(content, min_estimated_words=80):
    """Validate scraped text has enough meaningful content."""
    if not content:
        return False

    cleaned = re.sub(r'\s+', ' ', content).strip()
    if len(cleaned) < 180:
        return False

    english_words = len(re.findall(r'[A-Za-z0-9]+', cleaned))
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', cleaned))
    estimated_words = english_words + (chinese_chars // 2)
    return estimated_words >= min_estimated_words

def scrape_oursteps():
    if not ENABLE_OURSTEPS_SCRAPE:
        print("OurSteps scraping is disabled (ENABLE_OURSTEPS_SCRAPE is not true) - skipping")
        return "OurSteps 抓取已禁用"

    url = oursteps_url

    # Add proper headers to avoid blocking
    headers = dict(BROWSER_HEADERS)

    try:
        # Make request with timeout and SSL verification disabled for now
        # Note: In production, consider using proper certificates or verify=True
        r = _fetch(url, headers, timeout=10)
        r.raise_for_status()

        soup = BeautifulSoup(r.content, 'html.parser')
        news_articles = []

        # Extract article links with their titles
        article_links = []

        # Try to find thread links
        all_links = soup.find_all('a', href=True)

        for link in all_links:
            href = link.get('href', '')
            title = link.get_text(strip=True)

            # Filter for likely thread/article links
            if (title and len(title) > 15 and len(title) < 200 and
                href and not any(skip in href.lower() for skip in ['javascript:', '#', 'mailto:', 'login', 'register']) and
                not any(skip in title.lower() for skip in ['首页', '登录', '注册', '更多', 'home', 'login', 'register']) and
                any(indicator in href.lower() for indicator in ['viewthread', 'tid=', 'thread'])):

                article_links.append({
                    'title': title,
                    'url': urljoin(url, href)
                })

                if len(article_links) >= 10:  # Limit to first 10 articles
                    break

        # If no specific thread links found, try general approach
        if not article_links:
            for link in all_links[:30]:  # Check first 30 links
                href = link.get('href', '')
                title = link.get_text(strip=True)

                if (title and len(title) > 10 and len(title) < 200 and
                    href and
                    not any(skip in title.lower() for skip in ['首页', '登录', '注册', '更多', 'home', 'login'])):

                    article_links.append({
                        'title': title,
                        'url': urljoin(url, href)
                    })

                    if len(article_links) >= 10:
                        break

        print(f"Found {len(article_links)} oursteps links to scrape")

        # Scrape content for each article
        for i, article in enumerate(article_links, 1):
            print(f"Scraping oursteps article {i}/10: {article['title'][:50]}...")

            content = scrape_article_content(article['url'], headers, base_url=url)

            # Validate content has meaningful length/word amount
            if not _has_significant_words(content):
                print(f"Skipping short or low-content article: {article['title'][:50]}...")
                continue

            # Create a summary format
            article_summary = f"""
新闻 {i}: {article['title']}
内容摘要: {content}
---
"""
            # print(f"Article {i} summary:\n{article_summary}")
            news_articles.append(article_summary.strip())

        return "\n\n".join(news_articles) if news_articles else "未能获取到足够内容的新闻"

    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        return "网络连接错误，无法获取新闻"
    except Exception as e:
        print(f"Unexpected error: {e}")
        return "获取新闻时发生未知错误"

def scrape_wenxuecity_detailed():
    """Scrape news and return detailed information for each article"""
    url = "https://www.wenxuecity.com/news/"

    # Add proper headers to avoid blocking
    headers = dict(BROWSER_HEADERS)

    try:
        # Make request with timeout and SSL verification disabled for now
        # Note: In production, consider using proper certificates or verify=True
        r = _fetch(url, headers, timeout=10)
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

            try:
                content = scrape_article_content(article['url'], headers)
            except Exception as e:
                print(f"Error scraping article {article['url']}: {e}")
                content = "内容获取失败"

            # Never pass placeholder text on to speech: a blocked or empty fetch
            # would otherwise be narrated as an article.
            if not _has_significant_words(content):
                print(f"Skipping article without usable content: {article['title'][:50]}...")
                continue

            # Add the article with both title and content
            news_articles.append({
                'title': article['title'],
                'content': content,
                'url': article['url']
            })

            # Space out requests so the site does not treat the run as a burst.
            time.sleep(ARTICLE_DELAY_SECONDS)

        return news_articles

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

def send_to_telegram_voice_with_caption(audio_data, caption):
    """Send audio data as voice message to Telegram with custom caption"""
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
            'caption': f"📰 {caption}"  # Use the article title as caption
        }

        response = requests.post(url, files=files, data=data, timeout=30)
        response.raise_for_status()

        result = response.json()
        if result.get('ok'):
            print(f"Voice message sent successfully to Telegram with caption: {caption}")
            return True
        else:
            print(f"Telegram API error: {result}")
            return False

    except Exception as e:
        print(f"Error sending to Telegram: {e}")
        return False

def sanitize_for_ssml(text):
    """
    Make text 100% safe for Amazon Polly SSML
    """
    text = re.sub(r'[\r\n]+', ' ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    text = html.escape(text)
    return text.strip()

# -------------------------
# 6. Lambda handler
# -------------------------
def lambda_handler(event, context):
    """Main Lambda handler function - synchronous processing only"""
    try:
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

        print("Rate limit check passed - processing news...")

        # Process news synchronously
        news_articles = scrape_wenxuecity_detailed()
        if not news_articles or isinstance(news_articles, str):
            print(f"Failed to scrape news: {news_articles}")
            return {
                "statusCode": 500,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({
                    "message": "Failed to scrape news",
                    "error": news_articles if isinstance(news_articles, str) else "Unknown error"
                })
            }

        print(f"Successfully scraped {len(news_articles)} news articles")

        # Process each article separately
        total_articles = len(news_articles)
        successful_articles = 0
        
        for i, article in enumerate(news_articles):
            print(f"Processing article {i+1}/{total_articles}: {article['title']}")
            print(f"Content: {article['content']}")
            
            # Convert article content to speech
            try:
                audio_data = text_to_speech(sanitize_for_ssml(article['content']))
                print(f"Successfully converted article {i+1} to speech")
                
                # Send to Telegram if configured
                telegram_sent = False
                if TELEGRAM_TOKEN and CHAT_ID:
                    telegram_sent = send_to_telegram_voice_with_caption(audio_data, article['title'])
                
                if telegram_sent:
                    successful_articles += 1
                    
                print(f"Article {i+1} processed. Telegram sent: {telegram_sent}")
                
            except Exception as e:
                print(f"Error processing article {i+1}: {e}")
                continue

        print(f"Processing completed. Successfully sent {successful_articles}/{total_articles} articles to Telegram.")

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "message": "News processing completed successfully",
                "total_articles": total_articles,
                "successful_articles": successful_articles,
                "timestamp": time.time()
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
    # scrape_oursteps()  # disabled: fid=43 is login-gated for guests, see ENABLE_OURSTEPS_SCRAPE
