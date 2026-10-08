import sqlite3
import datetime
from contextlib import contextmanager
from typing import List, Dict, Optional, Any, Generator
from werkzeug.security import generate_password_hash


@contextmanager
def get_connection(db_path: str) -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: str) -> None:
    with get_connection(db_path) as conn:
        # 1. Users table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                email TEXT UNIQUE NOT NULL COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(LOWER(username))")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(LOWER(email))")

        # 2. Password Resets table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS password_resets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_password_resets_user_code ON password_resets(user_id, code)")

        # 3. Check / Migrate default user for legacy databases
        cursor = conn.execute("SELECT id FROM users LIMIT 1")
        has_user = cursor.fetchone() is not None
        if not has_user:
            default_hash = generate_password_hash("demo123")
            conn.execute(
                "INSERT INTO users (id, username, email, password_hash) VALUES (1, 'demo', 'demo@example.com', ?)",
                (default_hash,)
            )

        # 4. Check folders table
        cursor = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='folders'")
        row = cursor.fetchone()

        if row is None:
            conn.execute("""
                CREATE TABLE folders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL DEFAULT 1,
                    name TEXT NOT NULL COLLATE NOCASE,
                    parent_id INTEGER DEFAULT NULL,
                    is_default INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (parent_id) REFERENCES folders(id) ON DELETE SET NULL
                )
            """)
        else:
            table_sql = row["sql"] or ""
            cursor_info = conn.execute("PRAGMA table_info(folders)")
            col_names = [c["name"] for c in cursor_info.fetchall()]

            if "name TEXT NOT NULL UNIQUE" in table_sql or "name TEXT UNIQUE" in table_sql:
                conn.execute("PRAGMA foreign_keys = OFF")
                conn.execute("""
                    CREATE TABLE folders_migrated (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL DEFAULT 1,
                        name TEXT NOT NULL COLLATE NOCASE,
                        parent_id INTEGER DEFAULT NULL,
                        is_default INTEGER NOT NULL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        FOREIGN KEY (parent_id) REFERENCES folders(id) ON DELETE SET NULL
                    )
                """)
                has_uid = "user_id" in col_names
                has_pid = "parent_id" in col_names

                uid_col = "user_id" if has_uid else "1"
                pid_col = "parent_id" if has_pid else "NULL"
                conn.execute(f"""
                    INSERT INTO folders_migrated (id, user_id, name, parent_id, is_default, created_at)
                    SELECT id, {uid_col}, name, {pid_col}, is_default, created_at FROM folders
                """)
                conn.execute("DROP TABLE folders")
                conn.execute("ALTER TABLE folders_migrated RENAME TO folders")
                conn.execute("PRAGMA foreign_keys = ON")
            else:
                if "parent_id" not in col_names:
                    conn.execute("ALTER TABLE folders ADD COLUMN parent_id INTEGER DEFAULT NULL REFERENCES folders(id)")
                if "user_id" not in col_names:
                    conn.execute("ALTER TABLE folders ADD COLUMN user_id INTEGER DEFAULT NULL REFERENCES users(id)")
                    conn.execute("UPDATE folders SET user_id = 1 WHERE user_id IS NULL")

        # Ensure default Home folder exists for user 1
        conn.execute("""
            INSERT OR IGNORE INTO folders (id, user_id, name, parent_id, is_default)
            VALUES (1, 1, 'Home', NULL, 1)
        """)

        # Ensure any orphan folders belong to user 1
        conn.execute("UPDATE folders SET user_id = 1 WHERE user_id IS NULL")

        # Unique index on folder name within same user and same parent
        conn.execute("DROP INDEX IF EXISTS idx_folders_parent_name")
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_folders_user_parent_name
            ON folders(COALESCE(user_id, 1), COALESCE(parent_id, 0), LOWER(name))
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_folders_parent ON folders(parent_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_folders_user ON folders(user_id)")

        # 5. Notes table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                title TEXT NOT NULL,
                content TEXT NOT NULL DEFAULT '',
                tags TEXT NOT NULL DEFAULT '',
                color TEXT NOT NULL DEFAULT 'default',
                is_pinned INTEGER NOT NULL DEFAULT 0,
                folder_id INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE SET DEFAULT
            )
        """)

        cursor = conn.execute("PRAGMA table_info(notes)")
        note_cols = [r["name"] for r in cursor.fetchall()]
        if "folder_id" not in note_cols:
            conn.execute("ALTER TABLE notes ADD COLUMN folder_id INTEGER NOT NULL DEFAULT 1")
        if "user_id" not in note_cols:
            conn.execute("ALTER TABLE notes ADD COLUMN user_id INTEGER DEFAULT NULL REFERENCES users(id)")

        conn.execute("UPDATE notes SET user_id = 1 WHERE user_id IS NULL")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_pinned ON notes(is_pinned DESC, updated_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_folder ON notes(folder_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_user ON notes(user_id)")
        conn.commit()


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    raw_tags = d.get("tags", "")
    if isinstance(raw_tags, str):
        d["tags_list"] = [t.strip() for t in raw_tags.split(",") if t.strip()]
    else:
        d["tags_list"] = []
    d["is_pinned"] = bool(d.get("is_pinned", 0))
    d["folder_id"] = d.get("folder_id", 1)
    d["user_id"] = d.get("user_id", 1)
    d["folder_name"] = d.get("folder_name", "Home")
    d["folder_path"] = d.get("folder_path", d["folder_name"])
    return d


# ---------------- User & Authentication Operations ----------------

def create_user(db_path: str, username: str, email: str, password_hash: str) -> Dict[str, Any]:
    """Creates a new user and provisions their default Home folder."""
    clean_username = username.strip()
    clean_email = email.strip().lower()

    if not clean_username or len(clean_username) < 3:
        raise ValueError("Username must be at least 3 characters")
    if not clean_email or "@" not in clean_email:
        raise ValueError("A valid email address is required")
    if not password_hash:
        raise ValueError("Password hash is required")

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        # Check uniqueness
        cursor.execute("SELECT id FROM users WHERE LOWER(username) = LOWER(?)", (clean_username,))
        if cursor.fetchone():
            raise ValueError(f"Username '{clean_username}' is already registered")

        cursor.execute("SELECT id FROM users WHERE LOWER(email) = LOWER(?)", (clean_email,))
        if cursor.fetchone():
            raise ValueError(f"Email '{clean_email}' is already registered")

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (clean_username, clean_email, password_hash, now)
        )
        user_id = cursor.lastrowid

        # Provision user's personal default Home folder
        cursor.execute(
            "INSERT INTO folders (user_id, name, parent_id, is_default) VALUES (?, 'Home', NULL, 1)",
            (user_id,)
        )
        conn.commit()

    user = get_user_by_id(db_path, user_id)
    if not user:
        raise RuntimeError("Failed to create user account")
    return user


def get_user_by_id(db_path: str, user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve user public details (without password hash)."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, created_at FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_user_by_username_or_email(db_path: str, identifier: str) -> Optional[Dict[str, Any]]:
    """Retrieve full user details including password_hash for authentication."""
    clean = identifier.strip().lower()
    if not clean:
        return None
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, email, password_hash, created_at FROM users WHERE LOWER(username) = ? OR LOWER(email) = ?",
            (clean, clean)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_user_by_email(db_path: str, email: str) -> Optional[Dict[str, Any]]:
    """Retrieve user details by email address."""
    clean = email.strip().lower()
    if not clean:
        return None
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, created_at FROM users WHERE LOWER(email) = ?", (clean,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_user_password(db_path: str, user_id: int, new_password_hash: str) -> bool:
    """Updates password hash for a specific user."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_password_hash, user_id))
        conn.commit()
        return cursor.rowcount > 0


