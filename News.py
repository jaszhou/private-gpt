import requests
from bs4 import BeautifulSoup
import boto3
from telegram import Bot
from pydub import AudioSegment
import os

# -------------------------
# 1. Configuration
# -------------------------
AWS_REGION = 'us-east-1'
VOICE_ID = 'Zhiyu'
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
CHAT_ID = os.environ['CHAT_ID']

TMP_MP3 = '/tmp/news.mp3'
TMP_OGG = '/tmp/news.ogg'

# -------------------------
# 2. Scrape latest news
# -------------------------
def scrape_wenxuecity():
    url = "https://www.wenxuecity.com/news/"
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')

    news_items = []

    for section in ['焦点', '国际']:
        section_div = soup.find('div', text=section)
        if section_div:
            ul = section_div.find_next('ul')
            if ul:
                for li in ul.find_all('li', limit=3):
                    title = li.get_text(strip=True)
                    news_items.append(f"{section}新闻：{title}")

    return "\n".join(news_items)

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
