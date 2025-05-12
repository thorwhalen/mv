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
        @keyframes blink {{ 
          50% {{ opacity: 0.5; }}
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
    ts: str = Form(...),
):
    """
    Receives a video segment and names it with the client-provided timestamp.
    """
    # ensure directory exists
    dirpath = os.path.join(save_rootdir, space)
    os.makedirs(dirpath, exist_ok=True)
    # sanitize ts for filename
    safe_ts = ts.replace(':', '').replace('-', '').replace('.', '')
    filename = f"{safe_ts}_{file.filename}"
    path = os.path.join(dirpath, filename)
    contents = await file.read()
    with open(path, "wb") as f:
        f.write(contents)
    return {"status": "saved", "path": path}
