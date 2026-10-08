import os
import re
import json
import sqlite3
import secrets
import functools
from flask import Flask, render_template, request, jsonify, session, Response
from werkzeug.security import generate_password_hash, check_password_hash
import database
import email_service


def create_app(db_path=None):
    app = Flask(__name__, static_folder="static", template_folder="templates")

    if db_path is None:
        db_path = os.environ.get("NOTES_DB_PATH", os.path.join(os.path.dirname(__file__), "notes.db"))

    app.config["DB_PATH"] = db_path
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "simplenotes-session-secret-key-2026")
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    database.init_db(db_path)

    # ---------------- Auth Decorator ----------------

    def login_required(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session or not session["user_id"]:
                return jsonify({"error": "Authentication required", "logged_in": False}), 401
            return f(*args, **kwargs)
        return decorated_function

    def get_current_user_id() -> int:
        return session.get("user_id")

    @app.route("/")
    def index():
        return render_template("index.html")

    # ---------------- Authentication Routes ----------------

    @app.route("/api/auth/register", methods=["POST"])
    def register_route():
        data = request.get_json() or {}
        username = (data.get("username") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        if not username or len(username) < 3:
            return jsonify({"error": "Username must be at least 3 characters long"}), 400
        if not re.match(r"^[a-zA-Z0-9_.-]+$", username):
            return jsonify({"error": "Username can only contain letters, numbers, dots, hyphens, and underscores"}), 400
        if not email or "@" not in email or "." not in email:
            return jsonify({"error": "A valid email address is required"}), 400
        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters long"}), 400

        try:
            pw_hash = generate_password_hash(password)
            user = database.create_user(app.config["DB_PATH"], username, email, pw_hash)
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return jsonify({"success": True, "user": user}), 201
        except ValueError as e:
            return jsonify({"error": str(e)}), 409
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/auth/login", methods=["POST"])
    def login_route():
        data = request.get_json() or {}
        identifier = (data.get("username") or "").strip()
        password = data.get("password") or ""

        if not identifier or not password:
            return jsonify({"error": "Username/email and password are required"}), 400

        user = database.get_user_by_username_or_email(app.config["DB_PATH"], identifier)
        if not user or not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "Invalid username or password"}), 401

        session["user_id"] = user["id"]
        session["username"] = user["username"]

        safe_user = {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "created_at": user.get("created_at")
        }
        return jsonify({"success": True, "user": safe_user})

    @app.route("/api/auth/logout", methods=["POST"])
    def logout_route():
        session.clear()
        return jsonify({"success": True, "logged_in": False})

    @app.route("/api/auth/me", methods=["GET"])
    def me_route():
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"logged_in": False, "user": None})

        user = database.get_user_by_id(app.config["DB_PATH"], user_id)
        if not user:
            session.clear()
            return jsonify({"logged_in": False, "user": None})

        return jsonify({"logged_in": True, "user": user})

    @app.route("/api/auth/forgot-password", methods=["POST"])
    def forgot_password_route():
        data = request.get_json() or {}
        email = (data.get("email") or "").strip().lower()
        if not email or "@" not in email:
            return jsonify({"error": "A valid email address is required"}), 400

        user = database.get_user_by_email(app.config["DB_PATH"], email)
        if not user:
            return jsonify({"error": "No account found with this email address"}), 404

        # Generate secure 6-digit verification code
        code = f"{secrets.randbelow(900000) + 100000}"
        database.create_password_reset_code(app.config["DB_PATH"], user["id"], code, expires_minutes=15)

        # Dispatch verification email
        email_service.send_password_reset_email(email, code)

        is_dev = app.config.get("TESTING") or os.environ.get("FLASK_ENV") == "development" or not os.environ.get("SMTP_HOST")
        resp = {
            "success": True,
            "message": f"Verification code has been sent to {email}"
        }
        if is_dev:
            resp["dev_code"] = code

        return jsonify(resp)

    @app.route("/api/auth/reset-password", methods=["POST"])
    def reset_password_route():
        data = request.get_json() or {}
        email = (data.get("email") or "").strip().lower()
        code = (data.get("code") or "").strip()
        new_password = data.get("new_password") or ""

        if not email or not code or not new_password:
            return jsonify({"error": "Email, verification code, and new password are required"}), 400

        if len(new_password) < 6:
            return jsonify({"error": "Password must be at least 6 characters long"}), 400

        new_hash = generate_password_hash(new_password)
        success = database.verify_and_use_reset_code(app.config["DB_PATH"], email, code, new_hash)

        if not success:
            return jsonify({"error": "Invalid or expired verification code"}), 400

        return jsonify({"success": True, "message": "Password reset successfully. You can now log in with your new password."})

    # ---------------- Folder Routes ----------------

    @app.route("/api/folders", methods=["GET"])
    @login_required
    def list_folders_route():
        user_id = get_current_user_id()
        folders = database.list_folders(app.config["DB_PATH"], user_id=user_id)
        return jsonify(folders)

    @app.route("/api/folders", methods=["POST"])
    @login_required
    def create_folder_route():
        user_id = get_current_user_id()
        data = request.get_json() or {}
        name = data.get("name", "").strip()
        if not name:
            return jsonify({"error": "Folder name is required"}), 400

        parent_id = data.get("parent_id")
        if parent_id is not None:
            try:
                parent_id = int(parent_id)
            except (ValueError, TypeError):
                parent_id = None

        existing = database.get_folder_by_name(app.config["DB_PATH"], name, parent_id, user_id=user_id)
        if existing:
            return jsonify({"error": f"Folder '{name}' already exists in this folder"}), 409
        try:
            folder = database.create_folder(app.config["DB_PATH"], name, parent_id=parent_id, user_id=user_id)
            return jsonify(folder), 201
        except (sqlite3.IntegrityError, ValueError) as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/api/folders/<int:folder_id>", methods=["PUT"])
    @login_required
    def update_folder_route(folder_id):
        user_id = get_current_user_id()
        data = request.get_json() or {}
        name = data.get("name")
        if name is not None:
            name = name.strip()
            if not name:
                return jsonify({"error": "Folder name cannot be empty"}), 400

        existing = database.get_folder(app.config["DB_PATH"], folder_id, user_id=user_id)
        if not existing:
            return jsonify({"error": "Folder not found"}), 404
        if existing["is_default"]:
            return jsonify({"error": "Cannot rename default Home folder"}), 400

        parent_id = ...
        if "parent_id" in data:
            raw_p = data.get("parent_id")
            if raw_p is None:
                parent_id = None
            else:
                try:
                    parent_id = int(raw_p)
                except (ValueError, TypeError):
                    parent_id = None

        try:
            updated = database.update_folder(
                app.config["DB_PATH"],
                folder_id,
                name=name,
                parent_id=parent_id,
                user_id=user_id
            )
            return jsonify(updated)
        except (sqlite3.IntegrityError, ValueError) as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/api/folders/<int:folder_id>", methods=["DELETE"])
    @login_required
    def delete_folder_route(folder_id):
        user_id = get_current_user_id()
        folder = database.get_folder(app.config["DB_PATH"], folder_id, user_id=user_id)
        if not folder:
            return jsonify({"error": "Folder not found"}), 404
        if folder["is_default"]:
            return jsonify({"error": "Cannot delete default Home folder"}), 400
        database.delete_folder(app.config["DB_PATH"], folder_id, user_id=user_id)
        return jsonify({"success": True, "id": folder_id})

    # ---------------- Note Routes ----------------

    @app.route("/api/notes", methods=["GET"])
    @login_required
    def list_notes_route():
        user_id = get_current_user_id()
        query = request.args.get("q", None)
        tag = request.args.get("tag", None)
        folder_id_param = request.args.get("folder_id", None)
        subfolders_param = request.args.get("subfolders", None)
        universal = request.args.get("universal", "false").lower() in ("1", "true")

        folder_id = None
        if folder_id_param and folder_id_param.isdigit():
            # If universal search is requested with a query, search across all folders and subfolders
            if not (universal and query):
                folder_id = int(folder_id_param)

        if subfolders_param is not None:
            include_sub = subfolders_param.lower() in ("1", "true")
        else:
            # Default to including subfolders whenever searching with a query
            include_sub = True if query else False

        sort_by = request.args.get("sort", "updated_desc")
        notes = database.list_notes(
            app.config["DB_PATH"],
            query=query,
            tag=tag,
            folder_id=folder_id,
            include_subfolders=include_sub,
            sort_by=sort_by,
            user_id=user_id
        )
        return jsonify(notes)

    @app.route("/api/notes", methods=["POST"])
    @login_required
    def create_note_route():
        user_id = get_current_user_id()
        data = request.get_json() or {}
        title = data.get("title", "").strip() or "Untitled Note"
        content = data.get("content", "")
        tags = data.get("tags", "")
        if isinstance(tags, list):
            tags = ",".join(tags)
        color = data.get("color", "default")
        is_pinned = bool(data.get("is_pinned", False))

        raw_folder_id = data.get("folder_id")
        folder_id = None
        if raw_folder_id is not None:
            try:
                folder_id = int(raw_folder_id)
            except (TypeError, ValueError):
                folder_id = None

        note = database.create_note(
            app.config["DB_PATH"],
            title=title,
            content=content,
            tags=tags,
            color=color,
            is_pinned=is_pinned,
            folder_id=folder_id,
            user_id=user_id
        )
        return jsonify(note), 201

    @app.route("/api/notes/<int:note_id>", methods=["GET"])
    @login_required
    def get_note_route(note_id):
        user_id = get_current_user_id()
        note = database.get_note(app.config["DB_PATH"], note_id, user_id=user_id)
        if not note:
            return jsonify({"error": "Note not found"}), 404
        return jsonify(note)

    @app.route("/api/notes/<int:note_id>", methods=["PUT"])
    @login_required
    def update_note_route(note_id):
        user_id = get_current_user_id()
        data = request.get_json() or {}
        title = data.get("title")
        content = data.get("content")
        tags = data.get("tags")
        if isinstance(tags, list):
            tags = ",".join(tags)
        color = data.get("color")
        is_pinned = data.get("is_pinned")
        if is_pinned is not None:
            is_pinned = bool(is_pinned)

        folder_id = None
        if "folder_id" in data:
            try:
                folder_id = int(data["folder_id"])
            except (TypeError, ValueError):
                folder_id = None

        updated = database.update_note(
            app.config["DB_PATH"],
            note_id,
            title=title,
            content=content,
            tags=tags,
            color=color,
            is_pinned=is_pinned,
            folder_id=folder_id,
            user_id=user_id
        )
        if not updated:
            return jsonify({"error": "Note not found"}), 404
        return jsonify(updated)

    @app.route("/api/notes/<int:note_id>", methods=["DELETE"])
    @login_required
    def delete_note_route(note_id):
        user_id = get_current_user_id()
        success = database.delete_note(app.config["DB_PATH"], note_id, user_id=user_id)
        if not success:
            return jsonify({"error": "Note not found"}), 404
        return jsonify({"success": True, "id": note_id})

    @app.route("/api/notes/<int:note_id>/pin", methods=["POST"])
    @login_required
    def toggle_pin_route(note_id):
        user_id = get_current_user_id()
        note = database.toggle_pin(app.config["DB_PATH"], note_id, user_id=user_id)
        if not note:
            return jsonify({"error": "Note not found"}), 404
        return jsonify(note)

    @app.route("/api/tags", methods=["GET"])
    @login_required
    def get_tags_route():
        user_id = get_current_user_id()
        tags = database.get_all_tags(app.config["DB_PATH"], user_id=user_id)
        return jsonify(tags)

    @app.route("/api/export", methods=["GET"])
    @login_required
    def export_route():
        user_id = get_current_user_id()
        notes = database.export_notes(app.config["DB_PATH"], user_id=user_id)
        payload = {
            "version": "1.0",
            "count": len(notes),
            "notes": notes
        }
        response = Response(
            json.dumps(payload, indent=2),
            mimetype="application/json",
            headers={"Content-Disposition": "attachment;filename=notes_backup.json"}
        )
        return response

    @app.route("/api/import", methods=["POST"])
    @login_required
    def import_route():
        user_id = get_current_user_id()
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid or missing JSON payload"}), 400

        notes_list = data.get("notes") if isinstance(data, dict) and "notes" in data else data
        if not isinstance(notes_list, list):
            return jsonify({"error": "Expected a list of notes"}), 400

        count = database.import_notes(app.config["DB_PATH"], notes_list, user_id=user_id)
        return jsonify({"success": True, "imported": count})

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() in ("1", "true")
    print(f"🚀 Notes App running at http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
