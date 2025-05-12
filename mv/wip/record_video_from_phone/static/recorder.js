// static/recorder.js

const preview      = document.getElementById('preview');
const startButton  = document.getElementById('start');
const stopButton   = document.getElementById('stop');
const toggleButton = document.getElementById('toggle');
const statusDiv    = document.getElementById('status');

let useFront = false;
let isRecording = false;
let mediaStream = null;
let currentRecorder = null;

// Chunk duration in milliseconds
const CHUNK_DURATION_MS = 5000;  // e.g. 5000ms = 5s

function updateStatus(msg) {
  statusDiv.textContent = msg;
  console.log(msg);
}

// Toggle between back and front camera
toggleButton.onclick = () => {
  useFront = !useFront;
  toggleButton.textContent = useFront
    ? 'Use Back Camera'
    : 'Use Front Camera';
  updateStatus(`Next segments will use the ${useFront ? 'front' : 'back'} camera.`);
};

// Start recording loop of chunks
startButton.onclick = async () => {
  if (isRecording) return;
  updateStatus('Requesting camera access…');
  try {
    const constraints = {
      video: { facingMode: useFront ? 'user' : 'environment' },
      audio: false
    };
    mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
    preview.srcObject = mediaStream;
    await preview.play();
    updateStatus('Camera ready. Starting segment recording…');

    isRecording = true;
    startButton.disabled = true;
    stopButton.disabled  = false;

    recordNextSegment();
  } catch (err) {
    updateStatus(`Error getting camera: ${err.message}`);
  }
};

// Stop the recording loop
stopButton.onclick = () => {
  if (!isRecording) return;
  isRecording = false;
  updateStatus('Stopping recording after current segment…');
  stopButton.disabled = true;
};

// Record one segment, then upload and recurse
function recordNextSegment() {
  if (!isRecording) {
    cleanupStream();
    startButton.disabled = false;
    updateStatus('Recording stopped.');
    return;
  }

  const recorder = new MediaRecorder(mediaStream, { mimeType: 'video/webm; codecs=vp8' });
  currentRecorder = recorder;
  const chunks = [];

  recorder.ondataavailable = event => {
    if (event.data && event.data.size > 0) {
      chunks.push(event.data);
    }
  };

  recorder.onstop = async () => {
    const blob = new Blob(chunks, { type: 'video/webm' });
    const timestamp = new Date().toISOString().replace(/[:.]/g, '');
    const filename = `${timestamp}.webm`;
    updateStatus(`Uploading segment ${filename} (${(blob.size/1024).toFixed(1)} KB)…`);

    try {
      const form = new FormData();
      form.append('file', blob, filename);
      const res = await fetch(`/upload/${space}`, { method: 'POST', body: form });
      const info = await res.json();
      updateStatus(`Segment saved: ${info.path}`);
    } catch (err) {
      updateStatus(`Upload failed: ${err.message}`);
    }

    // Immediately record the next segment
    recordNextSegment();
  };

  // Start and schedule stop
  recorder.start();
  updateStatus(`Recording segment for ${CHUNK_DURATION_MS/1000}s…`);
  setTimeout(() => {
    if (recorder.state !== 'inactive') {
      recorder.stop();
    }
  }, CHUNK_DURATION_MS);
}

// Stop all tracks and release camera
function cleanupStream() {
  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop());
    mediaStream = null;
    currentRecorder = null;
  }
}

// Initialize UI state
stopButton.disabled = true;
toggleButton.textContent = 'Use Front Camera';
updateStatus("Ready. Click 'Start Recording' to begin.");