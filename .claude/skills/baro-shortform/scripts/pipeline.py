"""안양연세바로치과 숏폼 편집 파이프라인 (01 바로 모션 기준, 02~05가 공유하는 공통 단계 포함).

실행은 rembg 가상환경 파이썬으로 한다 (numpy, Pillow 필요):
    PY=../tools/.venv-rembg/bin/python   # shortform-studio 기준
    $PY -I .claude/skills/baro-shortform/scripts/pipeline.py <명령> ...

명령
  analyze <입력.mp4> <작업폴더>      규격·채널·무음·받아쓰기(원본)  → analysis.json
  cut <작업폴더> [--keep 17.1,18.8] [--drop 3.2-7.9]   컷편집 EDL (--drop: NG 테이크 원본 구간 빼기) + 잡음 제거 + 컷 페이드 + 1.1배속 + −14 LUFS
                                      + 컷 결과 재받아쓰기/원본 비교 + 음성 에너지 구간 → words_cut.json, envelope.json
  frames <작업폴더>                   원본 프레임 30fps 1350x2400 JPEG 추출
  render <작업폴더> <출력이름>        plan.json 으로 그래픽 → 합성 → 효과음 → 인코딩 → 검사 (아래 4단계를 한 번에)
  overlay | compose | sfx <작업폴더>  render 의 개별 단계
  masks <작업폴더>                    03 바로 레이어: 핵심어 구간 사람 마스크(rembg) + 마스크 시험 → render 전에 실행
  encode <작업폴더> <출력이름>        output/<출력이름>_hq.mp4 / _phone.mp4 + 검사 + 장면 시트
  check <파일.mp4>                    Reels 규격 검사만

plan.json 형식은 references/plan-schema.md. 모든 시각은 **컷·배속 이후 출력 시각(초)** 이다.
"""
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
STUDIO = SKILL.parent.parent.parent                      # shortform-studio
TOOLS = STUDIO.parent / "tools"
WHISPER = TOOLS / "vendor" / "whisper.cpp"
WHISPER_BIN = WHISPER / "build" / "bin" / "whisper-cli"
WHISPER_MODEL = WHISPER / "models" / "ggml-large-v3-turbo.bin"
PW_MODULE = STUDIO.parent / "node_modules" / "@playwright" / "test" / "index.mjs"
SFX_DIR = STUDIO / "assets" / "sfx" / "ready"
OUTPUT = STUDIO / "output"
W, H, FPS = 1080, 1920, 30
SRC_W, SRC_H = 1350, 2400                                # 확대 구간 화질용 1.25배 원본 프레임

# Reels 규격 (YSA ffmpeg-skill _platforms.py reels 사양)
SPEC = {"lufs": -14.0, "lufs_tol": 2.0, "tp": -1.0, "fps": 30, "max_dur": 90, "safe_top": 0.08, "safe_bottom": 0.20}
# 01 바로 모션 기본 효과음 배치 (2026-10-22 원장님 확정)
SFX_DEFAULT = {"title": ("07_제목등장_통.wav", -11), "keyword": ("16_충격_붐.wav", -10), "panel": ("10_패널단계_선택.wav", -6)}
SFX_LEAD = 0.035                                          # 그래픽보다 35ms 먼저 (YSA motion-polish)


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        sys.exit(f"명령 실패: {' '.join(map(str, cmd[:6]))} ...\n{r.stderr[-2000:]}")
    return r


def ff(*args):
    return run(["ffmpeg", "-hide_banner", "-nostats", "-y", *map(str, args)])


def ffprobe_json(path):
    return json.loads(run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)]).stdout)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load(work):
    return json.loads((work / "analysis.json").read_text())


def save(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1))


def ebur128(path):
    err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    p = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", err)
    return float(i[-1]), float(p[-1])


def whisper_words(wav, out_base):
    run([str(WHISPER_BIN), "-m", str(WHISPER_MODEL), "-f", str(wav), "-l", "ko", "-ml", "1", "-sow", "-ojf", "-of", str(out_base)])
    d = json.loads(Path(str(out_base) + ".json").read_text())
    words = []
    for s in d["transcription"]:
        t = s["text"].strip()
        if not t:
            continue
        probs = [k["p"] for k in s.get("tokens", []) if not k["text"].startswith("[")]
        words.append({"start": s["offsets"]["from"] / 1000, "end": s["offsets"]["to"] / 1000, "text": t, "p": round(min(probs) if probs else 1.0, 2)})
    return words


def silences(path, noise="-38dB", dur=0.18):
    err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", f"silencedetect=n={noise}:d={dur}", "-f", "null", "-"]).stderr
    st = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", err)]
    en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    out = []
    for a, b in zip(st, en):   # 1ms 남짓한 틈으로 쪼개진 무음은 하나로 합친다
        if out and a - out[-1][1] < 0.05:
            out[-1][1] = round(b, 3)
        else:
            out.append([round(a, 3), round(b, 3)])
    return out


