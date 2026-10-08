# الوكيل المقاتل V4 - وضع البقاء 30 يوم
import os, pickle, base64, random, textwrap, json, datetime, re
from gtts import gTTS
from PIL import Image
# اصلاح مشكلة ANTIALIAS
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS
from moviepy.editor import *
from PIL import ImageDraw, ImageFont
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
import google.generativeai as genai

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
NISH = "قصص واقعية مؤثرة"

def log(msg):
    print(f"[{datetime.datetime.now()}] {msg}")

def setup_creds():
    if os.getenv("TOKEN_B64"):
        open("token.pickle","wb").write(base64.b64decode(os.getenv("TOKEN_B64")))
    if os.getenv("CLIENT_SECRET_B64"):
        open("client_secret.json","wb").write(base64.b64decode(os.getenv("CLIENT_SECRET_B64")))

setup_creds()

with open("token.pickle","rb") as f:
    creds = pickle.load(f)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    open("token.pickle","wb").write(pickle.dumps(creds))

youtube = build('youtube', 'v3', credentials=creds)
genai.configure(api_key=GEMINI_KEY)
try:
    model = genai.GenerativeModel("gemini-2.0-flash")
except:
    model = genai.GenerativeModel("gemini-flash-latest")

log("🤖 الوكيل استيقظ")

def spy_and_research():
    winning_word = "بر الوالدين"
    top_title = "بر الوالدين"
    try:
        ch = youtube.channels().list(part="contentDetails,statistics", mine=True).execute()
        log(f"📊 قناتك: {ch['items'][0]['statistics']}")
    except Exception as e:
        log(f"⚠️ تحليل القناة تخطيناه: {e}")
    viral_keywords = ["قصة حقيقية حدثت بالفعل", "قصة تبكي الحجر", "بر الوالدين"]
    prompt_research = f"انت صاحب قناة قصص واقعية. موضوعك الرابح '{winning_word}'. اعطني 3 افكار قصص جديدة مضمونة تجيب مشاهدات عالية في السعودية"
    try:
        res = model.generate_content(prompt_research)
        log(f"💡 افكار: {res.text[:300]}")
    except Exception as e:
        log(f"بحث فشل: {e}")
    return winning_word, top_title, viral_keywords

winning_word, top_title, viral_keywords = spy_and_research()

def generate_3_strategies(winning_word):
    strategies = []
    prompts = [
        f"اكتب قصة واقعية مؤثرة جدا عن {winning_word} بأسلوب يبكي، 180 كلمة، فيها تضحية ومفاجأة. بالعربية الفصحى البسيطة. فقط القصة.",
        f"اكتب قصة واقعية صادمة جدا عن الخيانة والانتقام، 180 كلمة، فيها twist. فقط القصة.",
        f"اكتب قصة واقعية عن معجزة حقيقية حدثت لفقير، 180 كلمة، تعطي امل. فقط القصة."
    ]
    titles_templates = [
        f"قصة {winning_word} التي ابكت الملايين - لن تصدق ماذا حدث",
        f"صدمة!! زوجة تفعل هذا بزوجها بعد 10 سنوات - قصة حقيقية",
        f"فقير نام جائعا واستيقظ مليونيرا - معجزة حقيقية"
    ]
    for i, prompt in enumerate(prompts):
        try:
            res = model.generate_content(prompt)
            story = res.text.strip().replace("*","")
            title = titles_templates[i]
            strategies.append((title, story))
            log(f"✍️ قصة {i+1} جاهزة")
        except Exception as e:
            log(f"فشل توليد {i+1}: {e}")
            strategies.append((titles_templates[i], "كان رجل فقير يعمل بجد. وجد محفظة مليئة بالمال. ارجعها لصاحبها. كافأه الله بضعفها."))
    return strategies

stories = generate_3_strategies(winning_word)

def create_video_with_thumbnail(title, story, idx):
    log(f"🎬 ينشئ فيديو {idx}")
    tts = gTTS(text=story, lang='ar', slow=False)
    tts.save(f"voice_{idx}.mp3")
    voice = AudioFileClip(f"voice_{idx}.mp3")
    W,H = 1280,720
    img_bg = Image.new('RGB', (W,H), (10,10,25))
    draw = ImageDraw.Draw(img_bg)
    for y in range(H):
        c = int(10 + y*0.18)
        draw.line([(0,y),(W,y)], fill=(c//2, c//3, c))
    img_bg.save(f"bg_{idx}.jpg")
    bg_clip = ImageClip(f"bg_{idx}.jpg", duration=voice.duration)
    img_text = Image.new('RGBA', (W,H), (0,0,0,0))
    d = ImageDraw.Draw(img_text)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
    except:
        font = ImageFont.load_default()
    wrapped = textwrap.fill(story, width=26)
    d.multiline_text((W//2+4, H//2+4), wrapped, font=font, fill=(0,0,0,200), anchor="mm", align="center", spacing=14)
    d.multiline_text((W//2, H//2), wrapped, font=font, fill=(255,255,255), anchor="mm", align="center", spacing=14)
    img_text.save(f"text_{idx}.png")
    text_clip = ImageClip(f"text_{idx}.png", duration=voice.duration).set_position("center")
    final = CompositeVideoClip([bg_clip, text_clip])
    final = final.set_audio(voice).resize(lambda t: 1 + 0.015*t)
    file = f"video_{idx}.mp4"
    final.write_videofile(file, fps=24, codec='libx264', audio_codec='aac', logger=None)
    thumb = Image.new('RGB', (W,H), (200,20,20))
    td = ImageDraw.Draw(thumb)
    td.rectangle([0,0,W, H//2], fill=(15,15,15))
    try:
        big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 75)
        small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 45)
    except:
        big = small = ImageFont.load_default()
    td.text((W//2, 220), "قصة ح
