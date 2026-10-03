import os
import uuid
import shutil
import subprocess
import tempfile
from pathlib import Path

from flask import Flask, request, jsonify, send_file, render_template_string
from werkzeug.utils import secure_filename

# ============================================================
# Akosibiko Audio Studio
# Single-file Flask web application
#
# Features:
# - Upload common audio/video files
# - Audio normalization
# - Noise reduction
# - Vocal/instrumental separation with Demucs
# - Instrumental/accompaniment creation
# - MP3 export
# - In-browser audio preview/download
#
# System dependency:
#   FFmpeg must be installed and available on PATH.
#
# Optional AI separation dependency:
#   Demucs is installed from requirements.txt.
# ============================================================

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 250 * 1024 * 1024  # 250 MB
app.secret_key = os.environ.get("SECRET_KEY", "akosibiko-audio-studio")

BASE_DIR = Path(__file__).resolve().parent
WORK_DIR = BASE_DIR / "akosibiko_jobs"
WORK_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {
    "mp3", "wav", "flac", "m4a", "aac", "ogg", "opus", "wma",
    "mp4", "mov", "mkv", "webm"
}

HTML = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Akosibiko Audio Studio</title>
<style>
:root{
  --bg:#07111f; --panel:#0d1b2e; --panel2:#10243c;
  --text:#f4f7fb; --muted:#9db0c6; --line:#20364f;
  --accent:#63e6be; --accent2:#5da9ff; --danger:#ff6b6b;
}
*{box-sizing:border-box}
body{
  margin:0; font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;
  background:radial-gradient(circle at 20% 0%,#12365b 0,#07111f 42%,#040a12 100%);
  color:var(--text); min-height:100vh;
}
.wrap{width:min(1050px,94%);margin:auto;padding:28px 0 20px}
.hero{text-align:center;padding:24px 10px 18px}
.logo{
  width:66px;height:66px;border-radius:20px;margin:auto;
  display:grid;place-items:center;font-weight:900;font-size:25px;
  background:linear-gradient(135deg,var(--accent),var(--accent2));
  color:#03111d;box-shadow:0 15px 45px #0007
}
h1{font-size:clamp(30px,6vw,52px);margin:18px 0 8px;letter-spacing:-1.5px}
.subtitle{color:var(--muted);max-width:720px;margin:auto;line-height:1.65}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:18px}
.card{
  background:linear-gradient(180deg,#0e2035e8,#091626e8);
  border:1px solid var(--line);border-radius:22px;padding:22px;
  box-shadow:0 20px 60px #0004;backdrop-filter:blur(10px)
}
.full{grid-column:1/-1}
label{display:block;font-weight:700;margin:0 0 8px}
input[type=file],select{
  width:100%;padding:13px;border:1px solid var(--line);border-radius:13px;
  background:#071321;color:var(--text)
}
.drop{
  border:1.5px dashed #3c638a;border-radius:17px;padding:28px 18px;
  text-align:center;cursor:pointer;background:#071625aa
}
.drop:hover{border-color:var(--accent)}
.drop strong{display:block;font-size:18px;margin-bottom:6px}
.small{font-size:13px;color:var(--muted)}
.options{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-top:16px}
.check{
  display:flex;align-items:center;gap:10px;padding:13px;border:1px solid var(--line);
  border-radius:13px;background:#081727
}
.check input{width:18px;height:18px;accent-color:var(--accent)}
button{
  border:0;border-radius:14px;padding:14px 18px;font-weight:800;cursor:pointer;
  background:linear-gradient(135deg,var(--accent),#46c9ff);color:#04101b;
  box-shadow:0 10px 30px #46d8c32b
}
button:disabled{opacity:.5;cursor:not-allowed}
.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}
.status{margin-top:15px;padding:13px 15px;border-radius:13px;background:#071625;color:var(--muted)}
.progress{height:9px;background:#06101b;border-radius:99px;overflow:hidden;margin-top:12px;display:none}
.bar{height:100%;width:0;background:linear-gradient(90deg,var(--accent),var(--accent2));transition:width .3s}
.result{margin-top:16px;display:grid;gap:12px}
.result-item{
  border:1px solid var(--line);background:#071625;border-radius:15px;padding:14px
}
audio{width:100%;margin-top:8px}
a.download{
  display:inline-block;margin-top:9px;padding:9px 12px;border-radius:10px;
  color:#03111d;background:var(--accent);font-weight:800;text-decoration:none
}
footer{text-align:center;color:#6f849b;padding:28px 0 12px;font-size:13px}
.thumb{
  display:inline-flex;align-items:center;gap:8px;color:#b9cadb;font-weight:900;
  letter-spacing:1.5px;text-transform:uppercase
}
.thumbmark{
  width:24px;height:24px;border-radius:50%;display:inline-grid;place-items:center;
  background:linear-gradient(135deg,var(--accent),var(--accent2));color:#04101b;font-size:12px
}
@media(max-width:720px){.grid{grid-template-columns:1fr}.options{grid-template-columns:1fr}.full{grid-column:auto}}
</style>
</head>
<body>
<div class="wrap">
  <section class="hero">
    <div class="logo">A</div>
    <h1>Akosibiko Audio Studio</h1>
    <p class="subtitle">
      Clean your audio, reduce unwanted noise, separate vocals from instruments,
      create an accompaniment, and export your finished track as MP3.
    </p>
  </section>

  <div class="grid">
    <section class="card full">
      <label>1. Choose your audio or video</label>
      <div class="drop" id="drop">
        <strong>Drop a file here or tap to browse</strong>
        <span class="small">MP3, WAV, FLAC, M4A, AAC, OGG, OPUS, MP4, MOV, MKV and WEBM · max 250 MB</span>
        <input id="file" type="file" accept="audio/*,video/*" hidden>
      </div>
      <div id="filename" class="status">No file selected.</div>
    </section>

    <section class="card">
      <label>2. Processing</label>
      <div class="options">
        <label class="check"><input id="normalize" type="checkbox" checked> Normalize audio</label>
        <label class="check"><input id="denoise" type="checkbox" checked> Reduce noise</label>
        <label class="check"><input id="separate" type="checkbox" checked> Separate vocals</label>
        <label class="check"><input id="accomp" type="checkbox" checked> Make accompaniment</label>
      </div>
      <div style="margin-top:16px">
        <label for="quality">MP3 quality</label>
        <select id="quality">
          <option value="192">192 kbps — balanced</option>
          <option value="256">256 kbps — high</option>
          <option value="320" selected>320 kbps — maximum</option>
        </select>
      </div>
    </section>

    <section class="card">
      <label>3. Start studio processing</label>
      <p class="small">
        AI stem separation uses Demucs when enabled. Processing time depends on
        audio length and the server's CPU/GPU.
      </p>
      <div class="actions">
        <button id="process">Process Audio</button>
        <button id="clear" type="button" style="background:#17283d;color:#dce9f7">Clear</button>
      </div>
      <div class="progress" id="progress"><div class="bar" id="bar"></div></div>
      <div class="status" id="status">Ready.</div>
    </section>

    <section class="card full">
      <label>Results</label>
      <div id="results" class="result">
        <div class="small">Your processed files will appear here.</div>
      </div>
    </section>
  </div>

  <footer>
    <div class="thumb"><span class="thumbmark">A</span> Akosibiko</div>
    <div style="margin-top:7px">Audio tools made for simple, practical editing.</div>
  </footer>
</div>

<script>
const $ = id => document.getElementById(id);
const fileInput = $("file"), drop = $("drop"), filename = $("filename");
let selectedFile = null;

drop.onclick = () => fileInput.click();
fileInput.onchange = () => setFile(fileInput.files[0]);

["dragenter","dragover"].forEach(e => drop.addEventListener(e, ev => {
  ev.preventDefault(); drop.style.borderColor = "#63e6be";
}));
["dragleave","drop"].forEach(e => drop.addEventListener(e, ev => {
  ev.preventDefault(); drop.style.borderColor = "";
}));
drop.addEventListener("drop", ev => setFile(ev.dataTransfer.files[0]));

function setFile(f){
  if(!f) return;
  selectedFile = f;
  filename.textContent = `${f.name} · ${(f.size/1024/1024).toFixed(2)} MB`;
}

$("clear").onclick = () => {
  selectedFile = null; fileInput.value = ""; filename.textContent = "No file selected.";
  $("results").innerHTML = '<div class="small">Your processed files will appear here.</div>';
  $("status").textContent = "Ready.";
  $("bar").style.width = "0%"; $("progress").style.display = "none";
};

$("process").onclick = async () => {
  if(!selectedFile){ $("status").textContent = "Please choose a file first."; return; }

  const fd = new FormData();
  fd.append("file", selectedFile);
  fd.append("normalize", $("normalize").checked ? "1":"0");
  fd.append("denoise", $("denoise").checked ? "1":"0");
  fd.append("separate", $("separate").checked ? "1":"0");
  fd.append("accompaniment", $("accomp").checked ? "1":"0");
  fd.append("quality", $("quality").value);

  $("process").disabled = true;
  $("progress").style.display = "block";
  $("bar").style.width = "8%";
  $("status").textContent = "Uploading and preparing your audio…";

  try{
    let pct = 10;
    const timer = setInterval(() => {
      pct = Math.min(pct + Math.random()*7, 92);
      $("bar").style.width = pct + "%";
    }, 900);

    const res = await fetch("/process", {method:"POST", body:fd});
    const data = await res.json();
    clearInterval(timer);
    $("bar").style.width = "100%";

    if(!res.ok || !data.ok) throw new Error(data.error || "Processing failed.");

    $("status").textContent = data.message || "Finished.";
    $("results").innerHTML = data.files.map(x => `
      <div class="result-item">
        <strong>${escapeHtml(x.label)}</strong>
        <audio controls preload="metadata" src="${x.url}"></audio>
        <a class="download" href="${x.url}" download>Download MP3</a>
      </div>
    `).join("");
  }catch(err){
    $("status").textContent = "Error: " + err.message;
  }finally{
    $("process").disabled = false;
  }
};

function escapeHtml(s){
  return String(s).replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]));
}
</script>
</body>
</html>
"""

def allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def run(cmd, timeout=1800):
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-4000:] or "Command failed.")
    return result

def ffmpeg_to_wav(src, dst):
    run([
        "ffmpeg", "-y", "-i", str(src),
        "-vn", "-ac", "2", "-ar", "44100",
        "-c:a", "pcm_s16le", str(dst)
    ])

def normalize_audio(src, dst):
    run([
        "ffmpeg", "-y", "-i", str(src),
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-ar", "44100", "-ac", "2",
        "-c:a", "pcm_s16le", str(dst)
    ])

def denoise_audio(src, dst):
    # FFmpeg's afftdn provides practical broadband noise reduction without
    # requiring a separate DSP package.
    run([
        "ffmpeg", "-y", "-i", str(src),
        "-af", "afftdn=nr=18:nf=-40",
        "-ar", "44100", "-ac", "2",
        "-c:a", "pcm_s16le", str(dst)
    ])

def export_mp3(src, dst, bitrate):
    run([
        "ffmpeg", "-y", "-i", str(src),
        "-vn", "-codec:a", "libmp3lame", "-b:a", f"{bitrate}k",
        "-ar", "44100", str(dst)
    ])

def separate_demucs(src, outdir):
    # Demucs creates a four-stem mix (drums, bass, other, vocals).
    # --two-stems=vocals also creates a practical vocal/accompaniment split.
    run([
        "python", "-m", "demucs",
        "--two-stems=vocals",
        "-n", "htdemucs",
        "-o", str(outdir),
        str(src)
    ], timeout=3600)

def find_demucs_outputs(root):
    candidates = list(root.rglob("*"))
    vocals = next((p for p in candidates if p.is_file() and p.name.lower() == "vocals.wav"), None)
    no_vocals = next((p for p in candidates if p.is_file() and p.name.lower() in {"no_vocals.wav", "accompaniment.wav"}), None)
    return vocals, no_vocals

@app.get("/")
def index():
    return render_template_string(HTML)

@app.post("/process")
def process():
    job_id = uuid.uuid4().hex
    job = WORK_DIR / job_id
    job.mkdir(parents=True, exist_ok=True)

    try:
        upload = request.files.get("file")
        if not upload or not upload.filename:
            return jsonify(ok=False, error="No file uploaded."), 400
        if not allowed(upload.filename):
            return jsonify(ok=False, error="Unsupported file type."), 400

        original = job / secure_filename(upload.filename)
        upload.save(original)

        bitrate = request.form.get("quality", "320")
        if bitrate not in {"192", "256", "320"}:
            bitrate = "320"

        normalize = request.form.get("normalize") == "1"
        denoise = request.form.get("denoise") == "1"
        separate = request.form.get("separate") == "1"
        accompaniment = request.form.get("accompaniment") == "1"

        base_wav = job / "source.wav"
        ffmpeg_to_wav(original, base_wav)

        current = base_wav
        if denoise:
            cleaned = job / "cleaned.wav"
            denoise_audio(current, cleaned)
            current = cleaned

        if normalize:
            normalized = job / "normalized.wav"
            normalize_audio(current, normalized)
            current = normalized

        output_dir = job / "outputs"
        output_dir.mkdir()

        results = []

        if separate:
            demucs_dir = job / "stems"
            demucs_dir.mkdir()
            try:
                separate_demucs(current, demucs_dir)
                vocals, instrumental = find_demucs_outputs(demucs_dir)

                if vocals:
                    vocal_mp3 = output_dir / "vocals.mp3"
                    export_mp3(vocals, vocal_mp3, bitrate)
                    results.append({"label":"Vocals / Voice", "url":f"/download/{job_id}/vocals.mp3"})

                if instrumental and accompaniment:
                    acc_mp3 = output_dir / "accompaniment.mp3"
                    export_mp3(instrumental, acc_mp3, bitrate)
                    results.append({"label":"Instrumental / Accompaniment", "url":f"/download/{job_id}/accompaniment.mp3"})

                if instrumental and not accompaniment:
                    inst_mp3 = output_dir / "instrumental.mp3"
                    export_mp3(instrumental, inst_mp3, bitrate)
                    results.append({"label":"Instrumental", "url":f"/download/{job_id}/instrumental.mp3"})
            except Exception as exc:
                # If Demucs is unavailable, still provide a cleaned master.
                fallback = output_dir / "processed.mp3"
                export_mp3(current, fallback, bitrate)
                results.append({
                    "label":"Processed Master (AI separation unavailable)",
                    "url":f"/download/{job_id}/processed.mp3"
                })
                results.append({
                    "label":"Separation note",
                    "url":f"/download/{job_id}/processed.mp3"
                })

        else:
            master = output_dir / "processed.mp3"
            export_mp3(current, master, bitrate)
            results.append({"label":"Processed Master", "url":f"/download/{job_id}/processed.mp3"})

        # Always provide a master if separation produced no usable file.
        if not results or not any((output_dir / f).exists() for f in ["vocals.mp3","accompaniment.mp3","instrumental.mp3","processed.mp3"]):
            master = output_dir / "processed.mp3"
            export_mp3(current, master, bitrate)
            results.append({"label":"Processed Master", "url":f"/download/{job_id}/processed.mp3"})

        return jsonify(ok=True, message="Your audio is ready.", files=results)

    except FileNotFoundError as exc:
        return jsonify(
            ok=False,
            error="A required program is missing. Make sure FFmpeg is installed and available on PATH."
        ), 500
    except subprocess.TimeoutExpired:
        return jsonify(ok=False, error="Processing took too long. Try a shorter audio file."), 504
    except Exception as exc:
        return jsonify(ok=False, error=str(exc)), 500

@app.get("/download/<job_id>/<filename>")
def download(job_id, filename):
    safe = secure_filename(filename)
    target = WORK_DIR / job_id / "outputs" / safe
    if not target.exists() or not target.is_file():
        return "File not found", 404
    return send_file(target, as_attachment=True, download_name=safe, mimetype="audio/mpeg")

@app.get("/health")
def health():
    return jsonify(status="ok", app="Akosibiko Audio Studio")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