# ───────────────────────── analyze ─────────────────────────
def cmd_analyze(inp, work):
    inp, work = Path(inp).resolve(), Path(work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    pr = ffprobe_json(inp)
    v = next(s for s in pr["streams"] if s["codec_type"] == "video")
    a = next((s for s in pr["streams"] if s["codec_type"] == "audio"), None)
    num, den = map(int, v["r_frame_rate"].split("/"))
    dur = float(pr["format"]["duration"])
    chans = []
    if a and int(a.get("channels", 1)) >= 2:
        for ch in ("FL", "FR"):
            err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(inp), "-af", f"pan=mono|c0={ch},volumedetect", "-f", "null", "-"]).stderr
            chans.append(float(re.findall(r"mean_volume: (-?[\d.]+)", err)[-1]))
    sil = silences(inp)
    # 말이 있는 구간 = 무음이 아닌 구간
    # 말 구간 = 무음 사이 소리. 0.25초 미만 소리(잡음·숨소리)는 첫 말·끝 말로 치지 않는다
    bounds = [0.0] + [x for ab in sil for x in ab] + [dur]
    bursts = [(a, b) for a, b in zip(bounds[0::2], bounds[1::2]) if b - a >= 0.25]
    speech_start = bursts[0][0] if bursts else 0.0
    speech_end = bursts[-1][1] if bursts else dur
    ff("-i", inp, "-vn", "-ac", "1", "-ar", "16000", work / "src16k.wav")
    words = whisper_words(work / "src16k.wav", work / "words_src")
    info = {
        "input": str(inp), "input_sha256": sha256(inp), "duration": round(dur, 3),
        "width": v["width"], "height": v["height"], "fps": round(num / den, 3), "vcodec": v["codec_name"],
        "audio": bool(a), "channels": int(a.get("channels", 0)) if a else 0, "channel_mean_db": chans,
        "silences": sil, "speech_start": speech_start, "speech_end": speech_end, "words_src": words,
    }
    info["retakes"] = find_retakes(words, sil)
    save(work / "analysis.json", info)
    low = [w for w in words if w["p"] < 0.6]
    print(f"{inp.name}: {dur:.2f}s {v['width']}x{v['height']} {num/den:.2f}fps 오디오 {info['channels']}ch {chans}")
    print(f"말 시작 {speech_start:.2f}s / 끝 {speech_end:.2f}s, 무음 {len(sil)}구간")
    print("받아쓰기:", " ".join(w["text"] for w in words))
    print("확인 필요(신뢰도<0.6):", ", ".join(f"{w['text']}@{w['start']:.1f}s({w['p']})" for w in low) or "없음")
    if info["retakes"]:
        print("다시 말한 문장(NG 후보) — 마지막 테이크만 남기려면 cut --drop 으로 앞 테이크를 빼요:")
        for r in info["retakes"]:
            print(f"  NG {r['ng'][0]:.2f}-{r['ng'][1]:.2f}s 「{r['ng_text']}」 → 다시 말함 {r['keep'][0]:.2f}s 「{r['keep_text']}」 (유사도 {r['sim']})")
    else:
        print("다시 말한 문장(NG 후보): 없음")


def find_retakes(words, sil, min_pause=0.45, sim_min=0.6):
    """무음(min_pause 이상)으로 문장을 나눈 뒤, 이어지는 문장의 앞부분이 비슷하면 앞 문장을 NG로 본다.
    원장님 혼자 찍을 때 말이 꼬여 처음부터 다시 말하는 경우를 잡는다. 확정은 사람이 한다."""
    import difflib
    breaks = [a for a, b in sil if b - a >= min_pause]
    sents, cur = [], []
    for w in words:
        if cur and any(cur[-1]["end"] - 0.05 <= x <= w["start"] + 0.05 for x in breaks):
            sents.append(cur); cur = []
        cur.append(w)
    if cur:
        sents.append(cur)
    norm = lambda ws: "".join(x["text"] for x in ws).replace(" ", "").strip("?,.!")
    out = []
    for i in range(len(sents) - 1):
        a, b = norm(sents[i]), norm(sents[i + 1])
        n = min(len(a), len(b), 12)
        if n < 4:
            continue
        sim = difflib.SequenceMatcher(None, a[:n], b[:n]).ratio()
        if sim >= sim_min:
            out.append({"ng": [round(sents[i][0]["start"], 2), round(sents[i][-1]["end"], 2)], "ng_text": " ".join(x["text"] for x in sents[i]),
                        "keep": [round(sents[i + 1][0]["start"], 2), round(sents[i + 1][-1]["end"], 2)], "keep_text": " ".join(x["text"] for x in sents[i + 1]), "sim": round(sim, 2)})
    return out


# ───────────────────────── cut ─────────────────────────
def subtract(segs, drops):
    out = []
    for a, b in segs:
        parts = [[a, b]]
        for d0, d1 in drops:
            nxt = []
            for x, y in parts:
                if d1 <= x or d0 >= y:
                    nxt.append([x, y])
                else:
                    if d0 > x: nxt.append([x, d0])
                    if d1 < y: nxt.append([d1, y])
            parts = nxt
        out += [[round(x, 3), round(y, 3)] for x, y in parts if y - x > 0.05]
    return out


def make_edl(info, lead, tail, min_gap, pad_before, pad_after, keep=()):
    s0, s1 = info["speech_start"], info["speech_end"]
    inner = [(a, b) for a, b in info["silences"] if a > s0 + 0.05 and b < s1 - 0.05 and b - a > min_gap
             and not any(a <= k <= b for k in keep)]   # keep: 작게 말한 단어가 무음으로 잡힌 구간은 자르지 않음
    segs, cur = [], max(0.0, s0 - lead)
    for a, b in inner:
        segs.append([round(cur, 3), round(a + pad_before, 3)])
        cur = b - pad_after
    segs.append([round(cur, 3), round(min(info["duration"], s1 + tail), 3)])
    return segs


def to_src_fn(edl):
    segs, speed = edl["segments"], edl["speed"]

    def f(t_out):
        t = t_out * speed
        for a, b in segs:
            if t < b - a:
                return a + t
            t -= b - a
        return segs[-1][1]
    return f


