// static/audio_recorder.js

let mediaStream = null;
let isRecording = false;
let currentRecorder = null;
let currentSessionId = null;
const CHUNK_DURATION_MS = 10000;  // 10 seconds per chunk
const audioPreview = document.getElementById('audioPreview');
const recordToggleButton = document.getElementById('recordToggle');
const statusDiv = document.getElementById('status');

// WebM format constants
const MIME_TYPE = 'audio/webm;codecs=opus';
const FILE_EXTENSION = 'webm';

function updateStatus(msg) {
  statusDiv.textContent = msg;
  console.log(msg);
}

// Toggle recording state
recordToggleButton.onclick = async () => {
  if (isRecording) {
    // Stop recording
    isRecording = false;
    updateStatus('Will stop after current segment…');
    
    // Visual feedback that stopping is in progress
    recordToggleButton.textContent = 'Stopping...';
    recordToggleButton.classList.remove('recording');
    recordToggleButton.classList.add('stopping');
    recordToggleButton.disabled = true;
  } else {
    // Start recording
    updateStatus('Requesting microphone access…');
    try {
      const constraints = {
        audio: true,
        video: false
      };
      mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
      
      if (audioPreview) {
        audioPreview.srcObject = mediaStream;
        audioPreview.play();
      }
      
      // Generate session ID in YYMMDD_HHMMSS format
      const now = new Date();
      currentSessionId = now.toISOString()
        .replace(/[-:]/g, '')
        .replace(/T/, '_')
        .replace(/\..+/, '')
        .slice(2); // Get YYMMDD_HHMMSS format
      
      updateStatus(`Microphone ready. Beginning session ${currentSessionId}…`);

      isRecording = true;
      recordToggleButton.textContent = 'Stop Recording';
      recordToggleButton.classList.add('recording');

      recordNextSegment();
    } catch (err) {
      updateStatus(`Error accessing microphone: ${err.message}`);
    }
  }
};

// Record one segment, then upload and recurse
function recordNextSegment() {
  if (!isRecording) {
    cleanupStream();
    recordToggleButton.textContent = 'Start Recording';
    recordToggleButton.classList.remove('recording');
    recordToggleButton.classList.remove('stopping');
    recordToggleButton.disabled = false;
    updateStatus('Recording fully stopped.');
    return;
  }

  // Check browser support for WebM
  const options = {};
  
  if (MediaRecorder.isTypeSupported(MIME_TYPE)) {
    options.mimeType = MIME_TYPE;
  } else {
    updateStatus(`Warning: ${MIME_TYPE} not supported, using browser default`);
  }
  
  const recorder = new MediaRecorder(mediaStream, options);
  currentRecorder = recorder;
  const chunks = [];
  const startTs = new Date().toISOString();  // mark beginning

  recorder.ondataavailable = e => {
    if (e.data && e.data.size > 0) chunks.push(e.data);
  };

  recorder.onstop = async () => {
    const endTs = new Date().toISOString();  // mark end
    const blob = new Blob(chunks, { type: recorder.mimeType || MIME_TYPE });
    const safeStartTs = startTs.replace(/[:.\-]/g,'');
    const safeEndTs = endTs.replace(/[:.\-]/g,'');
    const filename = `${safeStartTs}_${safeEndTs}.${FILE_EXTENSION}`;
    updateStatus(`Uploading segment ${filename} (${(blob.size/1024).toFixed(1)}KB)…`);

    try {
      const form = new FormData();
      form.append('file', blob, filename);
      form.append('start_ts', startTs);
      form.append('end_ts', endTs);
      form.append('session', currentSessionId);
      const res = await fetch(`/upload_chunk/${space}`, {
        method: 'POST',
        body: form
      });
      const info = await res.json();
      updateStatus(`Saved: ${info.path}`);
    } catch (err) {
      updateStatus(`Upload failed: ${err.message}`);
    }

    // proceed to the next segment immediately
    recordNextSegment();
  };

  recorder.start();  // no timeslice → full segment on stop
  updateStatus(`Recording segment for ${CHUNK_DURATION_MS/1000}s…`);

  // schedule stop of this segment
  setTimeout(() => {
    if (recorder.state !== 'inactive') recorder.stop();
  }, CHUNK_DURATION_MS);
}

// Release microphone when done
function cleanupStream() {
  if (mediaStream) {
    mediaStream.getTracks().forEach(t => t.stop());
    mediaStream = null;
  }
}

// Initialize UI
updateStatus("Ready. Click 'Start Recording' to begin.");
