#!/usr/bin/env python3
import argparse, cgi, json, os, sqlite3, subprocess, threading, time, uuid
from datetime import datetime
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib import request

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "assets"
DATA = Path(os.environ.get("MEETING_DATA_DIR", ROOT / "data")).resolve()
DB = DATA / "meetings.db"
LOCK = threading.Lock()

def now(): return datetime.now().astimezone().isoformat(timespec="seconds")
def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    DATA.mkdir(parents=True, exist_ok=True)
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS meetings(id TEXT PRIMARY KEY,title TEXT NOT NULL,meeting_date TEXT,location TEXT,host TEXT,participants TEXT,project TEXT,objective TEXT,status TEXT NOT NULL,created_at TEXT,updated_at TEXT,transcript TEXT DEFAULT '',draft_json TEXT DEFAULT '{}',final_json TEXT DEFAULT '{}');
        CREATE TABLE IF NOT EXISTS chunks(id INTEGER PRIMARY KEY AUTOINCREMENT,meeting_id TEXT NOT NULL,seq INTEGER NOT NULL,path TEXT NOT NULL,size INTEGER NOT NULL,created_at TEXT,UNIQUE(meeting_id,seq));
        CREATE TABLE IF NOT EXISTS versions(id INTEGER PRIMARY KEY AUTOINCREMENT,meeting_id TEXT NOT NULL,version INTEGER NOT NULL,status TEXT NOT NULL,content_json TEXT NOT NULL,created_at TEXT);
        """)

def rowdict(row): return dict(row) if row else None
def meeting(mid):
    with conn() as c: return rowdict(c.execute("SELECT * FROM meetings WHERE id=?",(mid,)).fetchone())

def json_response(h, data, code=200):
    raw=json.dumps(data,ensure_ascii=False).encode()
    h.send_response(code); h.send_header("Content-Type","application/json; charset=utf-8"); h.send_header("Content-Length",str(len(raw))); h.end_headers(); h.wfile.write(raw)

def multipart_post(url, fields, file_path, api_key):
    boundary="----HermesMeeting"+uuid.uuid4().hex
    parts=[]
    for k,v in fields.items(): parts += [f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()]
    p=Path(file_path); parts += [f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{p.name}\"\r\nContent-Type: audio/webm\r\n\r\n".encode(),p.read_bytes(),f"\r\n--{boundary}--\r\n".encode()]
    req=request.Request(url,data=b"".join(parts),headers={"Authorization":f"Bearer {api_key}","Content-Type":f"multipart/form-data; boundary={boundary}"})
    with request.urlopen(req,timeout=1800) as r: return json.loads(r.read())

def transcribe(audio):
    base=os.environ.get("HERMES_STT_BASE_URL","").rstrip("/"); key=os.environ.get("HERMES_STT_API_KEY","")
    if not base or not key: raise RuntimeError("未配置 HERMES_STT_BASE_URL/HERMES_STT_API_KEY")
    out=multipart_post(base+"/audio/transcriptions",{"model":os.environ.get("HERMES_STT_MODEL","whisper-1"),"response_format":"json","language":"zh"},audio,key)
    return out.get("text","")

def summarize(meta, transcript):
    base=os.environ.get("HERMES_LLM_BASE_URL","").rstrip("/"); key=os.environ.get("HERMES_LLM_API_KEY","")
    if not base or not key: raise RuntimeError("未配置 HERMES_LLM_BASE_URL/HERMES_LLM_API_KEY")
    schema=(ROOT/"references/minutes-schema.md").read_text(encoding="utf-8")
    prompt=f"""你是唐予衡，育才国际内部项目计划经理。请把会议转化成可以直接执行、检查和跟进的工作清单。

最高优先级是待办任务，并适配手机微信快速查看。每项待办只输出五个字段：业务类型、待办事项、负责人、具体要求、完成时间。将必要的交付结果和注意事项简洁合并到“具体要求”，不要增加协作人、部门、优先级、状态、依赖或原文依据等字段。不得用会议摘要代替任务清单，不得把被提及的人自动认定为负责人，不得把“尽快、后续、回头”等模糊表达虚构成具体日期。信息不明确时保留任务并标记待确认。

严格依据逐字稿，不得虚构客户、学生、项目、人员、金额、日期、决策或业务承诺。先执行提示词中的提取规则和输出前自检，再只返回合法 JSON。

会议元数据：
{json.dumps(meta,ensure_ascii=False)}

{schema}