def to_out_fn(edl):
    segs, speed = edl["segments"], edl["speed"]

    def f(ts):
        acc = 0.0
        for a, b in segs:
            if ts < a:
                return acc / speed
            if ts < b:
                return (acc + ts - a) / speed
            acc += b - a
        return acc / speed
    return f


def envelope(wav16):
    import numpy as np
    import wave
    w = wave.open(str(wav16))
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float)
    sr = w.getframerate()
    hop = int(sr * 0.02)
    e = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2) + 1e-9) for i in range(0, len(x) - hop, hop)])
    db = 20 * np.log10(e / 32768)
    thr = np.percentile(db, 20) + 10
    runs, s = [], None
    for i, on in enumerate(db > thr):
        if on and s is None:
            s = i
        if not on and s is not None:
            if i - s >= 3:
                runs.append([s * 0.02, i * 0.02])
            s = None
    merged = []
    for a, b in runs:
        if merged and a - merged[-1][1] < 0.12:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    return [[round(a, 2), round(b, 2)] for a, b in merged]


def cmd_cut(work, speed=1.1, lead=1.2, tail=0.35, min_gap=0.25, pad_before=0.10, pad_after=0.08, no_cut=False, keep=(), drop=()):
    work = Path(work).resolve()
    info = load(work)
    segs = [[0.0, info["duration"]]] if no_cut else make_edl(info, lead, tail, min_gap, pad_before, pad_after, keep)
    if drop:   # NG 테이크 빼기 (원본 시각 구간)
        segs = subtract(segs, drop)
    edl = {"segments": segs, "speed": 1.0 if no_cut else speed, "keep": list(keep), "drop": [list(d) for d in drop]}
    save(work / "edl.json", edl)
    # 한쪽 채널만 녹음된 원본은 양쪽으로 복사 (KMH §2)
    pre = ""
    cm = info["channel_mean_db"]
    if len(cm) == 2 and abs(cm[0] - cm[1]) > 20:
        ch = "FL" if cm[0] > cm[1] else "FR"
        pre = f"pan=stereo|c0={ch}|c1={ch},"
    # 잡음 학습: 첫 말 앞 무음 구간 (0.4초 이상일 때)
    a, b = 0.1, info["speech_start"] - 0.15
    den = (f"asendcmd=c='{a:.2f} afftdn@n sn start; {b:.2f} afftdn@n sn stop',afftdn@n=nr=14:nf=-55:tn=1"
           if b - a >= 0.4 else "afftdn=nr=10:nf=-55")
    n = len(segs)
    fc = f"[0:a]{pre}{den}[den];[den]asplit={n}" + "".join(f"[d{i}]" for i in range(n)) + ";"
    for i, (s, e) in enumerate(segs):
        L = e - s
        fc += f"[d{i}]atrim={s}:{e},asetpts=PTS-STARTPTS,afade=t=in:d=0.01,afade=t=out:st={max(0, L - 0.01):.3f}:d=0.01[s{i}];"
    fc += "".join(f"[s{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1" + (f",atempo={edl['speed']}" if edl["speed"] != 1 else "") + "[cut]"
    (work / "audio_filter.txt").write_text(fc)
    ff("-i", info["input"], "-/filter_complex", work / "audio_filter.txt", "-map", "[cut]", "-ar", 48000, "-ac", 2, work / "audio_cut_pre.wav")
    err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(work / "audio_cut_pre.wav"), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"]).stderr
    m = json.loads(err[err.rindex("{"):err.rindex("}") + 1])
    ln = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    ff("-i", work / "audio_cut_pre.wav", "-af", ln, "-ar", 48000, work / "audio_cut.wav")
    ff("-i", work / "audio_cut.wav", "-ac", 1, "-ar", 16000, work / "cut16k.wav")
    words = whisper_words(work / "cut16k.wav", work / "words_cut_raw")
    env = envelope(work / "cut16k.wav")
    save(work / "words_cut.json", words)
    save(work / "envelope.json", env)
    # 검수: 원본과 단어 비교 (KMH §1)
    import difflib
    diff = [x for x in difflib.ndiff([w["text"].strip("?,.") for w in info["words_src"]], [w["text"].strip("?,.") for w in words]) if x[0] in "+-"]
    dur = float(ffprobe_json(work / "audio_cut.wav")["format"]["duration"])
    lufs, peak = ebur128(work / "audio_cut.wav")
    edl.update({"duration_out": round(dur, 3), "lufs": lufs, "peak": peak, "word_diff": diff})
    save(work / "edl.json", edl)
    print(f"컷 {len(segs)}구간, {info['duration']:.2f}s → {dur:.2f}s (×{edl['speed']}), {lufs} LUFS, peak {peak} dBFS")
    print("원본 대비 단어 차이:", diff or "없음", "(빠진 단어가 있으면 그 단어의 원본 시각을 --keep 으로 줘서 그 무음만 자르지 않게 다시 실행)")
    print("음성 구간(출력 시각):", " ".join(f"{a}-{b}" for a, b in env))
    print("컷 받아쓰기(출력 시각):")
    print(" ".join(f"[{w['start']:.2f}]{w['text']}" + (f"({w['p']})" if w["p"] < 0.6 else "") for w in words))


# ───────────────────────── frames ─────────────────────────
def cmd_frames(work):
    work = Path(work).resolve()
    info = load(work)
    out = work / "frames_src"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir()
    vf = f"fps={FPS},scale={SRC_W}:{SRC_H}:force_original_aspect_ratio=increase:flags=lanczos,crop={SRC_W}:{SRC_H}"
    ff("-i", info["input"], "-vf", vf, "-q:v", 2, out / "s%05d.jpg")
    print("원본 프레임", len(list(out.glob("*.jpg"))))


# ───────────────────────── render steps ─────────────────────────
LEGACY_STYLE = {"06": "02", "07": "01", "03": "01"}   # 2026-10-22 정리: 06 한마디→02 바로 자막, 07 손글씨·03 레이어→01의 핵심어 디자인
FOLLOW_DEFAULT = {"text": "안양연세바로치과", "sub": "교정 궁금증, 매주 답해 드려요"}


def plan_of(work):
    """plan.json을 읽고 정리된 구조(스타일 01·02·03 + 옵션)로 맞춘다."""
    p = json.loads((work / "plan.json").read_text())
    p.setdefault("fps", FPS)
    p["style"] = LEGACY_STYLE.get(str(p.get("style", "01")), str(p.get("style", "01")))
    k = p.get("keyword")
    if k:
        design = k.get("design") or ("behind" if k.get("layer") == "behind" else "pop")
        k["design"] = design
        k["layer"] = "behind" if design == "behind" else "front"
    # 옵션: 팔로우 카드 (기본 켬, plan.follow = false 로 끔)
    if p.get("follow") is False:
        p.pop("follow")
    elif (work / "edl.json").exists():
        f = {**FOLLOW_DEFAULT, **(p.get("follow") or {})}
        if "start" not in f:
            edl = json.loads((work / "edl.json").read_text())
            D = dur_out(p, edl)
            f["start"] = round(min(max(D - 2.5, (p.get("cta") or {}).get("start", 0) + 0.9), D - 1.2), 2)
        p["follow"] = f
    return p


def dur_out(plan, edl):
    """출력 길이. plan.end(끝 지점, 출력 시각)로 촬영 종료 동작 등을 잘라 낼 수 있다."""
    end = plan.get("end")
    return round(min(edl["duration_out"], end) if end else edl["duration_out"], 3)


def cmd_overlay(work):
    work = Path(work).resolve()
    plan, edl = plan_of(work), json.loads((work / "edl.json").read_text())
    if plan["style"] == "03":
        sys.exit("03 바로 데일리는 아직 설계만 있어요 (references/03_바로데일리.md)")
    tpl = SKILL / "scripts" / "templates" / "baro_overlay.html"
    # 옵션: 핵심어 디자인 "hand" → 손글씨로 써지게 (머리 위 가운데)
    k = plan.get("keyword")
    if k and k["design"] == "hand":
        plan.setdefault("hand", []).insert(0, {"text": k["text"] + (k.get("mark") if k.get("mark") is not None else "?"), "start": k["start"], "end": k["end"] + 0.6,
                                               "x": 540, "y": k.get("top", 230) + 100, "size": k.get("size", 230), "color": k.get("color", "white"), "rotate": -4, "per": 0.16})
        plan.pop("keyword")
    # 자막 테두리: "auto"(기본)면 자막 자리 배경이 복잡할 때만 켠다
    if plan.get("outline", "auto") == "auto":
        b = background_busyness(work)
        plan["outline"] = b >= BUSY_OUTLINE
        print(f"자막 자리 배경 복잡도 {b:.1f} (기준 {BUSY_OUTLINE}) → 테두리 {'켬' if plan['outline'] else '끔'}")
    if plan.get("word_captions"):   # 06: 받아쓰기로 한두 단어 자막 자동 생성
        plan["subs"] = plan.get("subs", []) + word_captions(work, plan)
        print(f"한두 단어 자막 {len([s for s in plan['subs'] if s.get('word')])}개 자동 생성")
    for x in plan.get("insets", []) + plan.get("photos", []):   # 사진 인셋·사진 카드 경로 → 파일 URL
        src = Path(x["src"]) if Path(x["src"]).is_absolute() else (work / x["src"])
        if not src.exists():
            sys.exit(f"사진 없음: {src}")
        x["src"] = src.resolve().as_uri()
    render_plan = work / "_plan_render.json"
    save(render_plan, plan)
    behind = (plan.get("keyword") or {}).get("layer") == "behind"
    layers = [("main", "overlay"), ("kw", "overlay_kw")] if behind else [("all", "overlay")]
    for layer, folder in layers:
        env = {"PW_MODULE": str(PW_MODULE), "PATH": __import__("os").environ["PATH"], "LAYER": layer}
        r = run(["node", str(SKILL / "scripts" / "render_overlay.mjs"), str(tpl), str(render_plan), str(work / folder), str(dur_out(plan, edl))], env=env)
        info = json.loads(r.stdout.strip().splitlines()[-1])
        ov = info.pop("overlaps", {})
        print(f"그래픽({layer})", json.dumps(info, ensure_ascii=False))
        save(work / f"overlaps_{layer}.json", ov)
        if ov:
            print("  ⚠️ 글자 요소 겹침 (자동 조정 후에도 남음):", "; ".join(f"{k} {v['frames']}프레임({v['first']:.2f}초~)" for k, v in ov.items()))
        else:
            print("  글자 요소 겹침: 없음")


BUSY_OUTLINE = 4.0   # 자막 자리 평균 밝기 변화량. 스크럽·단색 벽 1~3, 진열장·책장이 비치면 4 이상


def fixed_words(work, plan):
    """컷 받아쓰기 + plan.word_fix(오인식 고치기, 예: {"암호와": "안모와"})"""
    fix = plan.get("word_fix", {})
    return [dict(w, text=fix.get(w["text"], w["text"])) for w in json.loads((work / "words_cut.json").read_text())]


def word_captions(work, plan):
    """컷 받아쓰기로 한두 단어씩 자막을 만든다 (한 자막 공백 빼고 8자 이하, 최대 2단어).
    plan.word_captions: {"highlight": ["나이", ...], "skip": [...], "from": 초, "to": 초} — highlight 단어는 코랄"""
    opt = plan["word_captions"] if isinstance(plan["word_captions"], dict) else {}
    edl = json.loads((work / "edl.json").read_text())
    D = dur_out(plan, edl)
    t0, t1 = opt.get("from", 0.0), opt.get("to", D)
    skip = set(opt.get("skip", [])) | set(plan.get("srt_skip", []))
    hl = opt.get("highlight", [])
    env = json.loads((work / "envelope.json").read_text()) if (work / "envelope.json").exists() else []
    # 받아쓰기 첫 단어 시각은 일찍 잡히기 쉬워서 끝 시각으로 거르고, 시작은 실제 첫 소리·from 이후로 당긴다
    first = max(t0, env[0][0] if env else 0.0)
    words = []
    for w in fixed_words(work, plan):
        if w["end"] <= t0 or w["start"] >= t1 or w["text"] in skip:
            continue
        words.append(dict(w, start=max(w["start"], first)))
    groups, cur = [], []
    for w in words:
        n = len("".join(x["text"] for x in cur + [w]).replace(" ", ""))
        if cur and (len(cur) >= 2 or n > 8 or w["start"] - cur[-1]["end"] > 0.4):
            groups.append(cur); cur = []
        cur.append(w)
        if w["text"].endswith((".", "?", "!", ",")):
            groups.append(cur); cur = []
    if cur:
        groups.append(cur)
    # 0.3초도 안 보이고 넘어가는 자막은 다음 자막과 합친다 (나가는 글자와 들어오는 글자 겹침 방지)
    merged = []
    for g in groups:
        if merged and g[0]["start"] - merged[-1][0]["start"] < 0.3 and len("".join(x["text"] for x in merged[-1] + g)) <= 10:
            merged[-1] = merged[-1] + g
        else:
            merged.append(g)
    groups = merged
    subs = []
    for i, g in enumerate(groups):
        a = g[0]["start"]
        b = groups[i + 1][0]["start"] if i + 1 < len(groups) else min(t1, g[-1]["end"] + 0.4)
        text = " ".join(x["text"].strip(".,") for x in g)
        for h in hl:
            text = text.replace(h, f"**{h}**")
        subs.append({"start": round(a, 2), "end": round(max(b, a + 0.2), 2), "text": text, "word": True})
    return subs


def background_busyness(work):
    """자막·제목 자리(x 200~880, y 1100~1450) 배경의 평균 기울기. 원본 프레임 1초 간격으로 잰다."""
    import numpy as np
    from PIL import Image
    vals = []
    for f in sorted((work / "frames_src").glob("s*.jpg"))[::30]:
        a = np.asarray(Image.open(f).convert("L").resize((W, H)).crop((200, 1100, 880, 1450)), dtype=float)
        vals.append(float((np.abs(np.diff(a, axis=0))[:, :-1] + np.abs(np.diff(a, axis=1))[:-1, :]).mean()))
    return sum(vals) / max(1, len(vals))


def behind_src_frames(work):
    """사람 뒤 핵심어가 보이는 출력 구간에 해당하는 원본 프레임 번호들."""
    plan, edl = plan_of(work), json.loads((work / "edl.json").read_text())
    K = plan.get("keyword") or {}
    if K.get("layer") != "behind":
        return []
    to_src = to_src_fn(edl)
    n_src = len(list((work / "frames_src").glob("s*.jpg")))
    return sorted({min(n_src - 1, round(to_src(i / FPS) * FPS)) for i in range(int(K["start"] * FPS), int(math.ceil(K["end"] * FPS)) + 1)})


def cmd_masks(work):
    """03 바로 레이어: 핵심어 구간 원본 프레임만 rembg(birefnet-portrait)로 사람 마스크를 만든다. CPU 프레임당 약 40초."""
    work = Path(work).resolve()
    idxs = behind_src_frames(work)
    if not idxs:
        sys.exit("plan.json의 keyword.layer가 \"behind\"가 아니라 마스크가 필요 없어요")
    stage, masks = work / "mask_src", work / "masks"
    masks.mkdir(exist_ok=True)
    shutil.rmtree(stage, ignore_errors=True)
    stage.mkdir()
    todo = 0
    for i in idxs:
        name = f"s{i + 1:05d}"
        if not (masks / f"{name}.png").exists():
            shutil.copy(work / "frames_src" / f"{name}.jpg", stage / f"{name}.jpg")
            todo += 1
    print(f"마스크 {len(idxs)}프레임 중 새로 만들 것 {todo}개 (예상 {todo * 40 // 60}분)")
    if todo:
        run([str(TOOLS / ".venv-rembg" / "bin" / "rembg"), "p", "-m", "birefnet-portrait", "-om", str(stage), str(masks)])
    shutil.rmtree(stage)
    # 마스크 시험: 머리 영역 프레임 간 변화 (평균 3/255 이하면 통과)
    import numpy as np
    from PIL import Image
    arr = [np.asarray(Image.open(masks / f"s{i + 1:05d}.png").convert("L").resize((W, H)))[200:900, 150:930].astype(float) for i in idxs]
    diffs = [float(np.mean(np.abs(a - b))) for a, b in zip(arr, arr[1:])]
    res = {"frames": len(idxs), "hair_diff_mean": round(sum(diffs) / max(1, len(diffs)), 2), "hair_diff_max": round(max(diffs or [0]), 2)}
    res["pass"] = res["hair_diff_mean"] <= 3.0
    save(work / "mask_test.json", res)
    print("마스크 시험:", res, "→ 실패하면 keyword.layer를 \"front\"로 바꿔 01 방식으로")


def zoom_at(plan, t):
    z = 1.0
    for e in plan.get("zoom", []):
        if e["start"] <= t < e["end"]:
            ramp = e.get("ramp", 0.1)
            x = 1.0 if ramp <= 0 else min(1.0, (t - e["start"]) / ramp)
            z0 = e.get("from", 1.0)
            z = z0 + (e["scale"] - z0) * (1 - (1 - x) ** 3)
    return z


def cmd_compose(work):
    from PIL import Image
    work = Path(work).resolve()
    plan, edl = plan_of(work), json.loads((work / "edl.json").read_text())
    to_src = to_src_fn(edl)
    src = sorted((work / "frames_src").glob("s*.jpg"))
    out = work / "composite"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir()
    if (plan.get("keyword") or {}).get("layer") != "behind":
        shutil.rmtree(work / "overlay_kw", ignore_errors=True)
    ax, ay = plan.get("anchor", [540, 800])
    n = round(dur_out(plan, edl) * FPS)
    for i in range(n):
        t = i / FPS
        idx = min(len(src) - 1, round(to_src(t) * FPS))
        s = zoom_at(plan, t)
        cw, ch = W / s, H / s
        x0 = min(max(ax - ax / s, 0), W - cw)
        y0 = min(max(ay - ay / s, 0), H - ch)
        k = SRC_W / W
        box = tuple(round(v * k) for v in (x0, y0, x0 + cw, y0 + ch))
        img = Image.open(src[idx]).crop(box).resize((W, H), Image.LANCZOS).convert("RGBA")
        kw = work / "overlay_kw" / f"f{i:05d}.png"
        mask = work / "masks" / f"s{idx + 1:05d}.png"
        if kw.exists():   # 03: 인물 → 핵심어 → 인물 컷아웃(같은 줌의 마스크)
            text = Image.open(kw).convert("RGBA")
            if text.getbbox():
                if not mask.exists():
                    sys.exit(f"마스크 없음: {mask.name} (pipeline.py masks 먼저 실행)")
                cut = img.copy()
                cut.putalpha(Image.open(mask).convert("L").resize((SRC_W, SRC_H)).crop(box).resize((W, H), Image.LANCZOS))
                img = Image.alpha_composite(Image.alpha_composite(img, text), cut)
        ov = work / "overlay" / f"f{i:05d}.png"
        if ov.exists():
            img = Image.alpha_composite(img, Image.open(ov).convert("RGBA"))
        img.convert("RGB").save(out / f"c{i:05d}.jpg", quality=95)
    print("합성", n, "프레임")


def peak_db(x):
    import numpy as np
    return 20 * math.log10(float(np.max(np.abs(x))) + 1e-9)


def read_wav(p):
    import numpy as np
    import wave
    w = wave.open(str(p))
    return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float).reshape(-1, w.getnchannels()).mean(1), w.getframerate()


