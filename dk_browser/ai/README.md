# DK AI: local-only prototype

The DK Browser source now includes a native toolbar entry **DK AI / ДК ИИ**
which opens `http://127.0.0.1:8766/` in a foreground tab. It does not
start the assistant process, install model weights, or send the current page's
contents. If the local service is not running the tab will show a normal
connection error. Start it manually using the command below.

This is an optional, bilingual English/Russian **development component**,
now linked from the native toolbar, but **not yet a native AI sidebar**. No accounts, cloud providers,
telemetry, model downloads, browser tab reads, system commands or agent tools
are implemented.

1. Install the **Ollama local inference runtime** separately, using its
   official instructions, and start it on `127.0.0.1:11434`.
2. **You** choose and install any suitable compatible Ollama chat model.
   This project does not download one. GigaChat is a future benchmark
   candidate, not a proven Ollama compatibility claim.
3. From the checkout root, run:

   ```bash
   python3 -m dk_browser.ai --open
   ```

4. The interface opens at `http://127.0.0.1:8766` and shows available models.
   Chat messages are only submitted to the chosen local model.

### Optional local OpenAI-compatible model server

DK AI also works with a separately started OpenAI-compatible local server
(such as a compatible vLLM setup). Bind that server to `127.0.0.1:8000`
and start DK AI with:

```bash
python3 -m dk_browser.ai --backend openai --model-port 8000 --open
```

This backend reads `GET /v1/models` and uses
`POST /v1/chat/completions`. Only a **local loopback port** can be selected.
The prototype has no cloud account, API key, internet server URL, or automatic
model installation. Compatibility with GigaChat weights or a specific model
server must be tested before making such a claim.

**Official artwork:** The assistant serves the approved Latin **DK** and Cyrillic
**ДК** imperial icons directly from `assets/images`. Both its header and
tab favicon switch with the English/Russian language setting. The master
images stay in their original folder, without duplicate image files.

**Usability:** The chat remembers only the language choice (English or Russian)
in browser local storage; it never stores messages there. Existing messages
change their role labels when the interface language changes. Press
**Ctrl+Enter** (or **Command+Enter**) to send while keeping Enter available
for multiline messages. **Export chat / Сохранить переписку** creates a
local text file only when clicked. **Clear chat / Очистить переписку**
forgets the session's messages; closing the page also discards them.

The service requires only Python's standard library. The browser UI sends
same-origin JSON to DK AI, and the backend contacts only the fixed loopback
Ollama or OpenAI-compatible model-service address. Browser origin and Host headers are verified to mitigate
cross-site submissions and DNS rebinding. Input size, response size, and
message count are bounded. The page uses text-only DOM updates and strict
CSP headers; model responses are not interpreted as executable markup.

**Important privacy limitation:** Any application on the same machine may
connect to loopback services, and Ollama might independently log or process
requests according to your local configuration. No encryption or per-user
authentication is implemented on this prototype. Do not expose either
service outside the host, forward its ports, or use it for secret data without
an additional security review. DK AI never writes transcripts to disk.

Use `python3 -m unittest discover -s dk_browser/tests` for local unit tests.
No GitHub Actions, browser executable, or installation package is created.

Future releases may add a **permissioned** native sidebar, optional model
management, and tested Russian-first model support. The current prototype
does not claim Alice AI-level intelligence.
