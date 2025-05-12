// static/recorder.js

let mediaRecorder;
const preview      = document.getElementById('preview');
const startButton  = document.getElementById('start');
const stopButton   = document.getElementById('stop');
const toggleButton = document.getElementById('toggle');
const statusDiv    = document.getElementById('status');

let useFront = false;

function updateStatus(msg) {
  statusDiv.textContent = msg;
  console.log(msg);
}

// Toggle between back (environment) and front (user) camera
toggleButton.onclick = () => {
  useFront = !useFront;
  toggleButton.textContent = useFront
    ? 'Use Back Camera'
    : 'Use Front Camera';
  updateStatus(`Will use ${useFront ? 'front' : 'back'} camera next.`);
};

// Start recording
startButton.onclick = async () => {
  try {
    updateStatus("Requesting camera access...");
    const constraints = {
      video: { facingMode: useFront ? 'user' : 'environment' },
      audio: false
    };
    const stream = await navigator.mediaDevices.getUserMedia(constraints);
    preview.srcObject = stream;
    await preview.play();
    updateStatus("Camera access granted. Recording...");

    mediaRecorder = new MediaRecorder(stream, { mimeType: 'video/webm' });
    mediaRecorder.ondataavailable = async (event) => {
      // console.log("Blob size:", event.data.size);
      if (event.data && event.data.size > 0) {
        updateStatus(`Uploading chunk (${(event.data.size/1024).toFixed(1)} KB)...`);
        const form = new FormData();
        form.append('file', event.data, 'chunk.webm');
        try {
          const res = await fetch(`/upload/${space}`, { method: 'POST', body: form });
          const result = await res.json();
          updateStatus(`Saved: ${result.path}`);
        } catch (err) {
          updateStatus(`Upload error: ${err.message}`);
        }
      }
    };

    mediaRecorder.start(1000);  // chunk every 1 second
    startButton.disabled = true;
    stopButton.disabled  = false;
  } catch (err) {
    updateStatus(`Error: ${err.message}`);
    console.error(err);
  }
};

// Stop recording
stopButton.onclick = () => {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
    preview.srcObject.getTracks().forEach(t => t.stop());
    updateStatus("Recording stopped.");
    startButton.disabled = false;
    stopButton.disabled  = true;
  }
};

// Initialize buttons
stopButton.disabled = true;