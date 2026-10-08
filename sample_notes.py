import os
import database

def seed_sample_notes(db_path=None):
    if db_path is None:
        db_path = os.environ.get("NOTES_DB_PATH", os.path.join(os.path.dirname(__file__), "notes.db"))

    database.init_db(db_path)

    # Create sample folders for specific categorization needs
    home_folder = database.get_user_home_folder(db_path, user_id=1)
    root_folders = ["Work", "Personal", "Computer Science"]
    folder_map = {"home": home_folder["id"]}

    for name in root_folders:
        existing = database.get_folder_by_name(db_path, name, user_id=1)
        if existing:
            folder_map[name.lower()] = existing["id"]
        else:
            created = database.create_folder(db_path, name, user_id=1)
            folder_map[name.lower()] = created["id"]

    # Create subfolders inside root folders to showcase tree connecting lines
    subfolders_to_seed = [
        ("Projects", folder_map["work"]),
        ("Python", folder_map["computer science"])
    ]

    for sub_name, parent_id in subfolders_to_seed:
        existing = database.get_folder_by_name(db_path, sub_name, parent_id=parent_id, user_id=1)
        if existing:
            folder_map[sub_name.lower()] = existing["id"]
        else:
            created = database.create_folder(db_path, sub_name, parent_id=parent_id, user_id=1)
            folder_map[sub_name.lower()] = created["id"]

    sample_notes = [
        {
            "title": "Welcome to SimpleNotes! 🚀",
            "content": """Welcome to your new personal notes space!

Features:
• Folder Organization - organize notes by subjects, categories, or projects!
• Home Folder - default home for general notes and quick thoughts.
• Real interactive checkboxes - click the Checkbox button to add one!
• Checklist Progress Bar - live completion tracking on cards and modal.
• Color accents - organize notes visually with flat pastel cards.
• Pinning - click the pin icon to keep important notes at the top.
• Instant Search - press / or Ctrl+K anytime to search.

Try clicking on any note to edit it, or press Ctrl+N to write a new one!""",
            "tags": "Welcome, Guide",
            "color": "blue",
            "is_pinned": True,
            "folder": "home"
        },
        {
            "title": "Project Sprint Checklist ✅",
            "content": """Current Sprint Goals:
[x] Set up Flask web server
[x] Configure SQLite database
[x] Build responsive frontend
[x] Organize notes into folders
[ ] Test JSON export and restore""",
            "tags": "Work, Sprint",
            "color": "green",
            "is_pinned": True,
            "folder": "projects"
        },
        {
            "title": "Books to Read This Year 📚",
            "content": """1. Atomic Habits by James Clear
2. Designing Data-Intensive Applications by Martin Kleppmann
3. Deep Work by Cal Newport
4. Clean Code by Robert C. Martin""",
            "tags": "Personal, Reading",
            "color": "purple",
            "is_pinned": False,
            "folder": "personal"
        },
        {
            "title": "Python Snippet 🐍",
            "content": """Simple helper to read JSON:
```
import json

with open("backup.json", "r") as f:
    data = json.load(f)
    print("Total items:", len(data))
```
Fast and clean!""",
            "tags": "Code, Python",
            "color": "amber",
            "is_pinned": False,
            "folder": "python"
        },
        {
            "title": "Meeting Notes - Product Sync 🗓️",
            "content": """Discussion on upcoming features and user feedback:

• Folder structure: categorize notes into custom folders.
• Home folder: default space for general notes.
• Theme switcher: users love dark mode.
• Shortcuts: Ctrl+S saves note instantly.
• Backup: JSON export allows seamless offline backups.
• Checklists: directly check off items from the cards.""",
            "tags": "Work, Meeting",
            "color": "rose",
            "is_pinned": False,
            "folder": "work"
        }
    ]

    for item in sample_notes:
        folder_id = folder_map.get(item["folder"].lower(), home_folder["id"])
        database.create_note(
            db_path,
            title=item["title"],
            content=item["content"],
            tags=item["tags"],
            color=item["color"],
            is_pinned=item["is_pinned"],
            folder_id=folder_id,
            user_id=1
        )

    print(f"✅ Successfully seeded {len(sample_notes)} sample notes into {db_path}!")

if __name__ == "__main__":
    seed_sample_notes()
