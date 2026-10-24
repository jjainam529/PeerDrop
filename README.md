# PeerDrop

PeerDrop is a browser-based, peer-to-peer file sharing tool. The sender picks a file, optionally converts it to another format, and gets a 4-digit code. Up to 10 receivers can enter the code and download the file directly from the sender's browser. The file is never stored on a server, and the code expires after 4 minutes.

An optional converter service handles conversions that need a real layout engine, such as Word and PowerPoint to PDF and PDF to Word.

## Features

- Direct browser-to-browser transfer with WebRTC (via PeerJS)
- 4-digit sharing code, valid for 4 minutes and up to 10 receivers
- Per-receiver progress bars and a "Stop sharing now" button
- Drag-and-drop or click-to-browse file selection
- Conversions:
  - PDF to TXT, DOCX (server), PNG, JPG
  - Word (.docx) to PDF (in browser or server), TXT, PNG/JPG is not supported
  - Images to PDF, PNG, JPG
  - Text files (TXT, CSV, MD, JSON, XML, HTML) to PDF, DOCX, PPTX, TXT
  - Office files (DOC, ODT, RTF, PPT, PPTX, ODP, XLS, XLSX, ODS) to PDF (server only)
- Works on phones and desktops

## Project structure
index.html Landing page (choose Send or Receive)
send.html Sender page: pick file, convert, share code
recieve.html Receiver page: enter code, download file
style.css Shared styles
logo1.png, *.png Images used by the pages
render.yaml Render.com blueprint for the converter service
converter/
app.py FastAPI converter service (LibreOffice, pdf2docx, OCR)
Dockerfile Container image for the converter


## How it works

1. **Sender** (`send.html`) prepares the file, converting it in the browser or on the converter server if needed.
2. The sender's browser registers a random 4-digit ID with the PeerJS signalling server.
3. **Receivers** (`recieve.html`) connect to that ID. WebRTC uses STUN to find a route, and TURN relay servers when a direct link is blocked.
4. The file is streamed over a data channel in 64 KB chunks.

Because the transfer is peer-to-peer, both people need to have their browser tab open until the transfer finishes.

## Network setup (TURN)

Direct connections fail on some networks, such as mobile data and some office or college Wi-Fi. In those cases a TURN relay is needed.

- The default TURN servers come from openrelay.metered.ca. They are shared and often unreliable.
- For reliable transfers, create a free TURN app at [metered.ca](https://www.metered.ca), copy the `iceServers` list, and paste it into `MY_ICE_SERVERS` in `send.html`.

```js
const MY_ICE_SERVERS = [
  { urls: "turn:standard.relay.metered.ca:80", username: "xxxx", credential: "yyyy" },
  { urls: "turn:standard.relay.metered.ca:443", username: "xxxx", credential: "yyyy" }
];
```

## Converter server

The converter is only needed for Office-to-PDF and PDF-to-DOCX conversions. The rest of the app works without it.

**Endpoints**

- `GET /health`: returns `{"ok": true}`. The frontend calls it when the page loads to wake the server.
- `POST /convert?to=pdf|docx`: accepts a multipart `file` upload and returns the converted file.
  - `to=pdf` accepts doc, docx, odt, rtf, txt, ppt, pptx, odp, xls, xlsx, ods, csv.
  - `to=docx` accepts pdf. Image-only PDFs are OCR'd first.
- Limits: 25 MB per file. Uploaded and converted files are deleted after the response is sent.

**Environment variables**

| Variable | Default | Purpose |
|---|---|---|
| `ALLOWED_ORIGINS` | `*` | Comma-separated list of origins allowed by CORS |
| `MAX_JOBS` | `1` | Conversions run at the same time (the free Render plan has 512 MB RAM) |
| `PORT` | `8000` | Port the server listens on |

**Deploying on Render**

1. Push this repo to GitHub.
2. In Render, create a new Blueprint from the repo. `render.yaml` sets up the Docker service from `converter/Dockerfile`.
3. Copy the service URL and set it as `CONVERTER_URL` near the top of `send.html`.

Free Render services sleep after inactivity. The first conversion can take up to a minute while the server wakes up.

**Running locally**

```bash
cd converter
docker build -t peerdrop-converter .
docker run -p 8000:8000 peerdrop-converter
```

Then set `CONVERTER_URL = "http://localhost:8000"` in `send.html`.

## Hosting the frontend

The HTML files are static. Serve the repository root from any static host, such as GitHub Pages, Netlify, or Cloudflare Pages. Keep `index.html`, `send.html`, `recieve.html`, `style.css`, and the images together in the same folder.

## Libraries used (loaded from CDNs)

- PeerJS 1.5.4 (WebRTC connections)
- pdf.js 3.11.174 (reading PDFs)
- jsPDF 2.5.1 (creating PDFs from images and text)
- docx 8.5.0 (creating Word files)
- pptxgenjs 3.12.0 (creating PowerPoint files)
- mammoth 1.8.0 (reading Word files)
- JSZip 3.10.1 (reading .docx internals)
- html2pdf.js 0.10.1 (Word to PDF in the browser)

## Known limitations

- Both sender and receiver must keep their tab open during the transfer.
- In-browser conversions keep only the text. Layout, fonts and images are lost, except for image-to-PDF and Word-to-PDF, which render the page.
- Scanned PDFs have no text to extract in the browser. Use the server conversion for those.
- Without a working TURN server, transfers between some networks will fail.

© Jainam Jain. All rights reserved.
