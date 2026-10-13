# -*- coding: utf-8 -*-
import os, re, json, base64, random, pickle, textwrap, requests, xml.etree.ElementTree as ET
from datetime import datetime
import PIL
from PIL import Image, ImageDraw, ImageFont, ImageFilter
if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
import google.generativeai as genai
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from gtts import gTTS
from moviepy.editor import VideoFileClip, ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips, vfx

W,H=1280,720
OUT="final_video.mp4"
HIST="history.json"
MARK=".last_upload"
GEMINI_KEY=os.getenv("GEMINI_API_KEY","").strip()
PEXELS_KEY=os.getenv("PEXELS_API_KEY","").strip()

def log(m): print(m, flush=True)

def get_youtube():
    if os.getenv("TOKEN_B64"):
        open("token.pickle","wb").write(base64.b64decode(os.getenv("TOKEN_B64")))
    with open("token.pickle","rb") as f:
        creds=pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        open("token.pickle","wb").write(pickle.dumps(creds))
    return build('youtube','v3',credentials=creds)

def get_gemini():
    genai.configure(api_key=GEMINI_KEY)
    name="models/gemini-flash-latest"
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods and 'flash' in m.name.lower():
            name=m.name; break
    log(f"Using {name}")
    return genai.GenerativeModel(name)

def load_history():
    if os.path.exists(HIST):
        try: return json.loads(open(HIST,"r",encoding="utf-8").read())
        except: return []
    return []

def save_history(topic,title,vid=None):
    h=load_history()
    h.append({"date":datetime.now().isoformat(),"topic":topic,"title":title,"video_id":vid})
    open(HIST,"w",encoding="utf-8").write(json.dumps(h[-100:],ensure_ascii=False,indent=2))

def is_dup(t):
    for x in load_history()[-30:]:
        if x["topic"].lower() in t.lower() or t.lower() in x["topic"].lower():
            return True
    return False

def get_trend(model):
    keys=[]
    try:
        r=requests.get("https://trends.google.com/trending/rss?geo=SA",timeout=10)
        root=ET.fromstring(r.content)
        for it in root.findall(".//item/title")[:5]:
            keys.append(it.text)
    except: pass
    hist=", ".join([h["topic"] for h in load_history()[-10:]])
    prompt=f"اعطني موضوع قصة واحدة ترند اليوم في السعودية غير مكرر. الممنوع: {hist}. الترند الحالي: {keys[:3]}. اختر من: بر الوالدين، عقوق، أم ضحت، يتيم، خيانة، غدر، فقير غني، توبة. أجب بكلمتين فقط"
    for _ in range(3):
        try:
            t=model.generate_content(prompt).text.strip()[:40].split("\n")[0]
            if not is_dup(t) and len(t)>3:
                log(f"TREND: {t}"); return t
        except: pass
    return random.choice(["أم باعت ذهبها","شاب عق أمه","يتيم أصبح غني","أب مظلوم","خيانة صديق"])

