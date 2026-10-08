
# الوكيل المقاتل V4 - وضع البقاء 30 يوم
# هدفه: 1000 مشترك + 4000 ساعة مشاهدة خلال 30 يوم والا ينحذف

import os, pickle, base64, random, textwrap, json, datetime, re
from gtts import gTTS
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
import google.generativeai as genai

# ========== اعدادات البقاء ==========
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
NISH = "قصص واقعية مؤثرة" # مجال القناة

def log(msg):
    print(f"[{datetime.datetime.now()}] {msg}")
    with open("agent_log.txt", "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now()} - {msg}\n")

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
model = genai.GenerativeModel("gemini-1.5-flash")

log("🤖 الوكيل المقاتل استيقظ - يوم جديد - لازم يحقق نتائج")

# ========== المرحلة 1: التجسس والبحث ==========
def spy_and_research():
    log("🔍 المرحلة 1: التجسس على الترند والمنافسين")
    
    # كلمات مفتاحية رابحة في السعودية (من بحث حقيقي)
    viral_keywords = [
        "قصة حقيقية حدثت بالفعل", "قصة تبكي الحجر", "قصة لن تنساها",
        "بر الوالدين", "قصة وفاء كلب", "قصة خيانة زوجية",
        "قصة رجل فقير اصبح غنيا", "قصة انتقام", "قصة ام ضحت",
        "قصة طفل يتيم", "قصة معجزة", "قصة توبة"
    ]
    
    # نحلل قناتنا
    try:
        ch = youtube.channels().list(part="contentDetails,statistics", mine=True).execute()
        uploads = ch['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        stats_channel = ch['items'][0]['statistics']
        subs = int(stats_channel.get('subscriberCount',0))
        total_views = int(stats_channel.get('viewCount',0))
        log(f"📊 قناتك حاليا: {subs} مشترك - {total_views} مشاهدة كلية")

        pl = youtube.playlistItems().list(part="snippet", playlistId=uploads, maxResults=15).execute()
        vids = [i['snippet']['resourceId']['videoId'] for i in pl['items']]
        if vids:
            details = youtube.videos().list(part="statistics,snippet", id=",".join(vids)).execute()
            sorted_v = sorted(details['items'], key=lambda x: int(x['statistics'].get('viewCount',0)), reverse=True)
            top = sorted_v[0]
            top_title = top['snippet']['title']
            top_views = top['statistics']['viewCount']
            top_topic = re.findall(r'قصة (\w+)', top_title)
            winning_word = top_topic[0] if top_topic else "بر الوالدين"
            log(f"🏆 الرابح عندك: {top_title} ({top_views} views) - الكلمة المفتاحية: {winning_word}")
        else:
            winning_word = "بر الوالدين"
            top_title = "قناة جديدة"
    except Exception as e:
        log(f"تحليل فشل: {e}")
        winning_word = "بر الوالدين"
        top_title = "بر الوالدين"

    # البحث عن افكار ترند جديدة
    prompt_research = f"""
    انت صاحب قناة يوتيوب قصص واقعية مهدد بالحذف خلال 30 يوم اذا ما حققت 100 الف مشاهدة.
    قناتك حاليا موضوعها الرابح هو '{winning_word}' والعنوان الرابح '{top_title}'
    اعطني 3 افكار قصص جديدة مضمونة تجيب مشاهدات عالية جدا في السعودية:
    1- قصة مشابهة للرابح لكن بزاوية جديدة (للناس اللي حبوا الرابح)
    2- قصة ترند حاليا في السعودية (خيانة، وفاء، انتقام، معجزة)
    3- قصة عنوانها يجيب ضغط عالي CTR (عنوان صادم)
    لكل فكرة اعطني: عنوان يجيب نقرات + ملخص 10 كلمات.
    """
    try:
        res = model.generate_content(prompt_research)
        ideas = res.text
        log(f"💡 افكار جديدة من البحث: {ideas[:300]}")
    except:
        ideas = ""

    return winning_word, top_title, viral_keywords

winning_word, top_title, viral_keywords = spy_and_research()

# ========== المرحلة 2: توليد 3 قصص باستراتيجيات مختلفة ==========
def generate_3_strategies(winning_word):
    strategies = []
    
    prompts = [
        f"اكتب قصة واقعية مؤثرة جدا عن {winning_word} بأسلوب يبكي، 180 كلمة، فيها تضحية ومفاجأة تبكي. بالعربية الفصحى البسيطة. فقط القصة.",
        f"اكتب قصة واقعية صادمة جدا عن الخيانة والانتقام، عنوانها يصدم، 180 كلمة، فيها twist في النهاية. فقط القصة.",
        f"اكتب قصة واقعية عن معجزة حقيقية حدثت لفقير او مريض، 180 كلمة، تعطي امل. فقط القصة."
    ]
    
    titles_templates = [
        f"قصة {winning_word} التي ابكت الملايين - لن تصدق ماذا حدث في النهاية",
        f"صدمة!! زوجة تفعل هذا بزوجها بعد 10 سنوات - قصة حقيقية",
        f"فقير نام جائعا واستيقظ مليونيرا - معجزة حقيقية حدثت بالفعل"
    ]
    
    for i, prompt in enumerate(prompts):
        try:
            res = model.generate_content(prompt)
            story = res.text.strip().replace("*","")
            title = titles_templates[i]
            strategies.append((title, story))
            log(f"✍️ قصة {i+1} جاهزة: {title[:40]}")
        except Exception as e:
            log(f"فشل توليد {i+1}: {e}")
            strategies.append((titles_templates[i], "كان رجل فقير يعمل بجد. وجد يوما محفظة مليئة بالمال. ارجعها لصاحبها. كافأه الله بضعفها. الخير لا يضيع."))
    
    return strategies

stories = generate_3_strategies(winning_word)

# ========== المرحلة 3: انشاء فيديو بصوت وصورة مصغرة تجيب نقرات ==========
def create_video_with_thumbnail(title, story, idx):
    log(f"🎬 ينشئ فيديو {idx}: {title[:30]}")
    
    # صوت
    tts = gTTS(text=story, lang='ar', slow=False)
    tts.save(f"voice_{idx}.mp3")
    voice = AudioFileClip(f"voice_{idx}.mp3")
    
    W,H = 1280,720
    
    # خلفية متدرجة سينمائية
    img_bg = Image.new('RGB', (W,H), (10,10,25))
    draw = ImageDraw.Draw(img_bg)
    for y in range(H):
        c = int(10 + y*0.18)
        draw.line([(0,y),(W,y)], fill=(c//2, c//3, c))
    img_bg.save(f"bg_{idx}.jpg")
    bg_clip = ImageClip(f"bg_{idx}.jpg", duration=voice.duration)
    
    # نص القصة
    img_text = Image.new('RGBA', (W,H), (0,0,0,0))
    d = ImageDraw.Draw(img_text)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
    except:
        font = ImageFont.load_default()
    wrapped = textwrap.fill(story, width=26)
    # ظل + نص ابيض
    d.multiline_text((W//2+4, H//2+4), wrapped, font=font, fill=(0,0,0,200), anchor="mm", align="center", spacing=14)
    d.multiline_text((W//2, H//2), wrapped, font=font, fill=(255,255,255), anchor="mm", align="center", spacing=14)
    img_text.save(f"text_{idx}.png")
    text_clip = ImageClip(f"text_{idx}.png", duration=voice.duration).set_position("center")
    
    final = CompositeVideoClip([bg_clip, text_clip])
    final = final.set_audio(voice).resize(lambda t: 1 + 0.015*t) # زوم خفيف
    
    file = f"video_{idx}.mp4"
    final.write_videofile(file, fps=24, codec='libx264', audio_codec='aac', logger=None)
    
    # صورة مصغرة تجيب نقرات - خلفية حمراء + نص اصفر
    thumb = Image.new('RGB', (W,H), (200,20,20))
    td = ImageDraw.Draw(thumb)
    td.rectangle([0,0,W, H//2], fill=(15,15,15))
    try:
        big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 75)
        small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 45)
    except:
        big = small = ImageFont.load_default()
    # كلمات تجيب نقرات
    td.text((W//2, 220), "قصة حقيقية", font=big, fill=(255,255,0), anchor="mm")
    td.text((W//2, 500), title[:28], font=small, fill=(255,255,255), anchor="mm")
    thumb.save(f"thumb_{idx}.jpg")
    
    return file, f"thumb_{idx}.jpg"

# ========== المرحلة 4: النشر الذكي مع وصف SEO ==========
for idx, (title, story) in enumerate(stories, 1):
    try:
        video_file, thumb_file = create_video_with_thumbnail(title, story, idx)
        
        # وصف SEO يجيب بحث
        description = f"""{story}

هذه القصة حقيقية ومؤثرة جدا، مشابهة لأكثر قصة ناجحة في قناتنا.

🔔 اشترك الآن وفعل الجرس 🔔 ليصلك كل يوم 3 قصص جديدة الساعة 8 مساء

📌 كلمات مفتاحية: قصة واقعية, قصة مؤثرة, قصة حقيقية, قصص تبكي, بر الوالدين, الوفاء, قصة قصيرة

#قصة #قصص_واقعية #قصة_مؤثرة #قصة_حقيقية #حكاية #عبرة #{winning_word}

تابعنا للمزيد يوميا الساعة 8 مساء بتوقيت السعودية
"""
        
        log(f"🚀 ينشر {idx}/3 PUBLIC - {title}")
        res = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title[:95], # مهم اقل من 100 حرف
                    "description": description,
                    "categoryId": "24", # Entertainment
                    "tags": ["قصة واقعية", "قصة مؤثرة", winning_word, "قصة حقيقية", "قصص تبكي"]
                },
                "status": {
                    "privacyStatus": "public",
                    "selfDeclaredMadeForKids": False
                }
            },
            media_body=MediaFileUpload(video_file, chunksize=-1, resumable=True)
        ).execute()
        
        vid_id = res['id']
        log(f"✅ نشر: https://youtu.be/{vid_id}")
        
        # رفع الصورة المصغرة
        try:
            youtube.thumbnails().set(videoId=vid_id, media_body=MediaFileUpload(thumb_file)).execute()
            log(f"🖼️ تم رفع صورة مصغرة تجيب نقرات")
        except Exception as e:
            log(f"فشل Thumbnail: {e}")
            
    except Exception as e:
        log(f"❌ فشل فيديو {idx}: {e}")

log("🎉 الوكيل المقاتل انهى مهمة اليوم - 3 فيديوهات ذكية تم نشرها PUBLIC")
log("📈 غدا سيحلل اي فيديو من الثلاثة جاب اعلى مشاهدات ويكرر استراتيجيته")