def cmd_sfx(work):
    work = Path(work).resolve()
    plan, edl = plan_of(work), json.loads((work / "edl.json").read_text())
    cues = []
    if plan.get("sfx_default", True):
        chat_over_title = plan.get("chat") and plan.get("title") and plan["chat"]["start"] < plan["title"]["end"]
        if plan.get("title") and not chat_over_title:   # 말풍선이 제목과 같이 나오면 말풍선 소리만
            f, g = SFX_DEFAULT["title"]
            cues.append({"t": plan["title"].get("start", 0.0), "file": f, "gain_db": g, "why": "제목 등장"})
        if plan.get("keyword"):
            f, g = ("18_타이핑.wav", -16) if plan["keyword"]["design"] == "hand" else SFX_DEFAULT["keyword"]
            cues.append({"t": plan["keyword"]["start"] - SFX_LEAD, "file": f, "gain_db": g, "why": "핵심어 " + plan["keyword"]["design"]})
        if plan.get("chat"):   # 말풍선이 떨어져 닿는 순간(시작 +0.22초)
            cues.append({"t": plan["chat"]["start"] + 0.22 - SFX_LEAD, "file": "01_사진등장_뽁.wav", "gain_db": -12, "why": "시청자 질문 말풍선"})
        for it in (plan.get("panel") or {}).get("items", []):
            f, g = SFX_DEFAULT["panel"]
            cues.append({"t": it["at"] - SFX_LEAD, "file": f, "gain_db": g, "why": f"패널 {it['label']}"})
    for c in plan.get("sfx", []):
        cues.append({"t": c["t"] - SFX_LEAD, "file": c["file"], "gain_db": c.get("gain_db", -10), "why": c.get("why", "")})
    D = dur_out(plan, edl)
    cues = [dict(c, t=round(max(0.0, c["t"]), 3)) for c in cues if c["t"] < D - 0.1]
    voice = work / "audio_voice.wav"
    ff("-i", work / "audio_cut.wav", "-af", f"atrim=0:{D},afade=t=out:st={max(0, D - 0.08):.3f}:d=0.08", "-ar", 48000, voice)
    if not cues:
        shutil.copy(voice, work / "audio_final.wav")
        save(work / "sfx_cues.json", [])
        print("효과음 없음")
        return
    if len(cues) > 5:
        print(f"주의: 효과음 {len(cues)}개 (권장 3~5개)")
    v, sr = read_wav(voice)
    for _ in range(3):   # 효과음 피크가 같은 구간 목소리 피크보다 3dB 이상 낮아질 때까지 낮춘다 (KMH §7)
        fc = "".join(f"[{i + 1}]aformat=sample_rates=48000:channel_layouts=stereo,volume={c['gain_db']}dB,adelay={int(c['t'] * 1000)}|{int(c['t'] * 1000)}[s{i}];" for i, c in enumerate(cues))
        ins = []
        for c in cues:
            ins += ["-i", str(SFX_DIR / c["file"])]
        only = fc + "".join(f"[s{i}]" for i in range(len(cues))) + f"amix=inputs={len(cues)}:normalize=0[a]"
        ff("-f", "lavfi", "-t", D, "-i", "anullsrc=r=48000:cl=stereo", *ins, "-filter_complex", only.replace("[a]", "[m];[0][m]amix=inputs=2:normalize=0:duration=first[a]"), "-map", "[a]", "-c:a", "pcm_s16le", work / "sfx_only.wav")
        s, _ = read_wav(work / "sfx_only.wav")
        changed = False
        for c in cues:
            a = int(c["t"] * sr); b = a + int(0.3 * sr)
            c["voice_pk"], c["sfx_pk"] = round(peak_db(v[a:b]), 1), round(peak_db(s[a:b]), 1)
            if c["sfx_pk"] > c["voice_pk"] - 3 and c["voice_pk"] > 60:
                c["gain_db"] -= round(c["sfx_pk"] - c["voice_pk"] + 4)
                changed = True
        if not changed:
            break
    mix = fc + "[0]" + "".join(f"[s{i}]" for i in range(len(cues))) + f"amix=inputs={len(cues) + 1}:normalize=0:duration=first,alimiter=limit=0.79:level=false:latency=1[a]"
    (work / "mix_filter.txt").write_text(mix)
    ff("-i", voice, *ins, "-/filter_complex", work / "mix_filter.txt", "-map", "[a]", "-ar", 48000, work / "audio_final.wav")
    save(work / "sfx_cues.json", cues)
    lufs, pk = ebur128(work / "audio_final.wav")
    for c in cues:
        print(f"  {c['t']:6.3f}s {c['file']:<24} {c['gain_db']:>4}dB  목소리 피크 {c['voice_pk']} / 효과음 {c['sfx_pk']}  {c['why']}")
    print(f"효과음 {len(cues)}개 믹스: {lufs} LUFS, peak {pk} dBFS")


