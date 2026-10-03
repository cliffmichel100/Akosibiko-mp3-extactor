# Akosibiko Audio Studio

A browser-based audio processing tool built with Python + Flask.

## Features

- Upload audio/video files
- Noise reduction
- Loudness normalization
- AI vocal/instrumental separation with Demucs
- Instrumental/accompaniment output
- MP3 export at 192/256/320 kbps
- In-browser audio preview
- Mobile-friendly interface
- 250 MB upload limit
- Root-level files only — no project folders are required

## Files

- `app.py` — complete web application
- `requirements.txt` — Python dependencies

## Local setup

You need Python 3.10+ and FFmpeg.

Install FFmpeg:

### Windows
Install FFmpeg and add its `bin` directory to PATH.

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install ffmpeg
```

### macOS
```bash
brew install ffmpeg
```

Then:

```bash
pip install -r requirements.txt
python app.py
```

Open:

```text
http://localhost:5000
```

## GitHub deployment

GitHub Pages cannot run the Python/Flask backend by itself because it only serves static files.

Put `app.py` and `requirements.txt` in the root of a GitHub repository, then deploy that repository to a Python-capable host such as Render, Railway, or another VPS/container service.

Recommended start command:

```bash
gunicorn app:app
```

The deployment environment must also have FFmpeg installed.

## Important production notes

This app processes uploaded files on the server. For a public service, add authentication, rate limiting, disk quotas, automatic cleanup of old jobs, HTTPS, and a queue/worker system before opening it to unrestricted public traffic.

Demucs is CPU/GPU intensive. Large files can take significant time.

## Branding

The bottom thumbmark is labeled:

AKOSIBIKO
