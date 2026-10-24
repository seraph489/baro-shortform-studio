"""편집 화면 서버 (로컬 전용, 127.0.0.1).

    PY=../tools/.venv-rembg/bin/python
    $PY -I .claude/skills/baro-shortform/scripts/editor_server.py work/<작업> [포트=8765]

브라우저에서 http://127.0.0.1:8765 를 연다.
- 미리보기 영상(컷·배속만 적용, 그래픽 없음)이 없으면 먼저 만든다 (preview.mp4).
- GET  /                편집 화면
- GET  /plan.json       현재 계획
- PUT  /plan.json       저장 (이전 계획은 plan_history/에 시각별로 보관)
- POST /render          pipeline.py render 실행 (출력 이름은 요청 본문 {"name": "..."})
- GET  /render/status   렌더 진행 로그
"""
import json
import shutil
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
STUDIO = SKILL.parent.parent.parent
PY = STUDIO.parent / "tools" / ".venv-rembg" / "bin" / "python"
SFX_DIR = STUDIO / "assets" / "sfx" / "ready"

work = Path(sys.argv[1]).resolve()
port = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
state = {"running": False, "log": "", "result": None}


def ensure_preview():
    """EDL대로 원본 영상을 자르고 배속을 적용한 가벼운 미리보기 (540x960)."""
    out = work / "preview.mp4"
    edl = json.loads((work / "edl.json").read_text())
    if out.exists() and out.stat().st_mtime > (work / "edl.json").stat().st_mtime:
        return
    info = json.loads((work / "analysis.json").read_text())
    segs, sp = edl["segments"], edl["speed"]
    n = len(segs)
    fc = f"[0:v]split={n}" + "".join(f"[v{i}]" for i in range(n)) + ";"
    for i, (a, b) in enumerate(segs):
        fc += f"[v{i}]trim={a}:{b},setpts=PTS-STARTPTS[t{i}];"
    fc += "".join(f"[t{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0,setpts=PTS/{sp},fps=30,scale=540:960[v]"
    print("미리보기 영상 만드는 중…", flush=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", info["input"], "-i", str(work / "audio_cut.wav"),
                    "-filter_complex", fc, "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-crf", "26", "-preset", "veryfast",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(out)], check=True)


def run_render(name):
    state.update(running=True, log="", result=None)
    p = subprocess.Popen([str(PY), "-I", str(HERE / "pipeline.py"), "render", str(work), name], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in p.stdout:
        state["log"] += line
    p.wait()
    state.update(running=False, result=("ok" if p.returncode == 0 else "fail"))


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def file(self, path, ctype):
        path = Path(path)
        size = path.stat().st_size
        rng = self.headers.get("Range")
        if rng and rng.startswith("bytes="):   # 영상 탐색(seek)용 부분 전송
            a, _, b = rng[6:].partition("-")
            a = int(a); b = int(b) if b else size - 1
            with open(path, "rb") as f:
                f.seek(a); data = f.read(b - a + 1)
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {a}-{b}/{size}")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self.send(200, path.read_bytes(), ctype)

    def do_GET(self):
        u = self.path.split("?")[0]
        if u == "/":
            return self.file(HERE / "editor.html", "text/html; charset=utf-8")
        if u == "/plan.json":
            return self.file(work / "plan.json", "application/json; charset=utf-8")
        if u == "/meta.json":
            edl = json.loads((work / "edl.json").read_text())
            words = json.loads((work / "words_cut.json").read_text()) if (work / "words_cut.json").exists() else []
            tpl = json.loads((work / "plan.json").read_text()).get("style", "01")
            return self.send(200, json.dumps({"work": work.name, "duration": edl["duration_out"], "words": words, "style": tpl,
                                              "sfx": sorted(p.name for p in SFX_DIR.glob("[0-9]*.wav"))}, ensure_ascii=False))
        if u == "/preview.mp4":
            return self.file(work / "preview.mp4", "video/mp4")
        if u.startswith("/template/"):   # 2026-10-22 정리: 템플릿은 baro_overlay.html 하나
            html = (HERE / "templates" / "baro_overlay.html").read_text().replace("__FONT_URL__", "/font.woff2").replace("__HAND_FONT_URL__", "/handfont.ttf")
            return self.send(200, html, "text/html; charset=utf-8")
        if u == "/font.woff2":
            return self.file(SKILL / "assets" / "fonts" / "PretendardVariable.woff2", "font/woff2")
        if u == "/handfont.ttf":
            return self.file(SKILL / "assets" / "fonts" / "NanumPenScript-Regular.ttf", "font/ttf")
        if u.startswith("/sfx/"):
            return self.file(SFX_DIR / Path(u).name, "audio/wav")
        if u == "/render/status":
            return self.send(200, json.dumps(state, ensure_ascii=False))
        if u == "/output":
            return self.send(200, json.dumps({"path": (state.get("out") or "")}, ensure_ascii=False))
        if u.startswith("/out/"):
            p = (STUDIO / "output" / u[5:]).resolve()
            if STUDIO / "output" in p.parents and p.exists():
                return self.file(p, "video/mp4")
        self.send(404, "{}")

    def do_PUT(self):
        if self.path != "/plan.json":
            return self.send(404, "{}")
        body = self.rfile.read(int(self.headers["Content-Length"]))
        plan = json.loads(body)
        hist = work / "plan_history"
        hist.mkdir(exist_ok=True)
        if (work / "plan.json").exists():
            shutil.copy(work / "plan.json", hist / f"plan_{time.strftime('%Y%m%d-%H%M%S')}.json")
        (work / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1))
        self.send(200, '{"saved": true}')

    def do_POST(self):
        if self.path != "/render":
            return self.send(404, "{}")
        if state["running"]:
            return self.send(409, '{"error": "이미 렌더 중"}')
        name = json.loads(self.rfile.read(int(self.headers["Content-Length"]) or 2) or b"{}").get("name")
        if not name or ".." in name:
            return self.send(400, '{"error": "name"}')
        state["out"] = f"{name}_hq.mp4"
        threading.Thread(target=run_render, args=(name,), daemon=True).start()
        self.send(202, '{"started": true}')


ensure_preview()
print(f"편집 화면: http://127.0.0.1:{port}  (작업 {work.name}, 종료 Ctrl+C)", flush=True)
ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
