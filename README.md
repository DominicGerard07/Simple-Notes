# 📝 SimpleNotes - Flask Note-Taking Web Application

A clean, responsive, and intuitive note-taking web application built with **Python 3**, **Flask**, and **SQLite**.

---

## ✨ Features

- **User Accounts & Multi-Tenant Privacy**:
  - **Individual Accounts**: Secure user registration and login with salted password hashing (`werkzeug.security`).
  - **Strict Data Isolation**: Each user has their own private notes, folders, and tags. Users cannot see, modify, or search across other users' data.
  - **Personal Home Folder**: Every user automatically receives their own default `Home` folder upon account creation.
  - **Quick Demo Account**: Pre-configured `demo` account (`demo` / `demo123`, email: `demo@example.com`) for immediate testing.
- **Password Reset via Email Verification Code**:
  - **Secure 6-Digit Codes**: Users can reset forgotten passwords by requesting a time-limited (15 min) verification code sent to their registered email address.
  - **Production SMTP Ready**: Works out of the box with standard SMTP servers (Gmail, SendGrid, Mailgun, Amazon SES, or custom mail transfer agents) via standard environment variables.
  - **Local Development / Offline Fallback**: When no SMTP credentials are configured, the reset code is securely logged to the console and displayed in the UI banner for zero-setup local development and evaluation.
- **Folder Structure & Hierarchical Subfolders**:
  - **Home Folder**: Pre-configured default space for general notes and quick thoughts (`parent_id = NULL`).
  - **Nested Subfolders**: Create folders inside folders to organize complex subjects, subcategories, or projects (e.g., *Work / Projects / Sprint 1*, *Computer Science / Python*).
  - **Visual Tree Guide Lines**: Directory tree sidebar displaying connecting branch lines (`├──`, `└──`) and vertical guide spines linking subfolders clearly with their parent folders.
  - **Hover Action**: Quick `+` button on any folder in the sidebar to instantly create a nested subfolder inside it.
  - **Safe Recursive Deletion**: Deleting any folder (root or nested) safely cascades all notes in that folder and its descendant subfolders to the **Home** folder—guaranteeing zero data loss.
  - **Folder Assignment & Breadcrumbs**: Assign notes to any subfolder from the note editor dropdown or filter by folder pill badge on cards with full path tooltips.
- **CRUD Operations**: Create, read, edit, and delete notes effortlessly.
- **Fluid FLIP Morphing Animations**: Seamless expanding and closing morph transitions calculated with precise bounding-box offsets (`top-left` origin FLIP math) and synchronized content fade, smoothly expanding from the card box into the full editor modal and collapsing back cleanly into the card box.
- **Markdown & Checklists**: Live markdown preview with support for bold, italic, code blocks, lists, interactive task checklists (`- [ ] task`), and real-time visual progress bars tracking task completion when checkboxes are ticked.
- **Modern Rounded Design**: Soft rounded edges across cards, modals, buttons, pill badges, and inputs.
- **Organization**:
  - **Pinning**: Pin key notes to keep them visible at the top.
  - **High-Contrast Pop Colors**: Categorize visually with punchy, high-contrast colors (Default, Blue, Green, Amber, Rose, Purple).
  - **Tags**: Multi-tagging with count badges and sidebar tag filtering.
- **Universal Search & Sort**:
  - **Universal Search across all folders & subfolders**: Instant debounced search querying across titles, content, tags, folder names, and nested subfolder paths (`Work / Projects / Sprint 1`).
  - **Subfolder Inclusivity**: Results from inside subfolders are surfaced universally, with note cards displaying full folder path pills.
  - **Quick Scope Toggle**: Easily switch between searching universally across all folders or restricting scope to the active folder and its subfolders.
  - Sort by Recently Updated, Oldest Updated, Recently Created, Oldest Created, or Title (A-Z / Z-A).
  - Switch between Card Grid and List layout views.
- **Dark / Light Mode**: Beautiful dark and light themes with preference saved in `localStorage`.
- **Keyboard Shortcuts**:
  - `Ctrl + N` / `Cmd + N`: Create a new note.
  - `/` or `Ctrl + K`: Jump to search bar.
  - `Ctrl + S`: Save note from within the editor.
  - `Escape`: Close open modal.
- **Data Portability**:
  - Export all notes as a JSON backup (`notes_backup.json`).
  - Import JSON backups to restore notes.
  - Single-note download as Plain Text (`.txt`).
- **Zero Heavy Frontend Dependencies**: Written in vanilla JavaScript and modern CSS for lightning-fast loading and zero bundle bloat.

---

## 📁 Project Structure

