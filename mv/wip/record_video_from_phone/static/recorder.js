// static/recorder.js

let mediaStream       = null;
let isRecording       = false;
let currentRecorder   = null;
const CHUNK_DURATION_MS = 5000;   // adjust chunk size here

const preview      = document.getElementById('preview');
const toggleButton = document.getElementById('toggle');
const recordToggleButton = document.getElementById('recordToggle');
const statusDiv    = document.getElementById('status');

let useFront = false;

function updateStatus(msg) {
  statusDiv.textContent = msg;
  console.log(msg);
}

// Toggle front/back camera
toggleButton.onclick = () => {
  useFront = !useFront;
  toggleButton.textContent = useFront
    ? 'Use Back Camera'
    : 'Use Front Camera';
  updateStatus(`Next segments will use the ${useFront ? 'front' : 'back'} camera.`);
};

// Toggle recording state
recordToggleButton.onclick = async () => {
  if (isRecording) {
    // Stop recording
    isRecording = false;
    updateStatus('Will stop after current segment…');
    recordToggleButton.disabled = true;
  } else {
    // Start recording
    updateStatus('Requesting camera access…');
    try {
      const constraints = {
        video: { facingMode: useFront ? 'user' : 'environment' },
        audio: false
      };
      mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
      preview.srcObject = mediaStream;
      await preview.play();
      updateStatus('Camera ready. Beginning segment capture…');

      isRecording = true;
      recordToggleButton.textContent = 'Stop Recording';
      recordToggleButton.classList.add('recording');

      recordNextSegment();
    } catch (err) {
      updateStatus(`Error accessing camera: ${err.message}`);
    }
  }
};

// Record one segment, then upload and recurse
function recordNextSegment() {
  if (!isRecording) {
    cleanupStream();
    recordToggleButton.textContent = 'Start Recording';
    recordToggleButton.classList.remove('recording');
    recordToggleButton.disabled = false;
    updateStatus('Recording fully stopped.');
    return;
  }

  const recorder = new MediaRecorder(mediaStream, { mimeType: 'video/webm; codecs=vp8' });
  currentRecorder = recorder;
  const chunks = [];
  const startTs = new Date().toISOString();  // mark beginning

  recorder.ondataavailable = e => {
    if (e.data && e.data.size > 0) chunks.push(e.data);
  };

  recorder.onstop = async () => {
    const blob = new Blob(chunks, { type: 'video/webm' });
    const filename = `${startTs.replace(/[:.\-]/g,'')}.webm`;
    updateStatus(`Uploading segment ${filename} (${(blob.size/1024).toFixed(1)}KB)…`);

    try {
      const form = new FormData();
      form.append('file', blob, filename);
      form.append('ts', startTs);
      const res = await fetch(`/upload/${space}`, {
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

// Release camera when done
function cleanupStream() {
  if (mediaStream) {
    mediaStream.getTracks().forEach(t => t.stop());
    mediaStream = null;
  }
}

// Initialize UI
toggleButton.textContent = 'Use Front Camera';
updateStatus("Ready. Click 'Start Recording' to begin.");