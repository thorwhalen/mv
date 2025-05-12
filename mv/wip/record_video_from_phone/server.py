# server.py
from fastapi import FastAPI, UploadFile, File, Path
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from datetime import datetime

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
app.mount(
    "/static", StaticFiles(directory="static"), name="static"
)

@app.get("/{space}", response_class=HTMLResponse)
async def get_recorder(space: str = Path(..., description="Subfolder name")):
    """
    Serves an HTML page with embedded JS that captures video (front/back toggle)
    and uploads to /upload/{space}.
    """
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Record to '{space}'</title>
        <style>
            body {{ 
                font-family: Arial, sans-serif; 
                max-width: 600px; 
                margin: 0 auto; 
                padding: 20px;
            }}
            button {{
                padding: 10px 20px;
                margin: 10px 5px;
                font-size: 16px;
            }}
            video {{
                border: 1px solid #ccc;
                max-width: 100%;
                height: auto;
            }}
            #status {{
                margin-top: 10px;
                font-family: monospace;
                white-space: pre-wrap;
            }}
        </style>
    </head>
    <body>
      <h1>Recording to space: {space}</h1>
      <video id="preview" autoplay playsinline muted width="320" height="240"></video>
      <div>
        <button id="toggle">Use Front Camera</button>
        <button id="start">Start Recording</button>
        <button id="stop">Stop Recording</button>
      </div>
      <div id="status">Ready. Click 'Start Recording' to begin.</div>
      <script src="/static/recorder.js"></script>
      <script>
        const space = "{space}";
      </script>
    </body>
    </html>
    """
    return html

@app.post("/upload/{space}")
async def upload_frame(
    space: str = Path(..., description="Subfolder to save into"),
    file: UploadFile = File(...),
):
    """
    Receives a video chunk and writes it to disk under save_rootdir/space with ms timestamp.
    """
    # ensure directory exists
    dirpath = os.path.join(save_rootdir, space)
    os.makedirs(dirpath, exist_ok=True)
    # timestamp with milliseconds
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S.%f")[:-3]
    filename = f"{ts}_{file.filename}"
    path = os.path.join(dirpath, filename)
    contents = await file.read()
    with open(path, "wb") as f:
        f.write(contents)
    return {"status": "saved", "path": path}