```
notes_app/
├── app.py              # Flask app factory, auth routes, page routes & RESTful JSON API
├── database.py         # SQLite schema initialization, users, reset codes & multi-tenant CRUD
├── email_service.py    # SMTP email dispatcher with TLS & local dev fallback
├── notes.db            # SQLite database file (created on first run)
├── sample_notes.py     # Script to seed starter notes & subject folders for demo user
├── requirements.txt    # Python dependencies (Flask >= 3.0.0, Werkzeug)
├── run.sh              # One-click startup script for Linux/macOS
├── run.bat             # One-click startup script for Windows
├── static/
│   ├── app.js          # Client-side auth, reactive search, folder tree logic, modals & markdown
│   └── style.css       # Clean responsive styling, auth modal, animations, themes, and CSS variables
├── templates/
│   └── index.html      # Main HTML5 application shell, auth modal and editor modals
└── tests/
    └── test_app.py     # Comprehensive automated test suite (25 tests: auth, DB & API)
```

---

## 🚀 Quick Start

### Option 1: Using the Startup Script (Recommended)

- **Linux / macOS / WSL / Git Bash**:
  ```bash
  ./run.sh
  ```
- **Windows (Command Prompt / PowerShell / Double-Click)**:
  ```cmd
  run.bat
  ```
This automatically sets up the `.venv`, installs requirements, seeds sample notes if needed, and launches the server at `http://127.0.0.1:5000`.

### Option 2: Manual Setup

#### On Linux / macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 sample_notes.py
python3 app.py
```

#### On Windows (PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python sample_notes.py
python app.py
```

#### On Windows (Command Prompt / CMD):
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
python sample_notes.py
python app.py
```

Open your browser at:
```
http://127.0.0.1:5000
```

---

## 📡 RESTful API Endpoints

### 🔐 Authentication & Password Reset
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Register a new user (`{"username", "email", "password"}`) and establish session |
| `POST` | `/api/auth/login` | Authenticate user via username or email (`{"username", "password"}`) |
| `POST` | `/api/auth/logout` | Terminate current session |
| `GET` | `/api/auth/me` | Fetch active authenticated user profile |
| `POST` | `/api/auth/forgot-password` | Dispatch 6-digit reset code to user's registered email (`{"email"}`) |
| `POST` | `/api/auth/reset-password` | Verify 6-digit code and set new password (`{"email", "code", "new_password"}`) |

### 📁 Notes & Folders (Protected by Session Authentication)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/folders` | List all user folders in tree order with `depth`, `path`, and `note_count` |
| `POST` | `/api/folders` | Create a new folder or nested subfolder (`{"name": "Projects", "parent_id": 2}`) |
| `PUT` | `/api/folders/<id>` | Rename or re-parent a folder (`{"name": "Sprint 1", "parent_id": 3}`) |
| `DELETE` | `/api/folders/<id>` | Delete folder & subfolders (cascades all descendant notes to Home) |
| `GET` | `/api/notes` | List user notes (supports `?q=search`, `?universal=true`, `?folder_id=1`, `?subfolders=true`, `?tag=work`) |
| `POST` | `/api/notes` | Create a new note (`{title, content, tags, color, is_pinned, folder_id}`) |
| `GET` | `/api/notes/<id>` | Fetch a single note by ID (includes `folder_path` and `folder_name`) |
| `PUT` | `/api/notes/<id>` | Update an existing note (supports moving between folders) |
| `DELETE` | `/api/notes/<id>` | Delete a note |
| `POST` | `/api/notes/<id>/pin` | Toggle pinned state for a note |
| `GET` | `/api/tags` | List all unique tags with note counts |
| `GET` | `/api/export` | Download a complete JSON backup of user's notes |
| `POST` | `/api/import` | Restore / import notes from JSON payload into user account |

---

## ✉️ Email (SMTP) Configuration for Password Resets

SimpleNotes includes built-in standard library SMTP support for sending real email verification codes. To configure a production SMTP mailer, set the following environment variables:

| Variable | Description | Default |
|---|---|---|
| `SMTP_HOST` | Hostname of your SMTP server (e.g. `smtp.gmail.com`, `smtp.sendgrid.net`) | *(None - offline mode)* |
| `SMTP_PORT` | Port for SMTP (e.g. `587` for STARTTLS, `465` for SSL) | `587` |
| `SMTP_USER` | SMTP username or API key | *(None)* |
| `SMTP_PASS` | SMTP password or app password | *(None)* |
| `SMTP_FROM` | Sender address shown in emails | `SimpleNotes <noreply@simplenotes.local>` |
| `SMTP_TLS` | Enable TLS encryption (`true` / `false`) | `true` |

> **Offline / Local Dev Fallback**: When `SMTP_HOST` is not set, SimpleNotes automatically prints the 6-digit verification code to the terminal console and displays it in a local dev banner in the UI modal—allowing instant, zero-setup testing of the full password reset flow.

---

## 🧪 Running Automated Tests

Run the test suite using Python's built-in `unittest`:

```bash
.venv/bin/python3 -m unittest discover -s tests -v
```

All 25 automated tests verify:
- User registration, authentication sessions, and logout
- Strict multi-tenant data isolation (User A cannot view, edit, search, or delete User B's notes or folders)
- Email-based password reset code generation, expiration, single-use validation, and password updating
- Universal search across all folders and subfolders
- Folder and nested subfolder creation, path construction, tree order, circular reference protection, and safe deletion cascade
- Checklists, progress calculations, and export/import workflows.
