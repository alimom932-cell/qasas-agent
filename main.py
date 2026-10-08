import os, pickle, base64, textwrap
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
def log(m): print(m)

if os.getenv("TOKEN_B64"):
    open("token.pickle","wb").write(base64.b64decode(os.getenv("TOKEN_B64")))

with open("token.pickle","rb") as f:
    creds = pickle.load(f)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    open("token.pickle","wb").write(pickle.dumps(creds))

youtube = build('youtube','v3',credentials=creds)
genai.configure(api_key=GEMINI_KEY)

# يكتشف اي موديل شغال حاليا
available = None
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        log(f"Found model: {m.name}")
        if 'flash' in m.name:
            available = m.name
            break

if not available:
    available = "models/gemini-flash-latest"
log(f"Using model: {available}")
model = genai.GenerativeModel(available)

log("Agent V6 - auto model")
try:
    r = model.generate_content("اكتب قصة واقعية مؤثرة جدا عن بر الوالدين 200 كلمة بالعربية الفصحى فقط القصة")
    story = r.text.strip().replace("*","")[:600]
    log(f"Story ok: {story[:50]}")
except Exception as e:
    log(f"Gemini error {e}")
    story = "كان شاب يعمل ليل نهار ليعالج امه المريضة. باع كل ما يملك. وفي يوم وجد محفظة مليئة بالمال ارجعها لصاحبها فكافأه الله باضعافها."

title = "قصة بر الوالدين التي ابكت الملايين - قصة حقيقية مؤثرة"

# ننشئ الفيديو ونحفظه بدون رفع (لان يوتيوب بلوك اليوم)
tts = gTTS(text=story, lang='ar', slow=False)
tts.save("voice.mp3")
voice = AudioFileClip("voice.mp3")
W,H = 1280,720
bg = Image.new('RGB',(W,H),(12,12,30))
bg.save("bg.jpg")
bg_clip = ImageClip("bg.jpg", duration=voice.duration)
txt_img = Image.new('RGBA',(W,H),(0,0,0,0))
d = ImageDraw.Draw(txt_img)
try: font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",42)
except: font = ImageFont.load_default()
wrapped = textwrap.fill(story, width=28)
d.multiline_text((W//2,H//2),wrapped,font=font,fill=(255,255,255),anchor="mm",align="center",spacing=12)
txt_img.save("text.png")
text_clip = ImageClip("text.png", duration=voice.duration).set_position("center")
final = CompositeVideoClip([bg_clip,text_clip]).set_audio(voice)
final.write_videofile("video.mp4",fps=24,codec='libx264',audio_codec='aac',logger=None)
log("Video created locally - youtube blocked for today")

# نحاول الرفع - لو فشل نحفظ الفيديو كـ artifact
try:
    log(f"Uploading: {title}")
    res = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet":{"title":title[:95],"description":f"{story}\n\n#قصة","categoryId":"24"},
            "status":{"privacyStatus":"public","selfDeclaredMadeForKids":False}
        },
        media_body=MediaFileUpload("video.mp4",chunksize=-1,resumable=True)
    ).execute()
    log(f"SUCCESS https://youtu.be/{res['id']}")
except Exception as e:
    log(f"Upload failed today (expected): {e}")
    log("VIDEO READY - will auto upload tomorrow at 8pm after limit resets")
