# 🏗️ AI Architecture Designer
**Convert requirements into software architecture — powered by Groq

---

## Setup (Windows + VS Code)

### 1. Get a free Groq API key
Go to **https://console.groq.com/keys** → sign in → **Create API Key** → copy it.

### 2. Open the project in VS Code
Extract the zip → right-click the `ai_architect` folder → **Open with Code**.

### 3. Run the setup script
Open a terminal in VS Code (**Ctrl + `**) and run:
```cmd
setup.bat
```
This creates a virtual environment, installs dependencies, and generates a `.env` file for you.

### 4. Add your API key
Open the `.env` file created in step 3 and replace:
```
GROQ_API_KEY=your-groq-api-key-here
```
with your real key, then save.

### 5. Start the app
```cmd
start_app.bat
```
Opens at **http://localhost:8501**

---

## Manual setup (alternative to setup.bat)
```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
REM edit .env and add your key
streamlit run app.py
```

---

## Notes
- The API key lives only in `.env` and is never shown or requested in the app's UI.
- 4 sample requirement documents are bundled under `sample_docs/` for quick testing.
- Exports: Markdown, JSON, PDF, DOCX, and raw Mermaid diagram files.

## Troubleshooting

| Problem | Fix |
|---|---|
| `python` not found | Reinstall Python, check "Add to PATH" |
| `activate` fails in PowerShell | Run `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| App says "not configured" | Your `.env` key is still the placeholder — edit and save it |
| Port already in use | `streamlit run app.py --server.port 8502` |