def create_password_reset_code(db_path: str, user_id: int, code: str, expires_minutes: int = 15) -> Dict[str, Any]:
    """Saves a password reset verification code with an expiration window."""
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    expires_at = now_utc + datetime.timedelta(minutes=expires_minutes)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        # Invalidate any old unused reset codes for this user
        cursor.execute("UPDATE password_resets SET used = 1 WHERE user_id = ? AND used = 0", (user_id,))
        cursor.execute(
            "INSERT INTO password_resets (user_id, code, expires_at, used, created_at) VALUES (?, ?, ?, 0, ?)",
            (user_id, code.strip(), expires_at.isoformat(), now_utc.isoformat())
        )
        conn.commit()

    return {
        "user_id": user_id,
        "code": code.strip(),
        "expires_at": expires_at.isoformat()
    }


def verify_and_use_reset_code(db_path: str, email: str, code: str, new_password_hash: str) -> bool:
    """
    Verifies reset code for the user identified by email.
    If valid and not expired, updates user password and marks code as used.
    """
    user = get_user_by_email(db_path, email)
    if not user:
        return False

    clean_code = code.strip()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM password_resets
            WHERE user_id = ? AND code = ? AND used = 0 AND expires_at > ?
            ORDER BY id DESC LIMIT 1
        """, (user["id"], clean_code, now_iso))
        row = cursor.fetchone()
        if not row:
            return False

        reset_id = row["id"]
        # Mark code used
        cursor.execute("UPDATE password_resets SET used = 1 WHERE id = ?", (reset_id,))
        # Update user password
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_password_hash, user["id"]))
        conn.commit()
        return True


# ---------------- Folder Operations ----------------

def get_user_home_folder(db_path: str, user_id: int) -> Dict[str, Any]:
    """Retrieve or create the default Home folder for a user."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM folders WHERE user_id = ? AND is_default = 1 ORDER BY id ASC LIMIT 1",
            (user_id,)
        )
        row = cursor.fetchone()
        if row:
            folder = get_folder(db_path, row["id"], user_id=user_id)
            if folder:
                return folder

        # Create one if somehow missing
        cursor.execute(
            "INSERT INTO folders (user_id, name, parent_id, is_default) VALUES (?, 'Home', NULL, 1)",
            (user_id,)
        )
        conn.commit()
        folder_id = cursor.lastrowid
        return get_folder(db_path, folder_id, user_id=user_id) or {"id": folder_id, "name": "Home", "user_id": user_id, "is_default": True}