会议逐字稿：
{transcript}"""
    body=json.dumps({"model":os.environ.get("HERMES_LLM_MODEL","deepseek-chat"),"temperature":0.1,"response_format":{"type":"json_object"},"messages":[{"role":"user","content":prompt}]},ensure_ascii=False).encode()
    req=request.Request(base+"/chat/completions",data=body,headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
    with request.urlopen(req,timeout=1800) as r: out=json.loads(r.read())
    text=out["choices"][0]["message"]["content"].strip().removeprefix("```json").removesuffix("```").strip()
    return json.loads(text)

def prepare_audio_segments(mid):
    folder=DATA/mid; raw=folder/"recording.raw.webm"; combined=folder/"recording.webm"; segment_dir=folder/"transcription_segments"
    with conn() as c: rows=c.execute("SELECT path FROM chunks WHERE meeting_id=? ORDER BY seq",(mid,)).fetchall()
    if not rows: raise RuntimeError("没有录音片段")
    # MediaRecorder timeslice chunks are consecutive bytes of one stream, not standalone media files.
    with raw.open("wb") as out:
        for r in rows:
            with Path(r[0]).open("rb") as src:
                while block:=src.read(1024*1024): out.write(block)
    cmd=["ffmpeg","-y","-i",str(raw),"-c:a","libopus","-b:a","48k",str(combined)]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=1800)
    if p.returncode: raise RuntimeError("音频合并失败，请确认已安装 ffmpeg："+p.stderr[-500:])
    segment_dir.mkdir(exist_ok=True)
    for old in segment_dir.glob("*.webm"): old.unlink()
    cmd=["ffmpeg","-y","-i",str(combined),"-f","segment","-segment_time","1200","-reset_timestamps","1","-c","copy",str(segment_dir/"part-%03d.webm")]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=1800)
    if p.returncode: raise RuntimeError("音频切段失败："+p.stderr[-500:])
    return sorted(segment_dir.glob("part-*.webm"))

class Handler(SimpleHTTPRequestHandler):
    def translate_path(self,path): return str(STATIC/("index.html" if path=="/" else path.lstrip("/")))
    def log_message(self,fmt,*args): print("[%s] %s"%(now(),fmt%args))
    def read_json(self): return json.loads(self.rfile.read(int(self.headers.get("Content-Length","0"))) or b"{}")
    def do_GET(self):
        if self.path=="/api/meetings":
            with conn() as c: rows=[dict(x) for x in c.execute("SELECT id,title,meeting_date,status,created_at,updated_at FROM meetings ORDER BY created_at DESC").fetchall()]
            return json_response(self,rows)
        if self.path.startswith("/api/meetings/"):
            mid=self.path.split("/")[3]; m=meeting(mid)
            if not m:return json_response(self,{"error":"会议不存在"},404)
            for k in ("draft_json","final_json"):
                try:m[k]=json.loads(m[k] or "{}")
                except:m[k]={}
            with conn() as c:m["chunk_count"]=c.execute("SELECT COUNT(*) FROM chunks WHERE meeting_id=?",(mid,)).fetchone()[0]
            return json_response(self,m)
        return super().do_GET()
    def do_POST(self):
        try:
            if self.path=="/api/meetings":
                b=self.read_json(); mid=datetime.now().strftime("MTG-%Y%m%d-")+uuid.uuid4().hex[:6].upper(); ts=now()
                vals=(mid,b.get("title") or "未命名会议",b.get("meeting_date",""),b.get("location",""),b.get("host",""),b.get("participants",""),b.get("project",""),b.get("objective",""),"recording",ts,ts)
                with conn() as c:c.execute("INSERT INTO meetings(id,title,meeting_date,location,host,participants,project,objective,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",vals)
                (DATA/mid/"chunks").mkdir(parents=True,exist_ok=True); return json_response(self,{"id":mid},201)
            parts=self.path.split("/"); mid=parts[3]; action=parts[4] if len(parts)>4 else ""
            if not meeting(mid):return json_response(self,{"error":"会议不存在"},404)
            if action=="chunks":
                seq=int(self.headers.get("X-Chunk-Seq","-1")); size=int(self.headers.get("Content-Length","0")); max_size=25*1024*1024
                if seq<0 or size<=0 or size>max_size:return json_response(self,{"error":"片段参数无效"},400)
                path=DATA/mid/"chunks"/f"{seq:07d}.webm"; raw=self.rfile.read(size); path.write_bytes(raw)
                with conn() as c:c.execute("INSERT OR REPLACE INTO chunks(meeting_id,seq,path,size,created_at) VALUES(?,?,?,?,?)",(mid,seq,str(path),len(raw),now()))
                return json_response(self,{"ok":True,"seq":seq})
            if action in ("pause","resume","stop"):
                status={"pause":"paused","resume":"recording","stop":"processing"}[action]
                with conn() as c:c.execute("UPDATE meetings SET status=?,updated_at=? WHERE id=?",(status,now(),mid))
                return json_response(self,{"status":status})
            if action=="process":
                audios=prepare_audio_segments(mid)
                texts=[]
                for i,audio in enumerate(audios,1): texts.append(f"[录音第{i}段]\n"+transcribe(audio))
                text="\n\n".join(texts); m=meeting(mid); draft=summarize({k:m[k] for k in ("title","meeting_date","location","host","participants","project","objective")},text)
                with conn() as c:c.execute("UPDATE meetings SET transcript=?,draft_json=?,status='draft',updated_at=? WHERE id=?",(text,json.dumps(draft,ensure_ascii=False),now(),mid))
                return json_response(self,{"transcript":text,"draft":draft})
            if action=="confirm":
                b=self.read_json(); content=b.get("minutes") or {}; transcript=b.get("transcript")
                with conn() as c:
                    v=c.execute("SELECT COALESCE(MAX(version),0)+1 FROM versions WHERE meeting_id=?",(mid,)).fetchone()[0]
                    c.execute("INSERT INTO versions(meeting_id,version,status,content_json,created_at) VALUES(?,?,?,?,?)",(mid,v,"confirmed",json.dumps(content,ensure_ascii=False),now()))
                    c.execute("UPDATE meetings SET transcript=COALESCE(?,transcript),final_json=?,status='confirmed',updated_at=? WHERE id=?",(transcript,json.dumps(content,ensure_ascii=False),now(),mid))
                return json_response(self,{"status":"confirmed","version":v})
            return json_response(self,{"error":"未知操作"},404)
        except Exception as e: return json_response(self,{"error":str(e)},500)

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--host",default="127.0.0.1"); ap.add_argument("--port",type=int,default=8765); a=ap.parse_args(); init_db(); print(f"Meeting recorder: http://{a.host}:{a.port}"); ThreadingHTTPServer((a.host,a.port),Handler).serve_forever()
