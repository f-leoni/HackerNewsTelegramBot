import pytest
import json
import sqlite3
from io import BytesIO
from unittest.mock import Mock
from contextlib import contextmanager # Import the correct decorator

from webserver.server import BookmarkHandler
from shared.database import init_database
from werkzeug.security import generate_password_hash

# --- Test Fixture Setup ---

@pytest.fixture
def test_client(mocker):
    """
    A comprehensive fixture to set up an in-memory database,
    create a test user and session, and provide a client to make simulated requests.
    """
    # Use a shared in-memory database URI. The connection must be kept open.
    db_uri = 'file:memdb_test?mode=memory&cache=shared'
    conn = sqlite3.connect(db_uri, uri=True, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()

    # 1. Mock the db_connection context manager in the server module
    # This is safer than patching a global variable like DB_PATH.
    # We replace it with a context manager that yields our in-memory cursor from the shared connection.
    @contextmanager # Use the standard library decorator
    def mock_db_context():
        yield cursor
    mocker.patch('webserver.server.db_connection', mock_db_context)

    # 2. Initialize the database schema in memory. Keep this connection alive.
    init_database(conn) # Pass the connection to init_database

    # 3. Create a test user. Use INSERT OR IGNORE to prevent errors on re-runs.
    test_user = {'id': 1, 'username': 'testuser', 'password': 'password123'}
    password_hash = generate_password_hash(test_user['password'])
    cursor.execute("INSERT OR IGNORE INTO users (id, username, password_hash) VALUES (?, ?, ?)",
                   (test_user['id'], test_user['username'], password_hash))

    # 4. Create a valid session for the test user. Use INSERT OR IGNORE.
    session_id = "test-session-id-12345"
    from datetime import datetime, timedelta
    expires_at = datetime.now() + timedelta(days=1)
    cursor.execute("INSERT OR IGNORE INTO sessions (session_id, user_id, expires_at) VALUES (?, ?, ?)",
                   (session_id, test_user['id'], expires_at))
    conn.commit()

    # 5. Define a helper function to simulate requests
    def make_request(method, path, body=None, headers=None, return_headers=False):
        if headers is None:
            headers = {}

        # Simulate the request environment
        request_line = f"{method} {path} HTTP/1.1"
        if body is None:
            payload = b''
        elif isinstance(body, (bytes, bytearray)):
            payload = bytes(body)
        elif isinstance(body, str):
            payload = body.encode('utf-8')
        else:
            payload = json.dumps(body).encode('utf-8')

        rfile = BytesIO(payload)
        wfile = BytesIO()

        # Mock the server and request objects that the handler expects
        request = Mock()
        request.makefile.return_value = rfile

        # Create an "empty" instance of the handler to avoid the base class's parsing logic
        handler = BookmarkHandler.__new__(BookmarkHandler)
        handler.rfile = rfile
        handler.wfile = wfile
        handler.headers = headers
        handler.command = method
        handler.path = path
        handler.requestline = request_line

        # Mock send_response and send_header to capture status and headers
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()

        # Dispatch to the correct do_* method
        handler_method = getattr(handler, f'do_{method}')
        handler_method()

        # Capture and return the response
        status_code = handler.send_response.call_args[0][0]
        response_body = wfile.getvalue()
        sent_headers = {}
        for header_call in handler.send_header.call_args_list:
            key, value = header_call[0]
            sent_headers[key] = value
        try:
            response_json = json.loads(response_body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            response_json = None

        if return_headers:
            return status_code, response_json, response_body.decode('utf-8'), sent_headers

        return status_code, response_json, response_body.decode('utf-8')

    # Yield the request function and the session ID to the tests
    yield make_request, session_id, test_user['id'], conn
    
    # Teardown: close the main connection after all tests in the session are done.
    conn.close()


# --- Authentication Tests ---

def test_unauthenticated_access_redirects_to_login(test_client):
    """Tests that accessing a protected route without a session redirects to /login."""
    make_request, _, _, _ = test_client
    status, _, _ = make_request('GET', '/')
    assert status == 302 # Redirect

def test_authenticated_access_succeeds(test_client):
    """Tests that a valid session cookie allows access."""
    make_request, session_id, _, _ = test_client
    headers = {'Cookie': f'session_id={session_id}'}
    status, _, _ = make_request('GET', '/', headers=headers)
    assert status == 200


def test_login_is_case_insensitive_for_username(test_client):
    """Username casing should not affect successful login."""
    make_request, _, _, _ = test_client
    body = 'username=TESTUSER&password=password123'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Content-Length': str(len(body)),
    }

    status, _, _, response_headers = make_request('POST', '/login', body=body, headers=headers, return_headers=True)

    assert status == 302
    assert response_headers.get('Location') == '/'
    assert 'session_id=' in response_headers.get('Set-Cookie', '')


# --- API Endpoint Tests ---

def test_add_bookmark_success(test_client):
    """Tests successfully adding a new bookmark via POST /api/bookmarks."""
    make_request, session_id, user_id, conn = test_client
    headers = {
        'Cookie': f'session_id={session_id}',
        'Content-Type': 'application/json',
        'Content-Length': '100' # Dummy length
    }
    bookmark_data = {'url': 'https://newsite.com', 'title': 'New Site'}

    status, response_json, _ = make_request('POST', '/api/bookmarks', body=bookmark_data, headers=headers)

    assert status == 201 # Created
    assert response_json['url'] == 'https://newsite.com'
    assert response_json['title'] == 'New Site'
    assert response_json['domain'] == 'newsite.com'

    # Verify it was actually saved in the database
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM bookmarks WHERE url = ? AND user_id = ?", ('https://newsite.com', user_id))
    assert cursor.fetchone()[0] == 1

def test_add_bookmark_duplicate_url_fails(test_client):
    """Tests that adding a bookmark with a duplicate URL returns a 409 Conflict."""
    make_request, session_id, user_id, conn = test_client
    headers = {
        'Cookie': f'session_id={session_id}',
        'Content-Type': 'application/json',
        'Content-Length': '100'
    }
    bookmark_data = {'url': 'https://duplicate.com', 'title': 'Duplicate'}

    # Add it once
    make_request('POST', '/api/bookmarks', body=bookmark_data, headers=headers)

    # Try to add it again
    status, response_json, _ = make_request('POST', '/api/bookmarks', body=bookmark_data, headers=headers)

    assert status == 409 # Conflict
    assert 'URL already exists' in response_json['error']

def test_delete_bookmark_success(test_client):
    """Tests successfully deleting a bookmark via DELETE /api/bookmarks/<id>."""
    make_request, session_id, user_id, conn = test_client
    headers = {'Cookie': f'session_id={session_id}'}

    # First, add a bookmark to delete
    cursor = conn.cursor()
    cursor.execute("INSERT INTO bookmarks (id, url, user_id) VALUES (?, ?, ?)", (99, 'https://todelete.com', user_id))
    conn.commit()

    # Now, delete it
    status, response_json, _ = make_request('DELETE', '/api/bookmarks/99', headers=headers)

    assert status == 200
    assert response_json['status'] == 'deleted'

    # Verify it's gone from the database
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM bookmarks WHERE id = 99")
    assert cursor.fetchone()[0] == 0

def test_update_bookmark_success(test_client):
    """Tests successfully updating a bookmark via PUT /api/bookmarks/<id>."""
    make_request, session_id, user_id, conn = test_client
    headers = {
        'Cookie': f'session_id={session_id}',
        'Content-Type': 'application/json',
        'Content-Length': '100'
    }
    # Add a bookmark to update
    cursor = conn.cursor()
    cursor.execute("INSERT INTO bookmarks (id, url, title, user_id) VALUES (?, ?, ?, ?)", (101, 'https://toupdate.com', 'Old Title', user_id))
    conn.commit()

    update_data = {'title': 'New Updated Title', 'is_read': 1}
    status, response_json, _ = make_request('PUT', '/api/bookmarks/101', body=update_data, headers=headers)

    assert status == 200
    assert response_json['title'] == 'New Updated Title'
    assert response_json['is_read'] == 1

    # Verify the change in the database
    cursor = conn.cursor()
    cursor.execute("SELECT title, is_read FROM bookmarks WHERE id = 101")
    result = cursor.fetchone()
    assert result[0] == 'New Updated Title'
    assert result[1] == 1


def test_export_html_success_headers_and_body(test_client):
    """Tests HTML export endpoint returns attachment headers and expected body."""
    make_request, session_id, user_id, conn = test_client
    headers = {'Cookie': f'session_id={session_id}'}

    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO bookmarks (id, user_id, url, title, description, domain, tags, is_read) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (111, user_id, 'https://export-test.example', 'Export Test Title', 'Export Description', 'export-test.example', '["tag1"]', 0),
    )
    conn.commit()

    status, _, body, response_headers = make_request('GET', '/api/export/html', headers=headers, return_headers=True)

    assert status == 200
    assert response_headers.get('Content-Type', '').startswith('text/html')
    assert 'attachment; filename="bookmarks.html"' in response_headers.get('Content-Disposition', '')
    assert '<title>Bookmarks Export</title>' in body
    assert '/static/export-page.css' in body
    assert 'Export Test Title' in body


def test_head_does_not_write_response_body(test_client):
    """HEAD requests must return headers only, without a response body."""
    make_request, session_id, _, _ = test_client
    headers = {'Cookie': f'session_id={session_id}'}

    status, response_json, body = make_request('HEAD', '/api/bookmarks', headers=headers)

    assert status == 200
    assert response_json is None
    assert body == ''


def test_scroll_endpoint_handles_malformed_query_params(test_client):
    """Scroll endpoint should clamp/fallback invalid query params instead of failing."""
    make_request, session_id, _, _ = test_client
    headers = {'Cookie': f'session_id={session_id}'}

    status, _, body = make_request(
        'GET',
        '/ui/bookmarks/scroll?offset=abc&limit=not-a-number&hide_read=definitely-not-bool',
        headers=headers,
    )

    assert status == 200
    assert 'loadMoreTrigger' in body