def get_folder_descendant_ids(db_path: str, folder_id: int) -> List[int]:
    """Return list of all descendant folder IDs (children, grandchildren, etc.)."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            WITH RECURSIVE subfolders AS (
                SELECT id FROM folders WHERE parent_id = ?
                UNION ALL
                SELECT f.id FROM folders f
                JOIN subfolders sf ON f.parent_id = sf.id
            )
            SELECT id FROM subfolders
        """, (folder_id,))
        return [r["id"] for r in cursor.fetchall()]


def create_folder(
    db_path: str,
    name: str,
    parent_id: Optional[int] = None,
    user_id: Optional[int] = None
) -> Dict[str, Any]:
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Folder name cannot be empty")

    target_user_id = user_id if user_id is not None else 1

    clean_parent_id = None
    if parent_id is not None:
        try:
            clean_parent_id = int(parent_id)
        except (ValueError, TypeError):
            clean_parent_id = None

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        if clean_parent_id is not None:
            cursor.execute(
                "SELECT id FROM folders WHERE id = ? AND (user_id = ? OR user_id IS NULL)",
                (clean_parent_id, target_user_id)
            )
            if not cursor.fetchone():
                raise ValueError("Parent folder does not exist")

        existing = get_folder_by_name(db_path, clean_name, clean_parent_id, user_id=target_user_id)
        if existing:
            raise ValueError(f"Folder '{clean_name}' already exists in this folder")

        cursor.execute(
            "INSERT INTO folders (user_id, name, parent_id, is_default) VALUES (?, ?, ?, 0)",
            (target_user_id, clean_name, clean_parent_id)
        )
        conn.commit()
        folder_id = cursor.lastrowid

    folder = get_folder(db_path, folder_id, user_id=target_user_id)
    if not folder:
        raise RuntimeError("Failed to retrieve created folder")
    return folder


