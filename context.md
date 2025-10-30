# Silent Screenshot → GPT → Local Store (Cross-platform) — Project Summary

## One-line purpose
A small background Python app (Windows + macOS) that captures a full-screen screenshot when a global hotkey is pressed, sends the image to the ChatGPT API for analysis, and stores the API response locally — all silently (no UI/popups).

---

## Metadata
- **Project name:** silent-shot-gpt  
- **Platforms:** Windows, macOS (Intel + Apple Silicon)  
- **Python:** >= 3.10 (pyinstaller-friendly)  
- **Primary libs:** `mss` (capture), `pynput` (global hotkey), `openai` or simple `requests` (API), `sqlite3` or JSON (storage), `Pillow` (optional compression), `tempfile`  
- **Packaging:** `pyinstaller` (or native bundler to produce `.exe` / `.app`)  
- **Trigger:** user presses a global hotkey (default `Ctrl+Alt+S` or `Cmd+Ctrl+S` on macOS)  
- **Privacy model:** images & responses stored locally in encrypted or access-controlled DB/file (developer to choose)

---

## Behavior / Flow (step-by-step)
1. App runs in background/daemon with no visible UI.  
2. User presses global hotkey. App debounces to prevent duplicate triggers.  
3. Capture full-screen screenshot silently (no visible flash or system notifications).  
4. Optionally compress/resize image if size > API limits.  
5. Convert image to an allowed format for the ChatGPT image-capable endpoint (data URI / multipart).  
6. Send request to ChatGPT API with a short system/user prompt describing the task (e.g., "Analyze this screenshot and return a concise JSON with sections: observed text, UI elements, suggestions").  
7. Receive response and save raw response + metadata (timestamp, image path, model name, request/response id) into local storage (SQLite recommended).  
8. Clean up temp images periodically. No UI displayed. (Later: add an encrypted vault or optional viewer.)

---

## Constraints & Important Platform Notes
- **macOS permissions:** Screen Recording permission must be requested (System Preferences → Security & Privacy → Screen Recording). Accessibility permissions needed for global hotkeys may be required.  
- **Windows:** Running as normal user usually suffices; avoid libraries that require elevation.  
- **No UI/notifications:** Avoid calls to notification libraries — keep completely silent.  
- **API limits & privacy:** Respect OpenAI file size limits and rate limits. Sensitive screenshots should be treated carefully — consider local-only storage encryption.  
- **Debounce:** Enforce a minimum inter-trigger delay (e.g., 500 ms) to avoid accidental floods.  
- **Bundle size:** If packaging, keep dependencies minimal to keep binary small.

---

## Default developer assumptions (state these when feeding to a tool)
- The user wants *full-screen* captures by default (not window-only) unless instructed.  
- OpenAI API key will be supplied via environment variable `OPENAI_API_KEY`.  
- Silent operation is required — no system tray icon, no toasts.  
- App must run on both Windows and macOS from the same Python codebase with minimal platform branching.

---

## Baseline Implementation Plan (📘) — 5 steps with exact levers
1. **Hotkey (cross-platform):** implement with `pynput.keyboard.HotKey` using `listener` pattern.  
   - Lever: `pynput` for macOS & Windows; check for macOS Accessibility permission.  
2. **Screenshot:** use `mss` grabbing `sct.monitors[1]` for the primary/full screen. Save temporarily to `tempfile.gettempdir()`.  
   - Lever: `mss.tools.to_png(...)`; optionally pipe to `PIL.Image` for compression.  
3. **Image -> API:** read bytes and send as `data:image/png;base64,...` or multipart. Use `openai.chat.completions.create` (image-capable model) or `requests` if library not available.  
   - Lever: `base64.b64encode` and send inside message payload per API contract.  
4. **Store:** SQLite DB table `logs(timestamp, image_path, model, response, metadata_json)`. Use WAL mode and parameterized queries.  
   - Lever: `sqlite3` + `PRAGMA journal_mode=WAL` for concurrency.  
5. **Packaging & silent run:** `pyinstaller --noconsole --onefile app.py` (macOS: create `.app` bundle). Ensure startup/daemon setup is offloaded to user-specific instructions.

---

