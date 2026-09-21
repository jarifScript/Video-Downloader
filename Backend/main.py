from pathlib import Path
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
import ipaddress
import logging
import os
import re
import socket
import shutil
import threading
import tempfile
import time
import uuid
from urllib.parse import urlsplit

import certifi


def configure_curl_certificate():
    """Copy the CA bundle to a writable temporary path."""
    source = Path(certifi.where())
    temp_folder = Path(tempfile.gettempdir())
    target = temp_folder / "video_downloader_cacert.pem"
    if source != target and (
        not target.exists() or target.stat().st_size != source.stat().st_size
    ):
        shutil.copyfile(source, target)
    os.environ.setdefault("CURL_CA_BUNDLE", str(target))


configure_curl_certificate()

import yt_dlp

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl, Field


app = FastAPI()
logger = logging.getLogger(__name__)


# -----------------------------
# Allow React to communicate
# -----------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip().rstrip("/")
        for origin in os.environ.get(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Download folder
# -----------------------------

DOWNLOAD_FOLDER = Path(
    os.environ.get(
        "DOWNLOAD_DIR",
        str(Path(tempfile.gettempdir()) / "video-downloader-downloads"),
    )
)
DOWNLOAD_FOLDER.mkdir(exist_ok=True)

MAX_DURATION_SECONDS = 60 * 60
MAX_FILE_SIZE_MB = int(os.environ.get("MAX_FILE_SIZE_MB", "512"))
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024
DOWNLOAD_TIMEOUT_SECONDS = 30
ABANDONED_FILE_AGE_SECONDS = 60 * 60
COOKIE_FILE_PATH = os.environ.get("COOKIES_FILE_PATH")
COOKIE_FILE = (
    COOKIE_FILE_PATH
    if COOKIE_FILE_PATH and os.path.exists(COOKIE_FILE_PATH)
    else None
)
JOB_RETENTION_SECONDS = 60 * 60
DOWNLOAD_WORKERS = 2
YOUTUBE_PO_TOKEN = os.environ.get("YOUTUBE_PO_TOKEN")
YOUTUBE_PO_TOKEN_CLIENT = os.environ.get("YOUTUBE_PO_TOKEN_CLIENT", "mweb")
UUID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
TEMP_FILE_PATTERN = re.compile(r"^[0-9a-f]{32}\..+$")
ALLOWED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "instagram.com",
    "www.instagram.com",
    "tiktok.com",
    "www.tiktok.com",
}


class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(deque)

    def check(self, key, limit, window_seconds):
        now = time.monotonic()
        timestamps = self.requests[key]
        while timestamps and now - timestamps[0] >= window_seconds:
            timestamps.popleft()
        if len(timestamps) >= limit:
            return False
        timestamps.append(now)
        return True


rate_limiter = RateLimiter()
download_executor = ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS)
jobs = {}
jobs_lock = threading.Lock()


@app.get("/health")
def health_check():
    return {"status": "ok"}


def cleanup_abandoned_files():
    cutoff = time.time() - ABANDONED_FILE_AGE_SECONDS
    for file in DOWNLOAD_FOLDER.iterdir():
        if not file.is_file() or not TEMP_FILE_PATTERN.match(file.name):
            continue
        try:
            if file.stat().st_mtime < cutoff:
                file.unlink()
        except OSError:
            logger.warning("Unable to remove abandoned file %s", file, exc_info=True)


def cleanup_old_jobs():
    cutoff = time.time() - JOB_RETENTION_SECONDS
    with jobs_lock:
        expired_jobs = [
            job_id
            for job_id, job in jobs.items()
            if job["status"] in {"completed", "failed"} and job["updated_at"] < cutoff
        ]
        for job_id in expired_jobs:
            del jobs[job_id]


@app.on_event("startup")
def remove_abandoned_files_on_startup():
    cleanup_abandoned_files()
    cleanup_old_jobs()


def find_ffmpeg():
    """Find FFmpeg in PATH or in the per-user WinGet installation directory."""
    executable = shutil.which("ffmpeg")

    if executable:
        return executable

    local_app_data = os.environ.get("LOCALAPPDATA")

    if local_app_data:
        winget_root = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"

        for executable in winget_root.glob("**/bin/ffmpeg.exe"):
            return str(executable.parent)

    return None