def get_folder(db_path: str, folder_id: int, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    folders = list_folders(db_path, user_id=user_id)
    for f in folders:
        if f["id"] == folder_id:
            return f
    return None


def get_folder_by_name(
    db_path: str,
    name: str,
    parent_id: Optional[int] = None,
    user_id: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    clean_name = name.strip()
    if not clean_name:
        return None

    clean_parent_id = int(parent_id) if parent_id is not None else None

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        query_parts = ["LOWER(name) = LOWER(?)"]
        params: List[Any] = [clean_name]

        if clean_parent_id is None:
            query_parts.append("parent_id IS NULL")
        else:
            query_parts.append("parent_id = ?")
            params.append(clean_parent_id)

        if user_id is not None:
            query_parts.append("(user_id = ? OR user_id IS NULL)")
            params.append(user_id)

        cursor.execute(f"SELECT id FROM folders WHERE {' AND '.join(query_parts)}", params)
        row = cursor.fetchone()
        if row:
            return get_folder(db_path, row["id"], user_id=user_id)
        return None


def list_folders(db_path: str, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Returns folders ordered in hierarchical tree order for the given user.
    Includes note_count, total_note_count, depth, path, parent_name.
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        if user_id is not None:
            cursor.execute("""
                SELECT f.id, f.user_id, f.name, f.parent_id, f.is_default, f.created_at,
                       COUNT(n.id) as note_count
                FROM folders f
                LEFT JOIN notes n ON n.folder_id = f.id AND (n.user_id = f.user_id OR n.user_id IS NULL)
                WHERE f.user_id = ? OR f.user_id IS NULL
                GROUP BY f.id
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT f.id, f.user_id, f.name, f.parent_id, f.is_default, f.created_at,
                       COUNT(n.id) as note_count
                FROM folders f
                LEFT JOIN notes n ON n.folder_id = f.id
                GROUP BY f.id
            """)
        raw_rows = [dict(r) for r in cursor.fetchall()]

    if not raw_rows:
        return []

    by_id: Dict[int, Dict[str, Any]] = {}
    children_map: Dict[Optional[int], List[int]] = {}

    for row in raw_rows:
        fid = row["id"]
        pid = row["parent_id"]
        row["is_default"] = bool(row.get("is_default", 0))
        by_id[fid] = row
        children_map.setdefault(pid, []).append(fid)

    def build_path(fid: int) -> str:
        f = by_id[fid]
        pid = f["parent_id"]
        if pid and pid in by_id:
            return f"{build_path(pid)} / {f['name']}"
        return f["name"]

    def get_depth(fid: int) -> int:
        f = by_id[fid]
        pid = f["parent_id"]
        if pid and pid in by_id:
            return get_depth(pid) + 1
        return 0

    for fid, f in by_id.items():
        f["path"] = build_path(fid)
        f["depth"] = get_depth(fid)
        pid = f["parent_id"]
        f["parent_name"] = by_id[pid]["name"] if pid and pid in by_id else None

    # Compute total recursive note counts
    def get_total_count(fid: int) -> int:
        count = by_id[fid].get("note_count", 0)
        for child_id in children_map.get(fid, []):
            count += get_total_count(child_id)
        return count

    for fid, f in by_id.items():
        f["total_note_count"] = get_total_count(fid)

    ordered_folders: List[Dict[str, Any]] = []

    def sort_key(fid: int):
        f = by_id[fid]
        return (0 if f["is_default"] else 1, f["name"].lower())

    def traverse(parent_id: Optional[int]):
        children = children_map.get(parent_id, [])
        children.sort(key=sort_key)
        for cid in children:
            ordered_folders.append(by_id[cid])
            traverse(cid)

    traverse(None)

    # In case of broken links
    if len(ordered_folders) < len(by_id):
        seen = {f["id"] for f in ordered_folders}
        for fid, f in sorted(by_id.items(), key=lambda x: x[1]["name"].lower()):
            if fid not in seen:
                ordered_folders.append(f)

    return ordered_folders


def update_folder(
    db_path: str,
    folder_id: int,
    name: Optional[str] = None,
    parent_id: Any = ...,
    user_id: Optional[int] = None
) -> Dict[str, Any]:
    existing = get_folder(db_path, folder_id, user_id=user_id)
    if not existing:
        raise ValueError("Folder not found")
    if existing["is_default"]:
        raise ValueError("Cannot rename default Home folder")

    target_user_id = existing.get("user_id") or user_id or 1
    new_name = existing["name"] if name is None else name.strip()
    if not new_name:
        raise ValueError("Folder name cannot be empty")

    new_parent_id = existing["parent_id"] if parent_id is ... else parent_id
    if new_parent_id is not None:
        try:
            new_parent_id = int(new_parent_id)
        except (ValueError, TypeError):
            new_parent_id = None

    if new_parent_id == folder_id:
        raise ValueError("A folder cannot be its own parent")

    if new_parent_id is not None:
        parent_folder = get_folder(db_path, new_parent_id, user_id=target_user_id)
        if not parent_folder:
            raise ValueError("Target parent folder does not exist")

        descendant_ids = get_folder_descendant_ids(db_path, folder_id)
        if new_parent_id in descendant_ids:
            raise ValueError("Cannot move a folder inside one of its subfolders")

    other = get_folder_by_name(db_path, new_name, new_parent_id, user_id=target_user_id)
    if other and other["id"] != folder_id:
        raise ValueError(f"Folder '{new_name}' already exists in that parent folder")

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE folders SET name = ?, parent_id = ? WHERE id = ?",
            (new_name, new_parent_id, folder_id)
        )
        conn.commit()

    res = get_folder(db_path, folder_id, user_id=target_user_id)
    if not res:
        raise RuntimeError("Failed to retrieve updated folder")
    return res


def delete_folder(db_path: str, folder_id: int, user_id: Optional[int] = None) -> bool:
    """
    Deletes a folder and all its descendant subfolders.
    Safely cascades all notes inside them to the user's default Home folder.
    """
    existing = get_folder(db_path, folder_id, user_id=user_id)
    if not existing or existing["is_default"]:
        return False

    target_user_id = existing.get("user_id") or user_id or 1
    user_home = get_user_home_folder(db_path, target_user_id)
    home_id = user_home["id"]

    if folder_id == home_id:
        return False

    descendant_ids = get_folder_descendant_ids(db_path, folder_id)
    all_to_delete = [folder_id] + descendant_ids

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        placeholders = ",".join(["?"] * len(all_to_delete))
        cursor.execute(
            f"UPDATE notes SET folder_id = ? WHERE folder_id IN ({placeholders}) AND (user_id = ? OR user_id IS NULL)",
            [home_id] + all_to_delete + [target_user_id]
        )
        cursor.execute(
            f"DELETE FROM folders WHERE id IN ({placeholders})",
            all_to_delete
        )
        conn.commit()
        return cursor.rowcount > 0


# ---------------- Note Operations ----------------

def _get_folders_path_map(db_path: str, user_id: Optional[int] = None) -> Dict[int, Dict[str, str]]:
    folders = list_folders(db_path, user_id=user_id)
    return {f["id"]: {"name": f["name"], "path": f["path"]} for f in folders}


def create_note(
    db_path: str,
    title: str,
    content: str = "",
    tags: str = "",
    color: str = "default",
    is_pinned: bool = False,
    folder_id: Optional[int] = None,
    user_id: Optional[int] = None
) -> Dict[str, Any]:
    cleaned_title = title.strip() or "Untitled Note"
    cleaned_tags = ",".join([t.strip() for t in tags.split(",") if t.strip()])
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    target_user_id = user_id if user_id is not None else 1

    # Verify folder_id belongs to user, fallback to user's Home folder
    target_folder = None
    if folder_id is not None:
        target_folder = get_folder(db_path, folder_id, user_id=target_user_id)
    if not target_folder:
        target_folder = get_user_home_folder(db_path, target_user_id)

    target_folder_id = target_folder["id"]

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO notes (user_id, title, content, tags, color, is_pinned, folder_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (target_user_id, cleaned_title, content, cleaned_tags, color, 1 if is_pinned else 0, target_folder_id, now, now)
        )
        conn.commit()
        note_id = cursor.lastrowid

    note = get_note(db_path, note_id, user_id=target_user_id)
    if not note:
        raise RuntimeError("Failed to retrieve created note")
    return note


def get_note(db_path: str, note_id: int, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    folders_map = _get_folders_path_map(db_path, user_id=user_id)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        if user_id is not None:
            cursor.execute("SELECT * FROM notes WHERE id = ? AND (user_id = ? OR user_id IS NULL)", (note_id, user_id))
        else:
            cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        if not row:
            return None
        d = _row_to_dict(row)
        fid = d.get("folder_id", 1)
        folder_info = folders_map.get(fid, {"name": "Home", "path": "Home"})
        d["folder_name"] = folder_info["name"]
        d["folder_path"] = folder_info["path"]
        return d


def list_notes(
    db_path: str,
    query: Optional[str] = None,
    tag: Optional[str] = None,
    folder_id: Optional[int] = None,
    include_subfolders: bool = False,
    sort_by: str = "updated_desc",
    user_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    conditions = []
    params: List[Any] = []

    folders_map = _get_folders_path_map(db_path, user_id=user_id)

    if user_id is not None:
        conditions.append("(notes.user_id = ? OR notes.user_id IS NULL)")
        params.append(user_id)

    if folder_id is not None:
        if include_subfolders:
            sub_ids = [folder_id] + get_folder_descendant_ids(db_path, folder_id)
            placeholders = ",".join(["?"] * len(sub_ids))
            conditions.append(f"notes.folder_id IN ({placeholders})")
            params.extend(sub_ids)
        else:
            conditions.append("notes.folder_id = ?")
            params.append(folder_id)

    if query and query.strip():
        q_clean = query.strip()
        search_term = f"%{q_clean}%"
        # Match title, content, tags, folder name, or notes located in matching subfolder paths
        matching_fids = [
            fid for fid, finfo in folders_map.items()
            if q_clean.lower() in finfo["path"].lower() or q_clean.lower() in finfo["name"].lower()
        ]
        if matching_fids:
            f_placeholders = ",".join(["?"] * len(matching_fids))
            conditions.append(
                f"(notes.title LIKE ? OR notes.content LIKE ? OR notes.tags LIKE ? OR folders.name LIKE ? OR notes.folder_id IN ({f_placeholders}))"
            )
            params.extend([search_term, search_term, search_term, search_term] + matching_fids)
        else:
            conditions.append(
                "(notes.title LIKE ? OR notes.content LIKE ? OR notes.tags LIKE ? OR folders.name LIKE ?)"
            )
            params.extend([search_term, search_term, search_term, search_term])

    if tag and tag.strip():
        tag_clean = tag.strip().lower()
        conditions.append("(',' || LOWER(notes.tags) || ',' LIKE ?)")
        params.append(f"%,{tag_clean},%")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sort_options = {
        "updated_desc": "notes.is_pinned DESC, notes.updated_at DESC",
        "updated_asc": "notes.is_pinned DESC, notes.updated_at ASC",
        "created_desc": "notes.is_pinned DESC, notes.created_at DESC",
        "created_asc": "notes.is_pinned DESC, notes.created_at ASC",
        "title_asc": "notes.is_pinned DESC, notes.title COLLATE NOCASE ASC",
        "title_desc": "notes.is_pinned DESC, notes.title COLLATE NOCASE DESC",
    }
    order_clause = sort_options.get(sort_by, "notes.is_pinned DESC, notes.updated_at DESC")

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT notes.* FROM notes
            LEFT JOIN folders ON notes.folder_id = folders.id
            {where_clause}
            ORDER BY {order_clause}
        """, params)
        rows = cursor.fetchall()

        results = []
        for r in rows:
            d = _row_to_dict(r)
            fid = d.get("folder_id", 1)
            folder_info = folders_map.get(fid, {"name": "Home", "path": "Home"})
            d["folder_name"] = folder_info["name"]
            d["folder_path"] = folder_info["path"]
            results.append(d)
        return results


def update_note(
    db_path: str,
    note_id: int,
    title: Optional[str] = None,
    content: Optional[str] = None,
    tags: Optional[str] = None,
    color: Optional[str] = None,
    is_pinned: Optional[bool] = None,
    folder_id: Optional[int] = None,
    user_id: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    existing = get_note(db_path, note_id, user_id=user_id)
    if not existing:
        return None

    target_user_id = existing.get("user_id") or user_id or 1
    new_title = existing["title"] if title is None else (title.strip() or "Untitled Note")
    new_content = existing["content"] if content is None else content
    if tags is not None:
        new_tags = ",".join([t.strip() for t in tags.split(",") if t.strip()])
    else:
        new_tags = existing["tags"]
    new_color = existing["color"] if color is None else color
    new_pinned = existing["is_pinned"] if is_pinned is None else (1 if is_pinned else 0)

    if folder_id is not None:
        target_folder = get_folder(db_path, folder_id, user_id=target_user_id)
        new_folder_id = folder_id if target_folder else existing.get("folder_id", 1)
    else:
        new_folder_id = existing.get("folder_id", 1)

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE notes
            SET title = ?, content = ?, tags = ?, color = ?, is_pinned = ?, folder_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (new_title, new_content, new_tags, new_color, 1 if new_pinned else 0, new_folder_id, now, note_id)
        )
        conn.commit()
    return get_note(db_path, note_id, user_id=target_user_id)


def delete_note(db_path: str, note_id: int, user_id: Optional[int] = None) -> bool:
    existing = get_note(db_path, note_id, user_id=user_id)
    if not existing:
        return False
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()
        return cursor.rowcount > 0


def toggle_pin(db_path: str, note_id: int, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    existing = get_note(db_path, note_id, user_id=user_id)
    if not existing:
        return None
    new_status = not existing["is_pinned"]
    return update_note(db_path, note_id, is_pinned=new_status, user_id=user_id)


def get_all_tags(db_path: str, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        if user_id is not None:
            cursor.execute("SELECT tags FROM notes WHERE tags != '' AND (user_id = ? OR user_id IS NULL)", (user_id,))
        else:
            cursor.execute("SELECT tags FROM notes WHERE tags != ''")
        rows = cursor.fetchall()
        counts: Dict[str, int] = {}
        for r in rows:
            raw = r["tags"]
            if raw:
                for t in raw.split(","):
                    clean = t.strip()
                    if clean:
                        counts[clean] = counts.get(clean, 0) + 1
        return [{"name": k, "count": v} for k, v in sorted(counts.items(), key=lambda x: (-x[1], x[0].lower()))]


def export_notes(db_path: str, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    return list_notes(db_path, sort_by="created_asc", user_id=user_id)


def import_notes(db_path: str, notes_data: List[Dict[str, Any]], user_id: Optional[int] = None) -> int:
    imported_count = 0
    target_user_id = user_id if user_id is not None else 1
    user_home = get_user_home_folder(db_path, target_user_id)
    home_id = user_home["id"]

    for item in notes_data:
        if not isinstance(item, dict):
            continue
        title = item.get("title", "Untitled Note")
        content = item.get("content", "")
        tags = item.get("tags", "")
        if isinstance(tags, list):
            tags = ",".join(tags)
        color = item.get("color", "default")
        is_pinned = bool(item.get("is_pinned", False))

        folder_path = (item.get("folder_path") or item.get("folder_name") or "").strip()
        folder_id = item.get("folder_id")

        target_folder_id = home_id
        if folder_path and folder_path.lower() != "home":
            # Recreate hierarchy along the path for this user
            segments = [s.strip() for s in folder_path.split("/") if s.strip()]
            current_parent_id = None
            for seg in segments:
                if seg.lower() == "home":
                    current_parent_id = home_id
                    continue
                f = get_folder_by_name(db_path, seg, current_parent_id, user_id=target_user_id)
                if not f:
                    try:
                        f = create_folder(db_path, seg, current_parent_id, user_id=target_user_id)
                    except Exception:
                        f = user_home
                current_parent_id = f["id"] if f else home_id
            target_folder_id = current_parent_id or home_id
        elif folder_id and get_folder(db_path, folder_id, user_id=target_user_id):
            target_folder_id = folder_id

        create_note(
            db_path,
            title,
            content,
            tags,
            color,
            is_pinned,
            folder_id=target_folder_id,
            user_id=target_user_id
        )
        imported_count += 1
    return imported_count