## Divergent Ideas (🧪) — non-obvious directions (each: Why / When it fails / Quick test)
1. **Queue + Batch Sync**
   - **Why:** Handles offline mode and rate limits; prevents blocking hotkey.  
   - **When it fails:** If immediate feedback is required; queue growth if storage not managed.  
   - **Quick test:** Trigger 50 screenshots rapidly, ensure local queueing and later successful upload.

2. **On-device lightweight inference (OCR + heuristic) before sending**
   - **Why:** Strip PII, reduce unnecessary uploads by pre-filtering screenshots (e.g., blank screens).  
   - **When it fails:** Complex UIs may be misclassified; increases local dependency size.  
   - **Quick test:** Run Tesseract/OCR on screenshot; skip upload if no words found.

3. **Selective-region capture by holding modifier**
   - **Why:** Smaller payloads, user-controlled scope.  
   - **When it fails:** More complex UX (but keyboard-only ROI selection possible).  
   - **Quick test:** Implement a second hotkey `Ctrl+Alt+R` that captures active window bounds.

4. **Encrypted local store**
   - **Why:** Protects sensitive screenshots/responses.  
   - **When it fails:** Adds key-management complexity and user friction.  
   - **Quick test:** Save DB encrypted with a passphrase and verify read/write.

---

## Pitfalls & Red-flags
- **macOS permission denial**: App will silently fail to capture if Screen Recording permission is not granted. Provide clear developer docs to request/guide these permissions during installation.  
- **Hotkey conflicts**: Choose sensible default and allow reconfiguration.  
- **Large images**: API rejects large inputs — resize/compress before upload.  
- **Privacy leakage**: Default behaviour uploads full desktop; warn users and consider explicit consent/opt-in.  
- **Background process termination**: On macOS, the OS may throttle or terminate background processes; prefer a user agent approach or a scheduled agent if needed.

---

## Prioritized Next Actions (P1 / P2 / P3)
- **P1** (implement & verify):  
  1. Minimal app: `pynput` hotkey + `mss` screenshot saved to temp. Test both Windows & macOS.  
  2. Local storage: log image path + timestamp in SQLite.
- **P2** (integration):  
  1. Hook OpenAI API: send screenshot, save raw response. Add image size check & compression.  
  2. Add debounce and error handling/logging (rotate logs).  
- **P3** (hardening + packaging):  
  1. Add macOS permission guide, optional encryption, and package using `pyinstaller`.  
  2. Add config file for hotkey, storage location, and model/prompt templates.

---

## 48-hour Action Checklist
- [ ] Create repo + `pyproject`/`requirements.txt` (include `mss`, `pynput`, `openai`, `Pillow`).  
- [ ] Implement `capture_and_save()` using `mss` and save to `tempfile`. Test on both OSes.  
- [ ] Implement hotkey listener with debounce and test accidental double-triggers.  
- [ ] Implement SQLite logger and ensure entries are written.  
- [ ] Wire a stubbed API call (no real key) that echoes back a deterministic response; confirm persistence.  
- [ ] Document macOS Screen Recording + Accessibility steps in `README.md`.

---

## Minimal example prompt to send with each image (tweakable)
> "You are an assistant that analyzes screenshots. Return a short JSON containing `{ "summary": "...", "visible_text": "...", "notable_UI_elements": ["..."], "sensitivity": "low|medium|high" }` — keep JSON only."

---

## Useful dev notes (quick)
- Use `tempfile.NamedTemporaryFile(delete=False, suffix=".png")` to safely create images.  
- Compress with Pillow: `Image.open(path).thumbnail((1920,1080))` then save with `optimize=True`.  
- Use environment variable `OPENAI_API_KEY`; never hardcode keys.  
- Consider `PRAGMA journal_mode=WAL` and `conn.execute("PRAGMA synchronous=NORMAL")` for SQLite speed.

---

## Contact/Context snippet (1–2 lines to paste into other tools)
`silent-shot-gpt` — background Python app that captures a full-screen screenshot on a global hotkey (Windows + macOS), sends the image to a ChatGPT image-capable endpoint for analysis, and stores the response locally (SQLite), prioritized for silent operation and minimal dependencies.