# -----------------------------
# Data we receive from React
# -----------------------------

class VideoRequest(BaseModel):
    url: HttpUrl
    resolution: int | None = Field(default=None, ge=144, le=4320)


def get_extractor_args():
    if not YOUTUBE_PO_TOKEN:
        return {}
    return {
        "youtube": {
            "player_client": [YOUTUBE_PO_TOKEN_CLIENT],
            "po_token": [f"{YOUTUBE_PO_TOKEN_CLIENT}+{YOUTUBE_PO_TOKEN}"],
        }
    }


def get_runtime_options():
    return {"js_runtimes": {"node": {}}}


def validate_request(request: Request, video_request: VideoRequest, action: str):
    client_ip = request.client.host if request.client else "unknown"
    parsed_url = urlsplit(str(video_request.url))
    hostname = (parsed_url.hostname or "").lower().rstrip(".")
    if (
        parsed_url.scheme not in {"http", "https"}
        or hostname not in ALLOWED_HOSTS
        or parsed_url.username
        or parsed_url.password
        or parsed_url.port not in {None, 80, 443}
    ):
        raise HTTPException(status_code=400, detail="This video URL is not supported.")

    try:
        addresses = socket.getaddrinfo(hostname, parsed_url.port or 443, type=socket.SOCK_STREAM)
    except (OSError, ValueError):
        raise HTTPException(status_code=400, detail="This video URL could not be validated.")

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise HTTPException(status_code=400, detail="This video URL could not be validated.")

    limits = {"info": (60, 60), "download": (10, 600)}
    limit, window = limits[action]
    if not rate_limiter.check(f"{action}:{client_ip}", limit, window):
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")


def validate_video_id(video_id: str):
    if not UUID_PATTERN.fullmatch(video_id):
        raise HTTPException(status_code=404, detail="File not found")


def raise_download_error(error):
    logger.exception("Downloader request failed: %s", error)
    error_message = str(error).lower()
    if "failed to extract any player response" in error_message:
        detail = (
            "YouTube blocked this server request. Configure a valid YOUTUBE_PO_TOKEN "
            "in Render and redeploy, or try another public video."
        )
    elif "unexpected response from webpage request" in error_message:
        detail = "TikTok blocked this request. Try again later or use a publicly viewable video."
    elif "private video" in error_message:
        detail = "This video is private and cannot be downloaded."
    elif "unavailable" in error_message or "not available" in error_message:
        detail = "This video is unavailable, private, region-restricted, or requires sign-in."
    else:
        detail = "Unable to process this video right now."
    raise HTTPException(status_code=400, detail=detail)


# -----------------------------
# Get video information
# -----------------------------

@app.post("/api/info")
def get_video_info(request: Request, video_request: VideoRequest):

    validate_request(request, video_request, "info")

    try:

        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "socket_timeout": DOWNLOAD_TIMEOUT_SECONDS,
            "extractor_args": get_extractor_args(),
            **get_runtime_options(),
            "cookiefile": COOKIE_FILE,
            "match_filter": lambda info, *, incomplete: (
                "This video exceeds the one-hour duration limit."
                if info.get("duration") and info["duration"] > MAX_DURATION_SECONDS
                else None
            ),
        }

        with yt_dlp.YoutubeDL(options) as ydl:

            info = ydl.extract_info(
                str(video_request.url),
                download=False
            )

        return {
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "platform": info.get("extractor_key")
        }

    except HTTPException:
        raise
    except Exception as error:
        raise_download_error(error)


# -----------------------------
# Download video
# -----------------------------

