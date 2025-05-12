# server.py
from fastapi import FastAPI, UploadFile, File, Path, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

# root directory for saves
save_rootdir = '/Users/thorwhalen/tmp/mv_video_saves'
os.makedirs(save_rootdir, exist_ok=True)

app = FastAPI()

# Enable CORS if front-end served elsewhere
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# Serve JS and other assets from ./static
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/{space}", response_class=HTMLResponse)
async def get_recorder(space: str = Path(..., description="Subfolder name")):
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Record to '{space}'</title>
      <style>
        body {{ font-family: Arial,sans-serif; max-width:600px; margin:20px auto; }}
        button {{ padding:10px 20px; margin:5px; font-size:16px; }}
        video {{ border:1px solid #ccc; width:100%; height:auto; }}
        #status {{ margin-top:10px; font-family:monospace; white-space:pre-wrap; }}
        #recordToggle {{ background-color: #4CAF50; color: white; }}
        #recordToggle.recording {{ background-color: #f44336; animation: blink 1s infinite; }}
        #recordToggle.stopping {{ background-color: #FF9800; animation: pulse 0.5s infinite; }}
        @keyframes blink {{ 
          50% {{ opacity: 0.5; }}
        }}
        @keyframes pulse {{ 
          0% {{ opacity: 1; }}
          50% {{ opacity: 0.7; }}
          100% {{ opacity: 1; }}
        }}
      </style>
    </head>
    <body>
      <h1>Recording to space: {space}</h1>
      <video id="preview" autoplay playsinline muted></video>
      <div>
        <button id="toggle">Use Front Camera</button>
        <button id="recordToggle">Start Recording</button>
      </div>
      <div id="status">Ready. Click 'Start Recording' to begin.</div>
      <script src="/static/recorder.js"></script>
      <script>const space = "{space}";</script>
    </body>
    </html>
    """
    return html


@app.post("/upload/{space}")
async def upload_frame(
    space: str = Path(..., description="Subfolder to save into"),
    file: UploadFile = File(...),
    start_ts: str = Form(...),
    end_ts: str = Form(...),
    session: str = Form(...),
):
    """
    Receives a video segment and saves it within session subfolder inside space folder.
    Session subfolder is named with the timestamp of when recording started.
    """
    # ensure space directory exists
    space_dirpath = os.path.join(save_rootdir, space)
    os.makedirs(space_dirpath, exist_ok=True)

    # ensure session subdirectory exists
    session_dirpath = os.path.join(space_dirpath, session)
    os.makedirs(session_dirpath, exist_ok=True)

    # The filename is already formatted correctly with start_ts and end_ts from the client
    path = os.path.join(session_dirpath, file.filename)

    contents = await file.read()
    with open(path, "wb") as f:
        f.write(contents)

    return {"status": "saved", "path": path}
