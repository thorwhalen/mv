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
# Store concerns
# TODO: Refactor to dol

import os
from typing import Optional, Tuple


def get_path(
    save_rootdir: str,
    space: str,
    start_ts: Optional[str],
    end_ts: Optional[str],
    session: Optional[str],
    resolve_upload_inputs: callable,
) -> Tuple[str, str]:
    """
    Compute the full path to save the file.

    Args:
        save_rootdir: Root directory for saving files
        space: Namespace or subdirectory
        start_ts: Optional start timestamp
        end_ts: Optional end timestamp
        session: Optional session identifier
        resolve_upload_inputs: Function to resolve timestamps and session ID

    Returns:
        Tuple containing the full file path and the session ID
    """
    filename_ts, session_id = resolve_upload_inputs(start_ts, end_ts, session)
    session_dirpath = os.path.join(save_rootdir, space, session_id)
    filename = f"{filename_ts}.webm"
    path = os.path.join(session_dirpath, filename)
    return path, session_id


def store_contents(path: str, contents: bytes):
    """
    Write binary contents to the given path, ensuring the directory exists.

    Args:
        path: The full path where contents should be saved
        contents: The binary data to save

    """
    # Ensure the directory exists
    dirpath = os.path.dirname(path)
    os.makedirs(dirpath, exist_ok=True)

    # Write the contents
    with open(path, "wb") as f:
        f.write(contents)


# from dol import Files, wrap_kvs, mk_dirs_if_missing

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
    path, session_id = get_path(
        save_rootdir, space, start_ts, end_ts, session, resolve_upload_inputs
    )
    contents = await file.read()  # Add await here
    store_contents(path, contents)
    return {"status": "saved", "path": path, "session": session_id}


# Add a root route handler
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Media Recording Server</title>
        <style>
            body { font-family: system-ui, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            h1 { color: #444; }
            .container { display: flex; gap: 20px; margin-top: 20px; }
            .card { background: #f5f5f5; border-radius: 8px; padding: 20px; flex: 1; }
            .card h2 { margin-top: 0; }
            a { display: inline-block; background: #444; color: white; padding: 10px 15px; 
               text-decoration: none; border-radius: 4px; margin-top: 10px; }
            input { padding: 8px; width: 100%; box-sizing: border-box; margin-bottom: 10px; }
        </style>
    </head>
    <body>
        <h1>Media Recording Server</h1>
        <p>Enter a space name and choose which recorder to access:</p>
        
        <input type="text" id="spaceInput" placeholder="Enter space name (e.g. test)" value="test">
        
        <div class="container">
            <div class="card">
                <h2>Video Recorder</h2>
                <p>Record video from your device's camera</p>
                <a href="#" onclick="goTo('video')">Access Video Recorder</a>
            </div>
            
            <div class="card">
                <h2>Audio Recorder</h2>
                <p>Record audio from your device's microphone</p>
                <a href="#" onclick="goTo('audio')">Access Audio Recorder</a>
            </div>
        </div>

        <script>
            function goTo(type) {
                const space = document.getElementById('spaceInput').value || 'test';
                window.location.href = `/${type}/${space}`;
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn

    # Run the FastAPI app with Uvicorn
    uvicorn.run(app)
