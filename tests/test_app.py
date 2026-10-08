import os
import tempfile
import unittest
import json
import database
from app import create_app


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_notes.db")
        database.init_db(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

    def test_default_folder_exists(self):
        home = database.get_folder(self.db_path, 1)
        self.assertIsNotNone(home)
        self.assertEqual(home["name"], "Home")
        self.assertTrue(home["is_default"])

    def test_create_and_get_note(self):
        note = database.create_note(
            self.db_path,
            title="Test Note 1",
            content="This is test content",
            tags="test, unit",
            color="blue",
            is_pinned=True
        )
        self.assertIsNotNone(note)
        self.assertEqual(note["title"], "Test Note 1")
        self.assertEqual(note["content"], "This is test content")
        self.assertEqual(note["tags_list"], ["test", "unit"])
        self.assertEqual(note["color"], "blue")
        self.assertTrue(note["is_pinned"])
        self.assertEqual(note["folder_id"], 1)
        self.assertEqual(note["folder_name"], "Home")

        fetched = database.get_note(self.db_path, note["id"])
        self.assertEqual(fetched["id"], note["id"])
        self.assertEqual(fetched["title"], "Test Note 1")
        self.assertEqual(fetched["folder_name"], "Home")

    def test_update_note(self):
        note = database.create_note(self.db_path, title="Original", content="Init")
        updated = database.update_note(
            self.db_path,
            note["id"],
            title="Updated Title",
            content="Updated Content",
            color="green",
            is_pinned=True
        )
        self.assertEqual(updated["title"], "Updated Title")
        self.assertEqual(updated["content"], "Updated Content")
        self.assertEqual(updated["color"], "green")
        self.assertTrue(updated["is_pinned"])

    def test_delete_note(self):
        note = database.create_note(self.db_path, title="To Delete")
        success = database.delete_note(self.db_path, note["id"])
        self.assertTrue(success)
        self.assertIsNone(database.get_note(self.db_path, note["id"]))

    def test_toggle_pin(self):
        note = database.create_note(self.db_path, title="Pin test", is_pinned=False)
        toggled = database.toggle_pin(self.db_path, note["id"])
        self.assertTrue(toggled["is_pinned"])
        toggled2 = database.toggle_pin(self.db_path, note["id"])
        self.assertFalse(toggled2["is_pinned"])

    def test_search_and_tag_filter(self):
        database.create_note(self.db_path, title="Grocery List", content="Milk, Eggs", tags="food, personal")
        database.create_note(self.db_path, title="Code Review", content="Review PR 42", tags="work, dev")
        database.create_note(self.db_path, title="Personal Diary", content="Sunny day", tags="personal")

        # Query search
        results = database.list_notes(self.db_path, query="Milk")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Grocery List")

        # Tag filter
        personal_notes = database.list_notes(self.db_path, tag="personal")
        self.assertEqual(len(personal_notes), 2)

        # Unique tags with counts
        all_tags = database.get_all_tags(self.db_path)
        tag_dict = {t["name"]: t["count"] for t in all_tags}
        self.assertEqual(tag_dict["personal"], 2)
        self.assertEqual(tag_dict["food"], 1)
        self.assertEqual(tag_dict["work"], 1)

    def test_universal_search_in_subfolders(self):
        # Create hierarchy: Work -> Engineering -> Backend
        work = database.create_folder(self.db_path, "Work")
        eng = database.create_folder(self.db_path, "Engineering", parent_id=work["id"])
        backend = database.create_folder(self.db_path, "Backend", parent_id=eng["id"])

        # Notes in different levels
        n_home = database.create_note(self.db_path, title="Home Todo", content="Buy groceries")
        n_work = database.create_note(self.db_path, title="Quarterly Plan", content="Company roadmap", folder_id=work["id"])
        n_eng = database.create_note(self.db_path, title="System Architecture", content="Microservices design", folder_id=eng["id"])
        n_backend = database.create_note(self.db_path, title="Database Migration", content="Postgres indexing", tags="sql, database", folder_id=backend["id"])

        # 1. Universal search without folder_id finds note deep in Backend subfolder
        res1 = database.list_notes(self.db_path, query="Postgres")
        self.assertEqual(len(res1), 1)
        self.assertEqual(res1[0]["id"], n_backend["id"])
        self.assertEqual(res1[0]["folder_path"], "Work / Engineering / Backend")

        # 2. Searching by subfolder name matches notes inside that subfolder
        res_by_folder = database.list_notes(self.db_path, query="Backend")
        self.assertEqual(len(res_by_folder), 1)
        self.assertEqual(res_by_folder[0]["id"], n_backend["id"])

        # 3. Searching inside parent folder Work with include_subfolders=True finds all descendants
        res_work_subs = database.list_notes(self.db_path, query="design", folder_id=work["id"], include_subfolders=True)
        self.assertEqual(len(res_work_subs), 1)
        self.assertEqual(res_work_subs[0]["id"], n_eng["id"])

        # 4. Searching for something in backend while scoped to work with include_subfolders=True
        res_backend_in_work = database.list_notes(self.db_path, query="indexing", folder_id=work["id"], include_subfolders=True)
        self.assertEqual(len(res_backend_in_work), 1)
        self.assertEqual(res_backend_in_work[0]["id"], n_backend["id"])

    def test_folder_crud_operations(self):
        # Create Folder
        folder = database.create_folder(self.db_path, "Math")
        self.assertEqual(folder["name"], "Math")
        self.assertFalse(folder["is_default"])

        # List Folders
        folders = database.list_folders(self.db_path)
        folder_names = [f["name"] for f in folders]
        self.assertIn("Home", folder_names)
        self.assertIn("Math", folder_names)

        # Rename Folder
        updated = database.update_folder(self.db_path, folder["id"], "Mathematics")
        self.assertEqual(updated["name"], "Mathematics")

        # Get Folder by Name
        found = database.get_folder_by_name(self.db_path, "mathematics")
        self.assertIsNotNone(found)
        self.assertEqual(found["id"], folder["id"])

    def test_folder_note_assignment_and_filtering(self):
        science = database.create_folder(self.db_path, "Science")
        history = database.create_folder(self.db_path, "History")

        n1 = database.create_note(self.db_path, title="Physics 101", folder_id=science["id"])
        n2 = database.create_note(self.db_path, title="Chemistry", folder_id=science["id"])
        n3 = database.create_note(self.db_path, title="Rome", folder_id=history["id"])
        n4 = database.create_note(self.db_path, title="General Note") # Defaults to Home

        # Filter by Science
        science_notes = database.list_notes(self.db_path, folder_id=science["id"])
        self.assertEqual(len(science_notes), 2)
        for sn in science_notes:
            self.assertEqual(sn["folder_name"], "Science")

        # Filter by History
        history_notes = database.list_notes(self.db_path, folder_id=history["id"])
        self.assertEqual(len(history_notes), 1)
        self.assertEqual(history_notes[0]["title"], "Rome")

        # Filter by Home
        home_notes = database.list_notes(self.db_path, folder_id=1)
        self.assertEqual(len(home_notes), 1)
        self.assertEqual(home_notes[0]["title"], "General Note")

        # Folders note counts
        folders = database.list_folders(self.db_path)
        count_map = {f["name"]: f["note_count"] for f in folders}
        self.assertEqual(count_map["Science"], 2)
        self.assertEqual(count_map["History"], 1)
        self.assertEqual(count_map["Home"], 1)

    def test_folder_deletion_safely_reassigns_to_home(self):
        temp_f = database.create_folder(self.db_path, "Temporary Subject")
        n1 = database.create_note(self.db_path, title="Temp Note 1", folder_id=temp_f["id"])
        n2 = database.create_note(self.db_path, title="Temp Note 2", folder_id=temp_f["id"])

        # Delete custom folder
        deleted = database.delete_folder(self.db_path, temp_f["id"])
        self.assertTrue(deleted)
        self.assertIsNone(database.get_folder(self.db_path, temp_f["id"]))

        # Notes must still exist and be in Home (folder_id = 1)
        reassigned_1 = database.get_note(self.db_path, n1["id"])
        reassigned_2 = database.get_note(self.db_path, n2["id"])
        self.assertIsNotNone(reassigned_1)
        self.assertIsNotNone(reassigned_2)
        self.assertEqual(reassigned_1["folder_id"], 1)
        self.assertEqual(reassigned_1["folder_name"], "Home")
        self.assertEqual(reassigned_2["folder_id"], 1)
        self.assertEqual(reassigned_2["folder_name"], "Home")

        # Home folder itself cannot be deleted
        cannot_del_home = database.delete_folder(self.db_path, 1)
        self.assertFalse(cannot_del_home)
        self.assertIsNotNone(database.get_folder(self.db_path, 1))

    def test_nested_folders_tree_hierarchy(self):
        work = database.create_folder(self.db_path, "Work")
        projects = database.create_folder(self.db_path, "Projects", parent_id=work["id"])
        sprint1 = database.create_folder(self.db_path, "Sprint 1", parent_id=projects["id"])

        # Check depth and path construction
        self.assertEqual(projects["parent_id"], work["id"])
        self.assertEqual(projects["depth"], 1)
        self.assertEqual(projects["path"], "Work / Projects")

        self.assertEqual(sprint1["parent_id"], projects["id"])
        self.assertEqual(sprint1["depth"], 2)
        self.assertEqual(sprint1["path"], "Work / Projects / Sprint 1")

        # Tree listing order and depth
        tree = database.list_folders(self.db_path)
        tree_paths = [f["path"] for f in tree]
        self.assertIn("Work", tree_paths)
        self.assertIn("Work / Projects", tree_paths)
        self.assertIn("Work / Projects / Sprint 1", tree_paths)

        # Circular reference check: Cannot set Work's parent to Sprint 1
        with self.assertRaises(ValueError):
            database.update_folder(self.db_path, work["id"], parent_id=sprint1["id"])

        # Cannot set folder's parent to itself
        with self.assertRaises(ValueError):
            database.update_folder(self.db_path, work["id"], parent_id=work["id"])

    def test_nested_folders_cascade_deletion_and_counts(self):
        dept = database.create_folder(self.db_path, "Engineering")
        team = database.create_folder(self.db_path, "Backend", parent_id=dept["id"])
        subteam = database.create_folder(self.db_path, "APIs", parent_id=team["id"])

        n_dept = database.create_note(self.db_path, title="Dept Note", folder_id=dept["id"])
        n_team = database.create_note(self.db_path, title="Team Note", folder_id=team["id"])
        n_sub = database.create_note(self.db_path, title="Sub Note", folder_id=subteam["id"])

        # Verify direct and total note counts
        tree = database.list_folders(self.db_path)
        f_map = {f["id"]: f for f in tree}
        self.assertEqual(f_map[dept["id"]]["note_count"], 1)
        self.assertEqual(f_map[dept["id"]]["total_note_count"], 3)
        self.assertEqual(f_map[team["id"]]["note_count"], 1)
        self.assertEqual(f_map[team["id"]]["total_note_count"], 2)
        self.assertEqual(f_map[subteam["id"]]["note_count"], 1)
        self.assertEqual(f_map[subteam["id"]]["total_note_count"], 1)

        # Recursive subfolder query: list notes in dept with subfolders=True
        all_eng_notes = database.list_notes(self.db_path, folder_id=dept["id"], include_subfolders=True)
        self.assertEqual(len(all_eng_notes), 3)

        # Deleting dept must safely move notes from dept, team, and subteam to Home
        deleted = database.delete_folder(self.db_path, dept["id"])
        self.assertTrue(deleted)

        for nid in [n_dept["id"], n_team["id"], n_sub["id"]]:
            note = database.get_note(self.db_path, nid)
            self.assertEqual(note["folder_id"], 1)
            self.assertEqual(note["folder_name"], "Home")

    def test_export_and_import(self):
        work_f = database.create_folder(self.db_path, "Work")
        database.create_note(self.db_path, title="N1", content="C1", tags="t1", folder_id=work_f["id"])
        database.create_note(self.db_path, title="N2", content="C2", tags="t2", folder_id=1)
        exported = database.export_notes(self.db_path)
        self.assertEqual(len(exported), 2)

        # Import into fresh DB
        fresh_db = os.path.join(self.temp_dir, "fresh.db")
        database.init_db(fresh_db)
        imported_count = database.import_notes(fresh_db, exported)
        self.assertEqual(imported_count, 2)
        fresh_notes = database.list_notes(fresh_db)
        self.assertEqual(len(fresh_notes), 2)
        # Check that Work folder was automatically created and assigned
        fresh_work_folder = database.get_folder_by_name(fresh_db, "Work")
        self.assertIsNotNone(fresh_work_folder)
        if os.path.exists(fresh_db):
            os.remove(fresh_db)


class TestFlaskAPI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_api.db")
        self.app = create_app(db_path=self.db_path)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        login_res = self.client.post(
            "/api/auth/login",
            data=json.dumps({"username": "demo", "password": "demo123"}),
            content_type="application/json"
        )
        assert login_res.status_code == 200, f"Login failed: {login_res.data}"

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

    def test_index_page(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Simple<strong>Notes</strong>", res.data)
        self.assertIn(b'id="modalProgressBar"', res.data)
        self.assertIn(b'id="foldersList"', res.data)
        self.assertIn(b'id="newFolderBtn"', res.data)
        self.assertIn(b'id="modalFolder"', res.data)

    def test_folders_api_crud(self):
        # 1. List initial folders (Home present)
        list_res = self.client.get("/api/folders")
        self.assertEqual(list_res.status_code, 200)
        folders = list_res.get_json()
        self.assertGreaterEqual(len(folders), 1)
        self.assertEqual(folders[0]["name"], "Home")

        # 2. Create custom folder
        create_res = self.client.post(
            "/api/folders",
            data=json.dumps({"name": "Subject A"}),
            content_type="application/json"
        )
        self.assertEqual(create_res.status_code, 201)
        f_data = create_res.get_json()
        folder_id = f_data["id"]
        self.assertEqual(f_data["name"], "Subject A")

        # 3. Duplicate folder creation rejected
        dup_res = self.client.post(
            "/api/folders",
            data=json.dumps({"name": "Subject A"}),
            content_type="application/json"
        )
        self.assertEqual(dup_res.status_code, 409)

        # 4. Empty name rejected
        empty_res = self.client.post(
            "/api/folders",
            data=json.dumps({"name": "  "}),
            content_type="application/json"
        )
        self.assertEqual(empty_res.status_code, 400)

        # 5. Rename custom folder
        put_res = self.client.put(
            f"/api/folders/{folder_id}",
            data=json.dumps({"name": "Subject Advanced"}),
            content_type="application/json"
        )
        self.assertEqual(put_res.status_code, 200)
        self.assertEqual(put_res.get_json()["name"], "Subject Advanced")

        # 6. Cannot rename Home folder
        put_home = self.client.put(
            "/api/folders/1",
            data=json.dumps({"name": "New Home"}),
            content_type="application/json"
        )
        self.assertEqual(put_home.status_code, 400)

        # 7. Create note in custom folder
        note_res = self.client.post(
            "/api/notes",
            data=json.dumps({
                "title": "Folder Note",
                "content": "In Subject Advanced",
                "folder_id": folder_id
            }),
            content_type="application/json"
        )
        self.assertEqual(note_res.status_code, 201)
        note_data = note_res.get_json()
        self.assertEqual(note_data["folder_id"], folder_id)
        self.assertEqual(note_data["folder_name"], "Subject Advanced")

        # 8. Filter notes by folder_id
        filter_res = self.client.get(f"/api/notes?folder_id={folder_id}")
        self.assertEqual(filter_res.status_code, 200)
        filtered_notes = filter_res.get_json()
        self.assertEqual(len(filtered_notes), 1)
        self.assertEqual(filtered_notes[0]["title"], "Folder Note")

        # 9. Delete custom folder (note reassigns to Home)
        del_res = self.client.delete(f"/api/folders/{folder_id}")
        self.assertEqual(del_res.status_code, 200)

        # Note is now in Home
        get_note = self.client.get(f"/api/notes/{note_data['id']}")
        self.assertEqual(get_note.status_code, 200)
        self.assertEqual(get_note.get_json()["folder_id"], 1)
        self.assertEqual(get_note.get_json()["folder_name"], "Home")

        # 10. Cannot delete Home folder
        del_home = self.client.delete("/api/folders/1")
        self.assertEqual(del_home.status_code, 400)

    def test_nested_folders_api(self):
        # Create root folder
        root_res = self.client.post(
            "/api/folders",
            data=json.dumps({"name": "Academics"}),
            content_type="application/json"
        )
        self.assertEqual(root_res.status_code, 201)
        root_id = root_res.get_json()["id"]

        # Create subfolder
        sub_res = self.client.post(
            "/api/folders",
            data=json.dumps({"name": "Physics", "parent_id": root_id}),
            content_type="application/json"
        )
        self.assertEqual(sub_res.status_code, 201)
        sub_id = sub_res.get_json()["id"]
        self.assertEqual(sub_res.get_json()["parent_id"], root_id)
        self.assertEqual(sub_res.get_json()["depth"], 1)

        # Create note in subfolder
        note_res = self.client.post(
            "/api/notes",
            data=json.dumps({"title": "Quantum Lecture", "folder_id": sub_id}),
            content_type="application/json"
        )
        self.assertEqual(note_res.status_code, 201)
        note_data = note_res.get_json()
        self.assertEqual(note_data["folder_path"], "Academics / Physics")

        # Query root folder with subfolders=true
        sub_query = self.client.get(f"/api/notes?folder_id={root_id}&subfolders=true")
        self.assertEqual(sub_query.status_code, 200)
        self.assertEqual(len(sub_query.get_json()), 1)
        self.assertEqual(sub_query.get_json()[0]["title"], "Quantum Lecture")

        # Query root folder without subfolders
        no_sub_query = self.client.get(f"/api/notes?folder_id={root_id}")
        self.assertEqual(no_sub_query.status_code, 200)
        self.assertEqual(len(no_sub_query.get_json()), 0)

        # Circular reference API check: cannot set Academics parent to Physics
        circ_res = self.client.put(
            f"/api/folders/{root_id}",
            data=json.dumps({"name": "Academics", "parent_id": sub_id}),
            content_type="application/json"
        )
        self.assertEqual(circ_res.status_code, 400)

    def test_universal_search_api(self):
        # 1. Create nested structure: Science -> Biology -> Genetics
        sci_res = self.client.post("/api/folders", data=json.dumps({"name": "Science"}), content_type="application/json")
        sci_id = sci_res.get_json()["id"]

        bio_res = self.client.post("/api/folders", data=json.dumps({"name": "Biology", "parent_id": sci_id}), content_type="application/json")
        bio_id = bio_res.get_json()["id"]

        gen_res = self.client.post("/api/folders", data=json.dumps({"name": "Genetics", "parent_id": bio_id}), content_type="application/json")
        gen_id = gen_res.get_json()["id"]

        # 2. Add notes
        self.client.post("/api/notes", data=json.dumps({"title": "DNA Structure", "content": "Double helix model", "folder_id": gen_id}), content_type="application/json")
        self.client.post("/api/notes", data=json.dumps({"title": "Cell Biology", "content": "Mitochondria power", "folder_id": bio_id}), content_type="application/json")
        self.client.post("/api/notes", data=json.dumps({"title": "Home Note", "content": "Buy notebook", "folder_id": 1}), content_type="application/json")

        # 3. Universal search: query without folder_id finds note in Genetics subfolder
        res_univ = self.client.get("/api/notes?q=helix")
        self.assertEqual(res_univ.status_code, 200)
        items = res_univ.get_json()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "DNA Structure")
        self.assertEqual(items[0]["folder_path"], "Science / Biology / Genetics")

        # 4. Universal search parameter overrides folder_id=1 (Home)
        res_override = self.client.get("/api/notes?q=helix&folder_id=1&universal=true")
        self.assertEqual(res_override.status_code, 200)
        self.assertEqual(len(res_override.get_json()), 1)
        self.assertEqual(res_override.get_json()[0]["title"], "DNA Structure")

        # 5. Scoped folder search with query automatically includes subfolder results
        res_scoped = self.client.get(f"/api/notes?q=Mitochondria&folder_id={sci_id}")
        self.assertEqual(res_scoped.status_code, 200)
        self.assertEqual(len(res_scoped.get_json()), 1)
        self.assertEqual(res_scoped.get_json()[0]["title"], "Cell Biology")

        # 6. Searching by subfolder name matches note inside it
        res_by_name = self.client.get("/api/notes?q=Genetics")
        self.assertEqual(res_by_name.status_code, 200)
        self.assertEqual(len(res_by_name.get_json()), 1)
        self.assertEqual(res_by_name.get_json()[0]["title"], "DNA Structure")

    def test_notes_api_crud(self):
        # Create Note
        create_res = self.client.post(
            "/api/notes",
            data=json.dumps({
                "title": "API Test Note",
                "content": "Testing via Flask test client",
                "tags": "api, test",
                "color": "amber",
                "is_pinned": True
            }),
            content_type="application/json"
        )
        self.assertEqual(create_res.status_code, 201)
        data = create_res.get_json()
        note_id = data["id"]
        self.assertEqual(data["title"], "API Test Note")
        self.assertEqual(data["color"], "amber")
        self.assertTrue(data["is_pinned"])
        self.assertEqual(data["folder_id"], 1)

        # Fetch Note
        get_res = self.client.get(f"/api/notes/{note_id}")
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.get_json()["id"], note_id)

        # Update Note
        put_res = self.client.put(
            f"/api/notes/{note_id}",
            data=json.dumps({"title": "Updated API Note", "color": "rose"}),
            content_type="application/json"
        )
        self.assertEqual(put_res.status_code, 200)
        self.assertEqual(put_res.get_json()["title"], "Updated API Note")
        self.assertEqual(put_res.get_json()["color"], "rose")

        # Toggle Pin
        pin_res = self.client.post(f"/api/notes/{note_id}/pin")
        self.assertEqual(pin_res.status_code, 200)
        self.assertFalse(pin_res.get_json()["is_pinned"])

        # List Notes
        list_res = self.client.get("/api/notes?q=Updated")
        self.assertEqual(list_res.status_code, 200)
        self.assertEqual(len(list_res.get_json()), 1)

        # Delete Note
        del_res = self.client.delete(f"/api/notes/{note_id}")
        self.assertEqual(del_res.status_code, 200)

        # Verify 404
        get_after_del = self.client.get(f"/api/notes/{note_id}")
        self.assertEqual(get_after_del.status_code, 404)

    def test_export_and_import_api(self):
        # Create a note
        self.client.post(
            "/api/notes",
            data=json.dumps({"title": "Backup Me", "content": "Sample"}),
            content_type="application/json"
        )

        export_res = self.client.get("/api/export")
        self.assertEqual(export_res.status_code, 200)
        backup_data = export_res.get_json()
        self.assertEqual(backup_data["count"], 1)

        import_res = self.client.post(
            "/api/import",
            data=json.dumps(backup_data),
            content_type="application/json"
        )
        self.assertEqual(import_res.status_code, 200)
        self.assertTrue(import_res.get_json()["success"])
        self.assertEqual(import_res.get_json()["imported"], 1)


