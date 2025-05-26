## Accessing the media_recording app

A simple FastAPI + web front-end proof-of-concept for recording video from a phone or browser and streaming chunks to a local server.

### Locally

From your development machine. Open in your browser:

```bash
http://localhost:8000/video/<space>  # For video recording
http://localhost:8000/audio/<space>  # For audio recording
```

e.g. http://localhost:8000/video/test


### Remotely

This requires doing more setup (see the TLS section)

From a phone or other device on the same LAN

In Safari/Chrome, navigate to:

```
https://IP_ADDRESS:8000/video/<space>  # For video recording
https://IP_ADDRESS:8000/audio/<space>  # For audio recording
```

## TLS: Generating & trusting a local TLS certificate


By default, browsers only allow getUserMedia() on secure contexts (HTTPS or localhost). To access your server from a phone on the same LAN, you must serve over HTTPS with a trusted cert.

### Install mkcert

```bash
brew install mkcert nss
mkcert -install
```

### Create certs for your LAN IP

Find your current LAN IP:

```bash
ipconfig getifaddr en0    # e.g. 192.168.1.80
```

Generate a certificate valid for that IP and localhost:

```bash
mkdir -p certs
mkcert -cert-file certs/cert.pem -key-file certs/key.pem 192.168.1.80 localhost
```

### Trust the mkcert root on the remote device (e.g. browser, phone...)

	•	Locate the root CA (mkcert -CAROOT), e.g. ~/.local/share/mkcert/rootCA.pem.
	•	Email or AirDrop it to your device.
	•	On iOS: tap the attachment, install the profile, then go to Settings → General → About → Certificate Trust Settings and enable full trust for “mkcert development CA.”


Running the server

For example, if your cert and key files are in `certs/`:

```python
uvicorn media_recording_server:app \
  --host 0.0.0.0 --port 8000 \
  --ssl-certfile=certs/cert.pem \
  --ssl-keyfile=certs/key.pem
```

	•	--host 0.0.0.0 listens on all interfaces.
	•	The server will now respond on HTTPS at port 8000.


## Tips

If your LAN IP changes, re-run mkcert for the new address:

```bash
mkcert -cert-file certs/cert.pem -key-file certs/key.pem NEW_IP localhost
```

## TLS Alternative

For quick demos without TLS setup, consider using ngrok:

```bash
ngrok http 8000
```

then visit the generated https://*.ngrok.io/<space> URL on any device.