def get_bgs(topic,n):
    paths=[]
    qmap={"أم":"mother crying sad","أب":"father old sad","يتيم":"orphan sad","فقير":"poor house","خيانة":"sad woman alone"}
    q="sad mother old house"
    for k,v in qmap.items():
        if k in topic: q=v; break
    for i in range(n):
        ok=False
        if PEXELS_KEY:
            try:
                r=requests.get(f"https://api.pexels.com/videos/search?query={q}&per_page=2&orientation=landscape",headers={"Authorization":PEXELS_KEY},timeout=15).json()
                if r.get('videos'):
                    link=r['videos'][0]['video_files'][0]['link']
                    open(f"v{i}.mp4","wb").write(requests.get(link,timeout=20).content)
                    paths.append(f"v{i}.mp4"); ok=True
            except: pass
        if not ok:
            img=Image.new('RGB',(W,H),(12+i*2,10,20+i*3))
            d=ImageDraw.Draw(img)
            for y in range(H):
                d.line([(0,y),(W,y)],fill=(12+y//20,10,20+y//10))
            img=img.filter(ImageFilter.GaussianBlur(1.5))
            img.save(f"b{i}.jpg")
            paths.append(f"b{i}.jpg")
    return paths

def voice_no_music(txt):
    paused=txt.replace(".",".... ")
    try:
        import edge_tts, asyncio
        async def gen():
            await edge_tts.Communicate(paused,"ar-SA-HamedNeural",rate="-5%").save("voice.mp3")
        asyncio.run(gen())
        if os.path.exists("voice.mp3"):
            return AudioFileClip("voice.mp3")
    except: pass
    gTTS(text=paused,lang='ar',slow=True).save("voice.mp3")
    return AudioFileClip("voice.mp3")

def main():
    if os.path.exists(MARK):
        try:
            if (datetime.now().timestamp()-float(open(MARK).read()))<20*3600:
                log("SKIP - in cooldown until midnight"); return
            os.remove(MARK)
        except: pass
    yt=get_youtube()
    model=get_gemini()
    log("V10 TREND NO MUSIC START")
    topic=get_trend(model)
    story=model.generate_content(f'اكتب قصة واقعية مؤثرة جدا عن "{topic}" 250 كلمة، بداية صادمة، نهاية تبكي، فصحى بسيطة، فقرات قصيرة، بدون موسيقى').text.strip().replace("*","")[:900]
    sents=[s.strip() for s in re.split(r'[.\n]+',story) if len(s.strip())>12][:10]
    title=model.generate_content(f'عنوان يوتيوب 55 حرف عن "{topic}" فيه "قصة حقيقية" يجيب نقرات').text.strip()[:95]
    if "قصة" not in title: title=f"قصة حقيقية {topic} - النهاية أبكت الملايين"
    bgs=get_bgs(topic,len(sents))
    voice=voice_no_music(story)
    dur=voice.duration/len(sents)
    clips=[]
    for i,(s,bg) in enumerate(zip(sents,bgs)):
        base=VideoFileClip(bg).subclip(0,min(dur+0.5,15)).resize((W,H)).set_duration(dur).fx(vfx.colorx,0.55) if bg.endswith(".mp4") else ImageClip(bg,duration=dur).resize(lambda t:1+0.04*t)
        txt=Image.new('RGBA',(W,H),(0,0,0,0))
        dr=ImageDraw.Draw(txt)
        try: fn=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",58)
        except: fn=ImageFont.load_default()
        w=textwrap.fill(s,width=22)
        dr.multiline_text((W//2+4,H//2+4),w,font=fn,fill=(0,0,0,220),anchor="mm",align="center",spacing=12)
        dr.multiline_text((W//2,H//2),w,font=fn,fill=(255,255,255),anchor="mm",align="center",spacing=12)
        txt.save(f"t{i}.png")
        tc=ImageClip(f"t{i}.png",duration=dur).set_position("center").fadein(0.3).fadeout(0.3)
        clips.append(CompositeVideoClip([base,tc],size=(W,H)))
    final=concatenate_videoclips(clips,method="compose").set_audio(voice)
    final.write_videofile(OUT,fps=24,codec='libx264',audio_codec='aac',logger=None)
    log("Video NO MUSIC done")
    thumb=Image.new('RGB',(W,H),(15,15,15))
    d=ImageDraw.Draw(thumb)
    d.rectangle([0,0,W,H//2],fill=(170,20,20))
    try: big=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",90); mid=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",52)
    except: big=mid=ImageFont.load_default()
    d.text((W//2,200),"قصة حقيقية",font=big,fill=(255,235,0),anchor="mm")
    d.text((W//2,500),topic[:30],font=mid,fill=(255,255,255),anchor="mm")
    thumb.save("thumb.jpg")
    desc=f"{story}\n\nقصة اليوم: {topic}\n\n#قصة_حقيقية #ترند_السعودية"
    try:
        res=yt.videos().insert(part="snippet,status",body={"snippet":{"title":title,"description":desc,"categoryId":"24","tags":["قصة حقيقية","ترند",topic]},"status":{"privacyStatus":"public","selfDeclaredMadeForKids":False}},media_body=MediaFileUpload(OUT,chunksize=-1,resumable=True)).execute()
        log(f"SUCCESS https://youtu.be/{res['id']}")
        yt.thumbnails().set(videoId=res['id'],media_body=MediaFileUpload("thumb.jpg")).execute()
        save_history(topic,title,res['id'])
        if os.path.exists(MARK): os.remove(MARK)
    except Exception as e:
        log(f"Upload fail {e}")
        if "uploadLimitExceeded" in str(e) or "exceeded" in str(e):
            open(MARK,"w").write(str(datetime.now().timestamp()))
            save_history(topic,title,None)

if __name__=="__m