def download_video(url, filename, resolution):

    output_path = DOWNLOAD_FOLDER / filename
    hostname = (urlsplit(url).hostname or "").lower().rstrip(".")
    is_youtube = hostname in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}

    if is_youtube:
        format_selector = (
            f"bestvideo[height<={resolution}][ext=mp4]+bestaudio[ext=m4a]/"
            f"best[height<={resolution}][ext=mp4]"
            if resolution
            else "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]"
        )
    else:
        format_selector = (
            f"bestvideo[height<={resolution}]+bestaudio/"
            f"best[height<={resolution}]/best"
            if resolution
            else "bestvideo+bestaudio/best"
        )

    options = {

        "format": format_selector,

        # Ask FFmpeg to make MP4 when merging is necessary
        "merge_output_format": "mp4",

        # Encode the audio stream as AAC so MP4 players can decode it.
        "postprocessor_args": {
            "Merger": ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k"]
        },

        # Support installations that have not refreshed the server's PATH.
        "ffmpeg_location": find_ffmpeg(),

        # File name
        "outtmpl": str(output_path),

        "quiet": True,
        "no_warnings": True,
        "socket_timeout": DOWNLOAD_TIMEOUT_SECONDS,
        "extractor_args": get_extractor_args(),
        **get_runtime_options(),
        "cookiefile": COOKIE_FILE,
        "retries": 2,
        "fragment_retries": 2,
        "max_filesize": MAX_FILE_SIZE,
        "match_filter": lambda info, *, incomplete: (
            "This video exceeds the one-hour duration limit."
            if info.get("duration") and info["duration"] > MAX_DURATION_SECONDS
            else None
        ),
    }

    with yt_dlp.YoutubeDL(options) as ydl:

        ydl.download([url])


def run_download_job(job_id, url, resolution):
    with jobs_lock:
        jobs[job_id]["status"] = "downloading"
        jobs[job_id]["updated_at"] = time.time()

    try:
        filename = f"{job_id}.%(ext)s"
        download_video(url, filename, resolution)
        file = DOWNLOAD_FOLDER / f"{job_id}.mp4"

        if not file.is_file():
            raise RuntimeError("Merged video file not found")

        with jobs_lock:
            jobs[job_id].update({
                "status": "completed",
                "filename": file.name,
                "updated_at": time.time(),
            })
    except Exception as error:
        cleanup_files_for_id(job_id)
        logger.exception("Background download job failed: %s", job_id)
        error_message = str(error).lower()
        if "max filesize" in error_message or "file is larger" in error_message:
            safe_error = f"This video is larger than the {MAX_FILE_SIZE_MB} MB limit."
        elif "duration" in error_message or "one-hour" in error_message:
            safe_error = "This video is longer than the one-hour limit."
        elif "unsupported url" in error_message or "no suitable extractor" in error_message:
            safe_error = "This video platform or URL is not supported."
        elif "unavailable" in error_message or "private video" in error_message:
            safe_error = "This video is unavailable or private."
        elif "requested format" in error_message or "no video formats" in error_message:
            safe_error = "No downloadable format is available for this video."
        else:
            safe_error = "Unable to process this video right now."
        with jobs_lock:
            jobs[job_id].update({
                "status": "failed",
                "error": safe_error,
                "updated_at": time.time(),
            })


# -----------------------------
# Download API
# -----------------------------

@app.post("/api/download")
def download(request: Request, video_request: VideoRequest):

    validate_request(request, video_request, "download")
    cleanup_old_jobs()
    video_id = uuid.uuid4().hex

    with jobs_lock:
        jobs[video_id] = {
            "status": "queued",
            "filename": None,
            "updated_at": time.time(),
        }

    download_executor.submit(
        run_download_job,
        video_id,
        str(video_request.url),
        video_request.resolution,
    )

    return {"job_id": video_id, "status": "queued"}


@app.get("/api/download/{job_id}")
def get_download_status(job_id: str):
    validate_video_id(job_id)

    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Download job not found")
        status = job["status"]
        response = {"job_id": job_id, "status": status}
        if status == "completed":
            response.update({
                "download_url": f"/api/file/{job_id}",
                "filename": job["filename"],
            })
        elif status == "failed":
            response["error"] = job["error"]
        return response


# -----------------------------
# Send file to user
# -----------------------------

@app.get("/api/file/{video_id}")
def get_file(
    video_id: str,
    background_tasks: BackgroundTasks
    ):

    validate_video_id(video_id)

    file = DOWNLOAD_FOLDER / f"{video_id}.mp4"

    if not file.is_file():

        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    # Delete file after sending
    background_tasks.add_task(
        delete_file,
        file
    )

    return FileResponse(
        path=file,
        filename=file.name,
        media_type="video/mp4"
    )


# -----------------------------
# Delete temporary file
# -----------------------------

def delete_file(file):

    try:

        if file.exists():
            file.unlink()

    except Exception:
        pass


def cleanup_files_for_id(video_id):
    for file in DOWNLOAD_FOLDER.glob(f"{video_id}.*"):
        if file.is_file():
            delete_file(file)