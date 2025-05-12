# server.py
from fastapi import FastAPI, UploadFile, File, Path, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
import os
from datetime import datetime

from mv.util import process_path

# -------------------------------------------------------------------------------------
# Resources

save_rootdir = os.environ.get('MV_MEDIA_RECORDINGS_DIR')

if save_rootdir is None:
    from mv.util import app_filepath

    # Default to current directory if not set
    save_rootdir = app_filepath('media_recordings', ensure_dir_exists=True)

save_rootdir = process_path(save_rootdir, ensure_dir_exists=True)

# video_recordings_dir = os.path.join(save_rootdir, "video")
# audio_recordings_dir = os.path.join(save_rootdir, "audio")
# video_recordings_dir = process_path(video_recordings_dir, ensure_dir_exists=True)
# audio_recordings_dir = process_path(audio_recordings_dir, ensure_dir_exists=True)
print("--------------------------------------------------------------------")
print(f"\nMedia recordings will be saved to: {save_rootdir}\n")
print("--------------------------------------------------------------------")

# -------------------------------------------------------------------------------------
# FastAPI app instance

app = FastAPI()

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Enable CORS if front-end served elsewhere
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# Serve JS and other assets from ./static
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/video/{space}", response_class=HTMLResponse)
async def get_video_recorder(
    request: Request, space: str = Path(..., description="Space")
):
    return templates.TemplateResponse(
        "video_recorder.html", {"request": request, "space": space}
    )


@app.get("/audio/{space}", response_class=HTMLResponse)
async def get_audio_recorder(
    request: Request,
    space: str = Path(..., description="Space"),
):
    return templates.TemplateResponse(
        "audio_recorder.html", {"request": request, "space": space}
    )


def resolve_upload_inputs(start_ts=None, end_ts=None, session=None):
    """
    Resolves input parameters for upload_chunk route.

    Args:
        start_ts: Start timestamp
        end_ts: End timestamp
        session: Session identifier

    Returns:
        Tuple of (filename_timestamp, session_id)
    """
    # Generate filename timestamp based on available inputs
    if not start_ts and not end_ts:
        # No timestamps provided, use current time
        now = datetime.now().isoformat()
        filename_ts = now.replace(':', '').replace('-', '').replace('.', '')
    elif start_ts and not end_ts:
        # Only start_ts provided
        filename_ts = start_ts.replace(':', '').replace('-', '').replace('.', '')
    elif not start_ts and end_ts:
        # Only end_ts provided
        filename_ts = end_ts.replace(':', '').replace('-', '').replace('.', '')
    else:
        # Both timestamps provided
        safe_start_ts = start_ts.replace(':', '').replace('-', '').replace('.', '')
        safe_end_ts = end_ts.replace(':', '').replace('-', '').replace('.', '')
        filename_ts = f"{safe_start_ts}_{safe_end_ts}"

    # Compute session from timestamp if not provided
    if not session:
        # Use start_ts for session if available, otherwise end_ts, otherwise current time
        timestamp_for_session = start_ts or end_ts
        if timestamp_for_session:
            try:
                # Remove Z and microseconds for compatibility
                clean_ts = timestamp_for_session.replace('Z', '+00:00')
                if '.' in clean_ts:
                    clean_ts = clean_ts[: clean_ts.index('.')]
                dt = datetime.fromisoformat(clean_ts)
                session = dt.strftime('%y%m%d_%H%M%S')
            except ValueError:
                # If parsing fails, use current time
                session = datetime.now().strftime('%y%m%d_%H%M%S')
        else:
            session = datetime.now().strftime('%y%m%d_%H%M%S')

    return filename_ts, session


@app.post("/upload_chunk")
async def upload_chunk_default(
    file: UploadFile = File(...),
    start_ts: str = Form(None),
    end_ts: str = Form(None),
    session: str = Form(None),
):
    """Default route for uploading chunks to the catch_all_space."""
    return await upload_chunk(file, "catch_all_space", start_ts, end_ts, session)


@app.post("/upload_chunk/{space}")
async def upload_chunk(
    file: UploadFile = File(...),
    space: str = Path(..., description="Space to save into"),
    start_ts: str = Form(None),
    end_ts: str = Form(None),
    session: str = Form(None),
):
    """
    Receives a video segment and saves it within session subfolder inside space folder.

    - If space is not provided, defaults to "catch_all_space" (via the default route)
    - If no timestamp is given, server uses its own
    - If only one timestamp is given, uses that for the filename
    - If session is not provided, computes it from the timestamp
    """
    # Resolve filename timestamp and session
    filename_ts, session_id = resolve_upload_inputs(start_ts, end_ts, session)

    # Ensure space directory exists
    space_dirpath = os.path.join(save_rootdir, space)
    os.makedirs(space_dirpath, exist_ok=True)

    # Ensure session subdirectory exists
    session_dirpath = os.path.join(space_dirpath, session_id)
    os.makedirs(session_dirpath, exist_ok=True)

    # Create filename with the resolved timestamp
    filename = f"{filename_ts}.webm"

    path = os.path.join(session_dirpath, filename)

    contents = await file.read()
    with open(path, "wb") as f:
        f.write(contents)

    return {"status": "saved", "path": path}