def contact_sheet(mp4, png, n=12):
    dur = float(ffprobe_json(mp4)["format"]["duration"])
    tmp = png.parent / "_sheet"
    tmp.mkdir(exist_ok=True)
    ts = [round(dur * (i + 0.5) / n, 2) for i in range(n)]
    for j, t in enumerate(ts):
        ff("-ss", t, "-i", mp4, "-frames:v", 1, "-vf", "scale=240:426", tmp / f"{j:02d}.png")
    ins = []
    for j in range(n):
        ins += ["-i", tmp / f"{j:02d}.png"]
    half = n // 2
    fc = "".join(f"[{j}]" for j in range(half)) + f"hstack={half}[a];" + "".join(f"[{j}]" for j in range(half, n)) + f"hstack={n - half}[b];[a][b]vstack,drawbox=y=ih/2*{1 - SPEC['safe_bottom']}:w=iw:h=2:color=red@0.6,drawbox=y=ih/2+ih/2*{1 - SPEC['safe_bottom']}:w=iw:h=2:color=red@0.6"
    ff(*ins, "-filter_complex", fc, png)
    shutil.rmtree(tmp)


def check(mp4):
    pr = ffprobe_json(mp4)
    v = next(s for s in pr["streams"] if s["codec_type"] == "video")
    a = next((s for s in pr["streams"] if s["codec_type"] == "audio"), None)
    num, den = map(int, v["r_frame_rate"].split("/"))
    dur = float(pr["format"]["duration"])
    lufs, pk = ebur128(mp4)
    err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(mp4), "-vf", "blackdetect=d=0.05,freezedetect=n=0.001:d=0.5", "-f", "null", "-"]).stderr
    rows = {
        "해상도": (f"{v['width']}x{v['height']}", v["height"] >= 1080 and abs(v["width"] / v["height"] - 9 / 16) < 0.01),
        "fps": (round(num / den, 2), abs(num / den - SPEC["fps"]) < 0.01),
        "길이": (round(dur, 2), dur <= SPEC["max_dur"]),
        "코덱": (v["codec_name"], v["codec_name"] in ("h264", "hevc")),
        "픽셀형식": (f"{v.get('pix_fmt')}/{v.get('color_range', '?')}", v.get("pix_fmt") == "yuv420p" and v.get("color_range") in ("tv", None)),
        "오디오": (f"{a['codec_name']} {a.get('sample_rate')}Hz {a.get('channels')}ch" if a else "없음", bool(a) and a.get("sample_rate") == "48000"),
        "음량": (f"{lufs} LUFS", abs(lufs - SPEC["lufs"]) <= SPEC["lufs_tol"]),
        "피크": (f"{pk} dBFS", pk <= SPEC["tp"]),
        "검은화면": (len(re.findall("black_start", err)), "black_start" not in err),
        "멈춘화면": (len(re.findall("freeze_start", err)), "freeze_start" not in err),
    }
    return {k: {"value": val, "ok": ok} for k, (val, ok) in rows.items()}


