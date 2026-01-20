import requests
from bs4 import BeautifulSoup
import boto3
# from telegram import Bot
# from pydub import AudioSegment
import os

# -------------------------
# 1. Configuration
# -------------------------
AWS_REGION = 'us-east-1'
VOICE_ID = 'Zhiyu'
# TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
# CHAT_ID = os.environ['CHAT_ID']

TMP_MP3 = '/tmp/news.mp3'
TMP_OGG = '/tmp/news.ogg'

# -------------------------
# 2. Scrape latest news
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
# 3. Convert text to speech
# -------------------------
def text_to_speech(text, mp3_file):
    polly = boto3.client('polly', region_name=AWS_REGION)
    ssml_text = "<speak>" + text.replace("\n", "<break time='700ms'/>") + "</speak>"

    response = polly.synthesize_speech(
        Text=ssml_text,
        TextType='ssml',
        OutputFormat='mp3',
        VoiceId=VOICE_ID
    )

    with open(mp3_file, 'wb') as f:
        f.write(response['AudioStream'].read())

# -------------------------
# 4. Convert MP3 → OGG/Opus for Telegram voice
# -------------------------
def convert_mp3_to_ogg(mp3_file, ogg_file):
    audio = AudioSegment.from_file(mp3_file, format="mp3")
    audio.export(ogg_file, format='ogg', codec='libopus')

# -------------------------
# 5. Send to Telegram
# -------------------------
def send_to_telegram_voice(ogg_file):
    bot = Bot(token=TELEGRAM_TOKEN)
    with open(ogg_file, 'rb') as f:
        bot.send_voice(chat_id=CHAT_ID, voice=f, caption="📰 最新新闻语音")

# -------------------------
# 6. Lambda handler
# -------------------------
def lambda_handler(event, context):
    news_text = scrape_wenxuecity()
    if not news_text:
        return {"statusCode": 200, "body": "No news found."}

    text_to_speech(news_text, TMP_MP3)
    convert_mp3_to_ogg(TMP_MP3, TMP_OGG)
    send_to_telegram_voice(TMP_OGG)

    return {"statusCode": 200, "body": "News sent successfully."}



if __name__ == "__main__":
    import sys
    # Set UTF-8 encoding for console output to handle Chinese characters
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    res = scrape_wenxuecity()

    try:
        print(res)
    except UnicodeEncodeError:
        # Fallback: encode to bytes and decode with error handling
        print(res.encode('utf-8', errors='replace').decode('utf-8'))