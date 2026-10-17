
import pytest
import database
from app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Use a separate database for each test.
    test_db = tmp_path / "test_elderguard.db"
    monkeypatch.setattr(database, "DATABASE_NAME", str(test_db))

    database.initialize_database()

    connection = database.get_connection()

    try:
        connection.executemany("""
            INSERT INTO customers
                (customer_id, name, average_transaction_amount)
            VALUES (?, ?, ?)
        """, [
            (101, "Ravi Kumar", 2250.0),
            (102, "Priya Sharma", 30000.0)
        ])

        connection.executemany("""
            INSERT INTO transactions
                (customer_id, amount, recipient, risk_level, status)
            VALUES (?, ?, ?, 'PENDING', 'HISTORICAL')
        """, [
            (101, 2000.0, "Local Grocery"),
            (102, 25000.0, "Known Recipient B")
        ])

        connection.commit()
    finally:
        connection.close()

    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-only-secret-key"

    with app.test_client() as test_client:
        # Simulate an authenticated user for protected API tests.
        with test_client.session_transaction() as session:
            session["user_id"] = 1
            session["user_name"] = "Test User"

        yield test_client


def test_health_check(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json["status"] == "success"


def test_get_customers(client):
    response = client.get("/api/customers")

    assert response.status_code == 200
    assert response.json["count"] == 2


def test_get_transactions(client):
    response = client.get("/api/transactions")

    assert response.status_code == 200
    assert response.json["count"] == 2


def test_get_customer_transactions(client):
    response = client.get("/api/customers/101/transactions")

    assert response.status_code == 200
    assert response.json["customer"]["name"] == "Ravi Kumar"
    assert response.json["count"] == 1


def test_unknown_customer(client):
    response = client.get("/api/customers/999/transactions")

    assert response.status_code == 404
    assert response.json["status"] == "error"


def test_high_risk_transaction(client):
    response = client.post("/api/transactions/assess", json={
        "customer_id": 101,
        "amount": 45000,
        "recipient": "New Recipient"
    })

    assert response.status_code == 201
    assert response.json["risk_level"] == "HIGH"
    assert response.json["risk_score"] == 3
    assert response.json["recommended_action"] == "HOLD_FOR_REVIEW"


def test_low_risk_transaction(client):
    response = client.post("/api/transactions/assess", json={
        "customer_id": 101,
        "amount": 2000,
        "recipient": "Local Grocery"
    })

    assert response.status_code == 201
    assert response.json["risk_level"] == "LOW"
    assert response.json["recommended_action"] == "APPROVE"


def test_new_recipient_requires_verification(client):
    response = client.post("/api/transactions/assess", json={
        "customer_id": 101,
        "amount": 2000,
        "recipient": "New Recipient B"
    })

    assert response.status_code == 201
    assert response.json["risk_level"] == "MEDIUM"
    assert response.json["recommended_action"] == "VERIFY_RECIPIENT"


def test_unknown_customer_cannot_submit_transaction(client):
    response = client.post("/api/transactions/assess", json={
        "customer_id": 999,
        "amount": 2000,
        "recipient": "Local Grocery"
    })

    assert response.status_code == 404


def test_negative_amount_is_rejected(client):
    response = client.post("/api/transactions/assess", json={
        "customer_id": 101,
        "amount": -100,
        "recipient": "Local Grocery"
    })

    assert response.status_code == 400

def test_missing_recipient_is_rejected(client):
    response = client.post("/api/transactions/assess", json={
        "customer_id": 101,
        "amount": 2000
    })

    assert response.status_code == 400


def test_assessment_is_saved(client):
    response = client.post("/api/transactions/assess", json={
        "customer_id": 101,
        "amount": 45000,
        "recipient": "Another New Recipient"
    })

    assert response.status_code == 201

    transaction_id = response.json["transaction_id"]

    connection = database.get_connection()

    try:
        saved = connection.execute("""
            SELECT customer_id, amount, risk_level, status
            FROM transactions
            WHERE transaction_id = ?
        """, (transaction_id,)).fetchone()
    finally:
        connection.close()

    assert saved is not None
    assert saved["customer_id"] == 101
    assert saved["amount"] == 45000
    assert saved["risk_level"] == "HIGH"
    assert saved["status"] == "PENDING_REVIEW"


def test_protected_endpoint_requires_authentication(client):
    # Remove the authenticated session created by the fixture.
    with client.session_transaction() as session:
        session.clear()

    response = client.get("/api/customers")

    assert response.status_code == 401
    assert response.json["status"] == "error"
    assert response.json["message"] == "Authentication required"


def test_current_user_requires_authentication(client):
    # The /api/auth/me route should reject a missing session.
    with client.session_transaction() as session:
        session.clear()

    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json["status"] == "error"


def test_register_new_user(client):
    response = client.post("/api/auth/register", json={
        "name": "Test User",
        "phone": "9876543210",
        "email": "testuser@example.com",
        "password": "TestPass123!"
    })

    assert response.status_code == 201
    assert response.json["status"] == "success"


def test_login_with_valid_credentials(client):
    # Register the user in the isolated test database.
    client.post("/api/auth/register", json={
        "name": "Login Test",
        "phone": "9876543211",
        "email": "login@example.com",
        "password": "SecurePass123!"
    })

    # Log in through the actual API route.
    response = client.post("/api/auth/login", json={
        "email": "login@example.com",
        "password": "SecurePass123!"
    })

    assert response.status_code == 200
    assert response.json["status"] == "success"
    assert response.json["user"]["email"] == "login@example.com"

    # Verify that the login session is active.
    me_response = client.get("/api/auth/me")
    assert me_response.status_code == 200
    assert me_response.json["user"]["name"] == "Login Test"


def test_login_with_invalid_password(client):
    client.post("/api/auth/register", json={
        "name": "Login Test",
        "phone": "9876543212",
        "email": "invalidpass@example.com",
        "password": "CorrectPass123!"
    })

    response = client.post("/api/auth/login", json={
        "email": "invalidpass@example.com",
        "password": "WrongPass123!"
    })

    assert response.status_code == 401
    assert response.json["status"] == "error"
    assert response.json["message"] == "Invalid email or password"


def test_logout_clears_session(client):
    # The fixture starts with a simulated authenticated session.
    response = client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.json["status"] == "success"

    # A protected endpoint should reject the cleared session.
    customers_response = client.get("/api/customers")
    assert customers_response.status_code == 401

    # The current-user endpoint should also reject it.
    me_response = client.get("/api/auth/me")
    assert me_response.status_code == 401