class TestAuthenticationAndMultiTenancy(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_auth.db")
        self.app = create_app(db_path=self.db_path)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

    def test_unauthenticated_api_rejection(self):
        # Without logging in, all data APIs must reject with 401
        self.assertEqual(self.client.get("/api/folders").status_code, 401)
        self.assertEqual(self.client.get("/api/notes").status_code, 401)
        self.assertEqual(self.client.get("/api/tags").status_code, 401)
        self.assertEqual(self.client.get("/api/export").status_code, 401)
        self.assertEqual(self.client.post("/api/folders", json={"name": "Test"}).status_code, 401)
        self.assertEqual(self.client.post("/api/notes", json={"title": "Test"}).status_code, 401)

    def test_user_registration_and_login(self):
        # 1. Register Alice
        reg_res = self.client.post(
            "/api/auth/register",
            json={"username": "alice", "email": "alice@example.com", "password": "password123"}
        )
        self.assertEqual(reg_res.status_code, 201)
        reg_data = reg_res.get_json()
        self.assertTrue(reg_data["success"])
        self.assertEqual(reg_data["user"]["username"], "alice")

        # 2. Check current session
        me_res = self.client.get("/api/auth/me")
        self.assertEqual(me_res.status_code, 200)
        self.assertTrue(me_res.get_json()["logged_in"])
        self.assertEqual(me_res.get_json()["user"]["username"], "alice")

        # 3. Log out
        out_res = self.client.post("/api/auth/logout")
        self.assertEqual(out_res.status_code, 200)
        me_out = self.client.get("/api/auth/me")
        self.assertFalse(me_out.get_json()["logged_in"])

        # 4. Log in using email
        login_res = self.client.post(
            "/api/auth/login",
            json={"username": "alice@example.com", "password": "password123"}
        )
        self.assertEqual(login_res.status_code, 200)
        self.assertTrue(login_res.get_json()["success"])

        # 5. Invalid password rejected
        self.client.post("/api/auth/logout")
        bad_login = self.client.post(
            "/api/auth/login",
            json={"username": "alice", "password": "wrongpassword"}
        )
        self.assertEqual(bad_login.status_code, 401)

    def test_duplicate_registration_rejected(self):
        self.client.post(
            "/api/auth/register",
            json={"username": "alice", "email": "alice@example.com", "password": "password123"}
        )
        # Duplicate username
        dup_user = self.client.post(
            "/api/auth/register",
            json={"username": "alice", "email": "other@example.com", "password": "password123"}
        )
        self.assertEqual(dup_user.status_code, 409)

        # Duplicate email
        dup_email = self.client.post(
            "/api/auth/register",
            json={"username": "bob", "email": "alice@example.com", "password": "password123"}
        )
        self.assertEqual(dup_email.status_code, 409)

    def test_multi_user_isolation(self):
        # Alice registers and creates a folder & note
        client_alice = self.app.test_client()
        client_alice.post(
            "/api/auth/register",
            json={"username": "alice", "email": "alice@example.com", "password": "alicepass123"}
        )
        f_res = client_alice.post("/api/folders", json={"name": "Alice Private Project"})
        self.assertEqual(f_res.status_code, 201)
        alice_folder_id = f_res.get_json()["id"]

        n_res = client_alice.post(
            "/api/notes",
            json={
                "title": "Alice Confidential Notes",
                "content": "Secret cryptographic keys",
                "folder_id": alice_folder_id,
                "tags": "secret, alice"
            }
        )
        self.assertEqual(n_res.status_code, 201)
        alice_note_id = n_res.get_json()["id"]

        # Bob registers
        client_bob = self.app.test_client()
        client_bob.post(
            "/api/auth/register",
            json={"username": "bob", "email": "bob@example.com", "password": "bobpass123"}
        )

        # Bob lists folders: should NOT see Alice's folder
        bob_folders = client_bob.get("/api/folders").get_json()
        bob_folder_names = [f["name"] for f in bob_folders]
        self.assertNotIn("Alice Private Project", bob_folder_names)
        self.assertIn("Home", bob_folder_names)

        # Bob lists notes: should NOT see Alice's note
        bob_notes = client_bob.get("/api/notes").get_json()
        self.assertEqual(len(bob_notes), 0)

        # Bob tries universal search for Alice's note title
        search_res = client_bob.get("/api/notes?q=Confidential&universal=true").get_json()
        self.assertEqual(len(search_res), 0)

        # Bob tries direct GET, PUT, DELETE of Alice's note ID -> must be 404
        self.assertEqual(client_bob.get(f"/api/notes/{alice_note_id}").status_code, 404)
        self.assertEqual(
            client_bob.put(f"/api/notes/{alice_note_id}", json={"title": "Hacked"}).status_code,
            404
        )
        self.assertEqual(client_bob.delete(f"/api/notes/{alice_note_id}").status_code, 404)

        # Bob tries to delete Alice's folder -> must be 404
        self.assertEqual(client_bob.delete(f"/api/folders/{alice_folder_id}").status_code, 404)

        # Alice's note still exists intact
        alice_check = client_alice.get(f"/api/notes/{alice_note_id}")
        self.assertEqual(alice_check.status_code, 200)
        self.assertEqual(alice_check.get_json()["title"], "Alice Confidential Notes")

    def test_password_reset_flow(self):
        from email_service import get_last_dev_code

        # Request reset code for demo account
        forgot_res = self.client.post(
            "/api/auth/forgot-password",
            json={"email": "demo@example.com"}
        )
        self.assertEqual(forgot_res.status_code, 200)
        code = forgot_res.get_json().get("dev_code") or get_last_dev_code("demo@example.com")
        self.assertIsNotNone(code)
        self.assertEqual(len(code), 6)

        # Try reset with invalid code -> 400
        bad_code_res = self.client.post(
            "/api/auth/reset-password",
            json={"email": "demo@example.com", "code": "000000", "new_password": "newpassword123"}
        )
        self.assertEqual(bad_code_res.status_code, 400)

        # Try reset with short password -> 400
        short_pw_res = self.client.post(
            "/api/auth/reset-password",
            json={"email": "demo@example.com", "code": code, "new_password": "123"}
        )
        self.assertEqual(short_pw_res.status_code, 400)

        # Valid reset
        reset_res = self.client.post(
            "/api/auth/reset-password",
            json={"email": "demo@example.com", "code": code, "new_password": "newpassword123"}
        )
        self.assertEqual(reset_res.status_code, 200)
        self.assertTrue(reset_res.get_json()["success"])

        # Old password no longer works
        old_login = self.client.post(
            "/api/auth/login",
            json={"username": "demo", "password": "demo123"}
        )
        self.assertEqual(old_login.status_code, 401)

        # New password works
        new_login = self.client.post(
            "/api/auth/login",
            json={"username": "demo", "password": "newpassword123"}
        )
        self.assertEqual(new_login.status_code, 200)

        # Re-using the same code must fail (one-time use)
        reuse_res = self.client.post(
            "/api/auth/reset-password",
            json={"email": "demo@example.com", "code": code, "new_password": "anotherpassword"}
        )
        self.assertEqual(reuse_res.status_code, 400)

    def test_password_reset_nonexistent_email(self):
        res = self.client.post(
            "/api/auth/forgot-password",
            json={"email": "doesnotexist@example.com"}
        )
        self.assertEqual(res.status_code, 404)


if __name__ == "__main__":
    unittest.main()