def write_srt(work, path, max_chars=14):
    """출력 시각 기준 전체 대사 SRT (유튜브·인스타 자막 업로드용). 컷 받아쓰기를 14자 안팎으로 묶는다.
    plan.srt_skip 에 넣은 단어(애매한 말·말 고침)는 뺀다."""
    plan, edl = plan_of(work), json.loads((work / "edl.json").read_text())
    D = dur_out(plan, edl)
    skip = set(plan.get("srt_skip", []))
    words = [w for w in fixed_words(work, plan) if w["start"] < D and w["text"] not in skip]
    cues, cur = [], []
    for w in words:
        text = " ".join(x["text"] for x in cur + [w])
        if cur and (len(text.replace(" ", "")) > max_chars or w["start"] - cur[-1]["end"] > 0.6):
            cues.append(cur); cur = []
        cur.append(w)
        if w["text"].endswith((".", "?", "!")):
            cues.append(cur); cur = []
    if cur:
        cues.append(cur)
    ts = lambda t: f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{int(t % 60):02d},{int(round(t % 1 * 1000)) % 1000:03d}"
    env = json.loads((work / "envelope.json").read_text()) if (work / "envelope.json").exists() else []
    first = env[0][0] if env else 0.0   # 받아쓰기 첫 단어 시각은 일찍 잡히는 경우가 많아 실제 첫 소리에 맞춘다
    lines = []
    for i, c in enumerate(cues, 1):
        a = max(c[0]["start"], first) if i == 1 else c[0]["start"]
        nxt = cues[i][0]["start"] if i < len(cues) else D
        b = max(a + 0.3, min(D, c[-1]["end"] + 0.15, nxt))
        lines += [str(i), f"{ts(a)} --> {ts(b)}", " ".join(x["text"] for x in c).rstrip("."), ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def cmd_encode(work, name):
    work = Path(work).resolve()
    info = load(work)
    OUTPUT.mkdir(exist_ok=True)
    hq, phone = OUTPUT / f"{name}_hq.mp4", OUTPUT / f"{name}_phone.mp4"
    hq.parent.mkdir(parents=True, exist_ok=True)
    ff("-framerate", FPS, "-i", work / "composite" / "c%05d.jpg", "-i", work / "audio_final.wav", "-map", "0:v", "-map", "1:a",
       "-vf", "scale=in_range=full:out_range=tv,format=yuv420p,setsar=1", "-color_range", "tv",
       "-c:v", "libx264", "-preset", "slow", "-crf", 18, "-c:a", "aac", "-b:a", "192k", "-ar", 48000, "-movflags", "+faststart", "-shortest", hq)
    ff("-i", hq, "-vf", "scale=720:1280,format=yuv420p", "-c:v", "libx264", "-crf", 28, "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", phone)
    srt = OUTPUT / f"{name}.srt"
    write_srt(work, srt)
    rep = {"hq": str(hq), "phone": str(phone), "srt": str(srt), "check": check(hq), "input_unchanged": sha256(info["input"]) == info["input_sha256"]}
    contact_sheet(hq, work / "sheet.png")
    rep_dur = float(ffprobe_json(hq)["format"]["duration"])
    rep["sheet"] = str(work / "sheet.png")
    rep["sheet_times"] = [round(rep_dur * (i + 0.5) / 12, 2) for i in range(12)]
    save(work / "report.json", rep)
    for k, r in rep["check"].items():
        print(f"  {'OK ' if r['ok'] else 'FAIL'} {k}: {r['value']}")
    print("원본 그대로:", rep["input_unchanged"], "| 장면 시트:", rep["sheet"], "(빨간 선 아래 = Reels 하단 20%)")
    print("장면 시트 시각(왼→오, 위→아래):", rep["sheet_times"])
    print("결과:", hq, phone, "| 자막 파일:", rep["srt"])


def cmd_render(work, name):
    cmd_overlay(work)
    cmd_compose(work)
    cmd_sfx(work)
    cmd_encode(work, name)


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    c = a[0]
    if c == "analyze":
        cmd_analyze(a[1], a[2])
    elif c == "cut":
        opts = {"no_cut": "--no-cut" in a}
        if "--drop" in a:
            opts["drop"] = [tuple(float(y) for y in x.split("-")) for x in a[a.index("--drop") + 1].split(",")]
        if "--keep" in a:
            opts["keep"] = [float(x) for x in a[a.index("--keep") + 1].split(",")]
        for k in ("speed", "lead", "tail", "min_gap", "pad_before", "pad_after"):
            flag = "--" + k.replace("_", "-")
            if flag in a:
                opts[k] = float(a[a.index(flag) + 1])
        cmd_cut(a[1], **opts)
    elif c == "frames":
        cmd_frames(a[1])
    elif c == "overlay":
        cmd_overlay(Path(a[1]))
    elif c == "masks":
        cmd_masks(a[1])
    elif c == "compose":
        cmd_compose(a[1])
    elif c == "sfx":
        cmd_sfx(a[1])
    elif c == "encode":
        cmd_encode(a[1], a[2])
    elif c == "render":
        cmd_render(Path(a[1]).resolve(), a[2])
    elif c == "check":
        for k, r in check(Path(a[1])).items():
            print(f"  {'OK ' if r['ok'] else 'FAIL'} {k}: {r['value']}")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
