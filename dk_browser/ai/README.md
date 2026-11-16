# DK AI: local-only prototype

This is an optional, bilingual English/Russian **development component**,
not yet the browser's native AI sidebar. No accounts, cloud providers,
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

**Usability:** The chat remembers only the language choice (English or Russian)
in browser local storage; it never stores messages there. Existing messages
change their role labels when the interface language changes. Press
**Ctrl+Enter** (or **Command+Enter**) to send while keeping Enter available
for multiline messages. **Export chat / Сохранить переписку** creates a
local text file only when clicked. **Clear chat / Очистить переписку**
forgets the session's messages; closing the page also discards them.

The service requires only Python's standard library. The browser UI sends
same-origin JSON to DK AI, and the backend contacts only the fixed loopback
Ollama address. Browser origin and Host headers are verified to mitigate
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
