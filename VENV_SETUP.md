
## `VENV_SETUP.md` — Python Virtual Environment (PowerShell / Windows)

### 1. Verify Python Is Installed

```powershell
python --version
```

If this fails:

```powershell
py --version
```

---

### 2. Create Virtual Environment

From your project root:

```powershell
python -m venv .venv
```

This creates:

```
project/
 ├─ .venv/
 ├─ app.py
 ├─ requirements.txt
```

---

### 3. Allow PowerShell Scripts (One-Time)

If activation is blocked:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

---

### 4. Activate Virtual Environment

```powershell
.\.venv\Scripts\Activate.ps1
```

You should now see:

```
(.venv)
```

in your terminal.

---

### 5. Upgrade pip (Recommended)

```powershell
python -m pip install --upgrade pip
```

---

### 6. Install Dependencies

```powershell
pip install -r requirements.txt
```

---

### 7. Verify Installation

```powershell
python -c "import flask; print('Flask OK')"
```

---

### 8. Run Your Project

```powershell
python app.py
```

---

### 9. Deactivate When Done

```powershell
deactivate
```

---

## Common Fixes

### ❌ `python was not found`

Use:

```powershell
py -m venv .venv
```

---

### ❌ `Activate.ps1 is disabled`

Run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

---

### ❌ Flask Installed but Not Importing

You are not in the venv. Activate it again:

```powershell
.\.venv\Scripts\Activate.ps1
```

Then verify:

```powershell
where python
```

Should point to:

```
.venv\Scripts\python.exe
```

---

## Best Practices

* ✅ Always commit **`requirements.txt`**, not `.venv`
* ✅ Always activate venv **before running**
* ❌ Never install packages globally for project use
* ✅ Use `Pathlib` for file paths (avoids venv path bugs)
* ✅ Backup JSON before writes

---
