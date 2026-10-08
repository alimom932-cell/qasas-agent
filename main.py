import os, pickle, base64, textwrap, datetime, re
from gtts import gTTS
from PIL import Image
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS
from moviepy.editor import *
from PIL import ImageDraw, ImageFont
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
import google.generativeai as genai

GEMINI_KEY = os.getenv("GEMINI_API_KEY")

def log(msg):
    print(msg)

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

log("Agent started")
winning_word = "Alwalidain"
try:
    ch = youtube.channels().list(part="statistics", mine=True).execute()
    log(f"Channel stats: {ch['items'][0]['statistics']}")
except Exception as e:
    log(f"Channel check skipped: {e}")

def generate_3():
    strategies = []
    prompts = [
        "Write a very emotional real story about bir al walidain, 180 words, with sacrifice and surprise ending. In simple Arabic. Only story.",
        "Write a shocking real story about betrayal and revenge, 180 words, twist ending. In Arabic. Only story.",
        "Write a real miracle story about a poor man becoming rich, 180 words, hopeful. In Arabic. Only story."
    ]
    titles_ar = [
        "قصة بر الوالدين التي ابكت الملايين - لن تصدق النهاية",
        "صدمة زوجة تفعل هذا بزوجها بعد 10 سنوات - قصة حقيقية",
        "فقير نام جائعا واستيقظ مليونيرا - معجزة حقيقية"
    ]
    for i, p in enumerate(prompts):
        try:
            res = model.generate_content(p)
            story = res.text.strip().replace("*","")
            strategies.append((titles_ar[i], story))
            log(f"Story {i+1} ready")
        except Exception as e:
            log(f"Gen {i+1} failed: {e}")
            strategies.append((titles_ar[i], "كان رجل فقير يعمل بجد. وجد محفظة مليئة بالمال. ارجعها لصاحبها. كافأه الله بضعفها."))
    return strategies

stories = generate_3()

def create_video(title, story, idx):
    log(f"Creating video {idx}")
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
    td.text((W//2, 220), "QISSA HAQIQIYA", font=big, fill=(255,255,0), anchor="mm")
    td.text((W//2, 500), title[:28], font=small, fill=(255,255,255), anchor="mm")
    thumb.save(f"thumb_{idx}.jpg")
    return file, f"thumb_{idx}.jpg"

for idx, (title, story) in enumerate(stories, 1):
    try:
        video_file, thumb_file = create_video(title, story, idx)
        description = f"{story}\n\n#qissa #qisas_waqiea"
        log(f"Uploading {idx}/3 PUBLIC - {title}")
        res = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {"title": title[:95], "description": description, "categoryId": "24", "tags": ["qissa", "qissa haqiqiya"]},
                "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
            },
            media_body=MediaFileUpload(video_file, chunksize=-1, resumable=True)
        ).execute()
        vid_id = res['id']
        log(f"DONE: https://youtu.be/{vid_id}")
        youtube.thumbnails().set(videoId=vid_id, media_body=MediaFileUpload(thumb_file)).execute()
    except Exception as e:
        log(f"Video {idx} failed: {e}")
log("Finished 3 videos PUBLIC")
