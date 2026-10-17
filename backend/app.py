import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from flask import Flask, jsonify, request, session
from database import get_connection
import os
from dotenv import load_dotenv
from functools import wraps

app = Flask(__name__)

def login_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if session.get("user_id") is None:
            return jsonify({
                "status": "error",
                "message": "Authentication required"
            }), 401

        return view_function(*args, **kwargs)

    return wrapped_view

load_dotenv()

app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY")

if not app.config["SECRET_KEY"]:
    raise RuntimeError("Set the FLASK_SECRET_KEY environment variable")

CORS(
    app,
    supports_credentials=True,
    resources={
        r"/api/*": {
            "origins": "http://127.0.0.1:5500"
        }
    }
)

def ensure_support_tables(connection):
    """Create additive tables only; existing customers/transactions/users are preserved."""
    connection.execute("""
        CREATE TABLE IF NOT EXISTS customer_profiles (
            customer_id INTEGER PRIMARY KEY,
            age INTEGER,
            guardian_name TEXT,
            guardian_relation TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS security_alerts (
            alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER NOT NULL UNIQUE,
            alert_type TEXT NOT NULL,
            message TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'OPEN',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            resolved_at TEXT,
            resolved_by TEXT
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            actor TEXT NOT NULL,
            event_type TEXT NOT NULL,
            target_ref TEXT,
            details TEXT,
            event_hash TEXT
        )
    """)

def write_audit(connection, event_type, target_ref=None, details="", actor=None):
    import hashlib
    from datetime import datetime, timezone
    actor = actor or str(session.get("user_name") or "System")
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    previous = connection.execute(
        "SELECT event_hash FROM audit_logs ORDER BY log_id DESC LIMIT 1"
    ).fetchone()
    previous_hash = previous["event_hash"] if previous and previous["event_hash"] else "GENESIS"
    payload = f"{timestamp}|{actor}|{event_type}|{target_ref or ''}|{details}|{previous_hash}"
    event_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    connection.execute(
        "INSERT INTO audit_logs (created_at, actor, event_type, target_ref, details, event_hash) VALUES (?, ?, ?, ?, ?, ?)",
        (timestamp, actor, event_type, str(target_ref) if target_ref is not None else None, details, event_hash)
    )

@app.route("/")
def home():
    return """
    <h1>Welcome to ElderGuard Z</h1>
    <p>Real-Time AI for Critical Decisions</p>
    <h2>Backend Status: Running</h2>
    <ul>
        <li><a href="/api/health">Health Check</a></li>
        <li><a href="/api/customers">View Customers</a></li>
        <li><a href="/api/transactions">View Transactions</a></li>
    </ul>
    """

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "success",
        "message": "ElderGuard Z backend is running"
    })


@app.route("/api/customers", methods=["GET"])
@login_required
def get_customers():
    connection = get_connection()

    try:
        ensure_support_tables(connection)
        rows = connection.execute("""
            SELECT c.customer_id, c.name, c.average_transaction_amount,
                   p.age, p.guardian_name, p.guardian_relation,
                   COALESCE(tx.high_risk_transactions, 0) AS high_risk_transactions,
                   COALESCE(tx.pending_transactions, 0) AS pending_transactions
            FROM customers AS c
            LEFT JOIN customer_profiles AS p ON p.customer_id = c.customer_id
            LEFT JOIN (
                SELECT customer_id,
                       SUM(CASE WHEN UPPER(risk_level) = 'HIGH' THEN 1 ELSE 0 END) AS high_risk_transactions,
                       SUM(CASE WHEN UPPER(status) IN ('PENDING_REVIEW','PENDING_VERIFICATION','HOLD_FOR_REVIEW','VERIFY_RECIPIENT') THEN 1 ELSE 0 END) AS pending_transactions
                FROM transactions
                GROUP BY customer_id
            ) AS tx ON tx.customer_id = c.customer_id
            ORDER BY c.customer_id
        """).fetchall()

        customers = [dict(row) for row in rows]

        return jsonify({
            "status": "success",
            "count": len(customers),
            "customers": customers
        })

    finally:
        connection.close()


@app.route("/api/transactions", methods=["GET"])
@login_required
def get_transactions():
    connection = get_connection()

    try:
        rows = connection.execute("""
            SELECT t.transaction_id, t.customer_id, c.name AS customer_name,
                   t.amount, t.recipient, t.risk_level, t.status, t.created_at
            FROM transactions AS t
            LEFT JOIN customers AS c ON c.customer_id = t.customer_id
            ORDER BY t.transaction_id DESC
        """).fetchall()

        transactions = [dict(row) for row in rows]

        return jsonify({
            "status": "success",
            "count": len(transactions),
            "transactions": transactions
        })

    finally:
        connection.close()


@app.route("/api/customers", methods=["POST"])
@login_required
def create_customer():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"status": "error", "message": "A JSON request body is required"}), 400
    name = data.get("name")
    age = data.get("age")
    guardian_name = str(data.get("guardian_name") or "").strip()
    guardian_relation = str(data.get("guardian_relation") or "").strip()
    baseline = data.get("average_transaction_amount", 5000)
    if not isinstance(name, str) or not name.strip():
        return jsonify({"status": "error", "message": "Customer name is required"}), 400
    if isinstance(age, bool) or not isinstance(age, int) or not 18 <= age <= 120:
        return jsonify({"status": "error", "message": "Age must be an integer between 18 and 120"}), 400
    if isinstance(baseline, bool) or not isinstance(baseline, (int, float)) or baseline <= 0:
        return jsonify({"status": "error", "message": "Average transaction amount must be greater than zero"}), 400
    connection = get_connection()
    try:
        ensure_support_tables(connection)
        cursor = connection.execute(
            "INSERT INTO customers (name, average_transaction_amount) VALUES (?, ?)",
            (name.strip(), float(baseline))
        )
        customer_id = cursor.lastrowid
        connection.execute(
            "INSERT INTO customer_profiles (customer_id, age, guardian_name, guardian_relation) VALUES (?, ?, ?, ?)",
            (customer_id, age, guardian_name or None, guardian_relation or None)
        )
        write_audit(connection, "CUSTOMER_REGISTERED", f"CUST-{customer_id}", f"Registered {name.strip()} (age {age})")
        connection.commit()
        return jsonify({"status": "success", "message": "Senior account registered.", "customer": {"customer_id": customer_id, "name": name.strip(), "age": age, "guardian_name": guardian_name, "guardian_relation": guardian_relation, "average_transaction_amount": float(baseline)}}), 201
    except Exception:
        connection.rollback()
        app.logger.exception("Customer registration failed")
        return jsonify({"status": "error", "message": "Could not register customer. Check the backend log."}), 500
    finally:
        connection.close()

@app.route("/api/transactions/<int:transaction_id>/approve", methods=["POST"])
@login_required
def approve_transaction(transaction_id):
    connection = get_connection()
    try:
        ensure_support_tables(connection)
        tx = connection.execute("SELECT transaction_id, status, risk_level FROM transactions WHERE transaction_id = ?", (transaction_id,)).fetchone()
        if tx is None:
            return jsonify({"status": "error", "message": "Transaction not found"}), 404
        current = str(tx["status"] or "").upper()
        if current not in {"PENDING_REVIEW", "PENDING_VERIFICATION", "HOLD_FOR_REVIEW", "VERIFY_RECIPIENT"}:
            return jsonify({"status": "error", "message": f"Transaction cannot be approved from status {current}"}), 409
        connection.execute("UPDATE transactions SET status = 'APPROVED' WHERE transaction_id = ?", (transaction_id,))
        connection.execute("UPDATE security_alerts SET status = 'RESOLVED', resolved_at = CURRENT_TIMESTAMP, resolved_by = ? WHERE transaction_id = ? AND status = 'OPEN'", (str(session.get("user_name") or "Operator"), transaction_id))
        write_audit(connection, "TRANSACTION_APPROVED", f"TX-{transaction_id}", "Operator approved the transaction in the ElderGuard Z application. No external payment network was invoked.")
        connection.commit()
        return jsonify({"status": "success", "message": "Transaction approved in ElderGuard Z. The saved status is APPROVED; no external payment was executed.", "transaction_id": transaction_id, "transaction_status": "APPROVED"})
    finally:
        connection.close()

@app.route("/api/transactions/<int:transaction_id>/cancel", methods=["POST"])
@login_required
def cancel_transaction(transaction_id):
    connection = get_connection()
    try:
        ensure_support_tables(connection)
        tx = connection.execute("SELECT transaction_id, status FROM transactions WHERE transaction_id = ?", (transaction_id,)).fetchone()
        if tx is None:
            return jsonify({"status": "error", "message": "Transaction not found"}), 404
        current = str(tx["status"] or "").upper()
        if current not in {"PENDING_REVIEW", "PENDING_VERIFICATION", "HOLD_FOR_REVIEW", "VERIFY_RECIPIENT"}:
            return jsonify({"status": "error", "message": f"Transaction cannot be cancelled from status {current}"}), 409
        connection.execute("UPDATE transactions SET status = 'CANCELLED' WHERE transaction_id = ?", (transaction_id,))
        connection.execute("UPDATE security_alerts SET status = 'RESOLVED', resolved_at = CURRENT_TIMESTAMP, resolved_by = ? WHERE transaction_id = ? AND status = 'OPEN'", (str(session.get("user_name") or "Operator"), transaction_id))
        write_audit(connection, "TRANSACTION_CANCELLED", f"TX-{transaction_id}", "Pending transaction cancelled by operator; record retained.")
        connection.commit()
        return jsonify({"status": "success", "message": "Transaction cancelled. The record remains in history.", "transaction_id": transaction_id, "transaction_status": "CANCELLED"})
    finally:
        connection.close()

@app.route("/api/alerts", methods=["GET"])
@login_required
def get_alerts():
    connection = get_connection()
    try:
        ensure_support_tables(connection)
        pending = connection.execute("SELECT transaction_id, risk_level FROM transactions WHERE UPPER(status) IN ('PENDING_REVIEW','PENDING_VERIFICATION','HOLD_FOR_REVIEW','VERIFY_RECIPIENT') AND UPPER(risk_level) IN ('HIGH','MEDIUM')").fetchall()
        for tx in pending:
            alert_type = "CRITICAL HIGH-RISK TRANSACTION" if str(tx["risk_level"]).upper() == "HIGH" else "MEDIUM-RISK VERIFICATION"
            message = "High-risk transaction requires review." if str(tx["risk_level"]).upper() == "HIGH" else "Recipient verification is required."
            connection.execute("INSERT OR IGNORE INTO security_alerts (transaction_id, alert_type, message, status) VALUES (?, ?, ?, 'OPEN')", (tx["transaction_id"], alert_type, message))
        connection.commit()
        rows = connection.execute("""SELECT a.alert_id, a.transaction_id, a.alert_type, a.message, a.status, a.created_at, t.customer_id, t.amount, t.recipient, t.risk_level, t.status AS transaction_status FROM security_alerts a JOIN transactions t ON t.transaction_id = a.transaction_id WHERE a.status = 'OPEN' ORDER BY a.alert_id DESC""").fetchall()
        alerts = [dict(row) for row in rows]
        return jsonify({"status": "success", "count": len(alerts), "alerts": alerts})
    finally:
        connection.close()

@app.route("/api/alerts/<int:alert_id>/resolve", methods=["POST"])
@login_required
def resolve_alert(alert_id):
    connection = get_connection()
    try:
        ensure_support_tables(connection)
        alert = connection.execute("SELECT alert_id, transaction_id, status FROM security_alerts WHERE alert_id = ?", (alert_id,)).fetchone()
        if alert is None:
            return jsonify({"status": "error", "message": "Alert not found"}), 404
        if alert["status"] != "OPEN":
            return jsonify({"status": "error", "message": "Alert is already resolved"}), 409
        connection.execute("UPDATE security_alerts SET status = 'RESOLVED', resolved_at = CURRENT_TIMESTAMP, resolved_by = ? WHERE alert_id = ?", (str(session.get("user_name") or "Operator"), alert_id))
        write_audit(connection, "SECURITY_ALERT_RESOLVED", f"ALERT-{alert_id}", f"Resolved alert for transaction TX-{alert['transaction_id']}; transaction status unchanged.")
        connection.commit()
        return jsonify({"status": "success", "message": "Security alert resolved. Transaction status was not changed."})
    finally:
        connection.close()

@app.route("/api/analytics", methods=["GET"])
@login_required
def get_analytics():
    connection = get_connection()
    try:
        rows = connection.execute("SELECT amount, risk_level, status FROM transactions").fetchall()
        total = len(rows)
        amount_total = sum(float(row["amount"] or 0) for row in rows)
        pending_statuses = {"PENDING_REVIEW", "PENDING_VERIFICATION", "HOLD_FOR_REVIEW", "VERIFY_RECIPIENT"}
        approved_statuses = {"SIMULATED_APPROVED", "APPROVED", "SETTLED"}
        cancelled_statuses = {"CANCELLED", "REJECTED"}
        pending = sum(str(row["status"] or "").upper() in pending_statuses for row in rows)
        approved = sum(str(row["status"] or "").upper() in approved_statuses for row in rows)
        cancelled = sum(str(row["status"] or "").upper() in cancelled_statuses for row in rows)
        high = sum(str(row["risk_level"] or "").upper() == "HIGH" for row in rows)
        medium = sum(str(row["risk_level"] or "").upper() == "MEDIUM" for row in rows)
        low = sum(str(row["risk_level"] or "").upper() == "LOW" for row in rows)
        held_amount = sum(float(row["amount"] or 0) for row in rows if str(row["status"] or "").upper() in pending_statuses)
        return jsonify({"status": "success", "metrics": {"total_transactions": total, "total_transaction_value": round(amount_total, 2), "pending_review": pending, "approved_demo": approved, "cancelled": cancelled, "high_risk": high, "medium_risk": medium, "low_risk": low, "pending_review_value": round(held_amount, 2), "model_precision": None, "latency_ms": None}})
    finally:
        connection.close()

@app.route("/api/audit-logs", methods=["GET"])
@login_required
def get_audit_logs():
    connection = get_connection()
    try:
        ensure_support_tables(connection)
        rows = connection.execute("SELECT log_id, created_at, actor, event_type, target_ref, details, event_hash FROM audit_logs ORDER BY log_id DESC").fetchall()
        logs = [dict(row) for row in rows]
        return jsonify({"status": "success", "count": len(logs), "logs": logs})
    finally:
        connection.close()

@app.route("/api/customers/<int:customer_id>/transactions",
           methods=["GET"])
@login_required
def get_customer_transactions(customer_id):
    connection = get_connection()

    try:
        customer = connection.execute("""
            SELECT customer_id, name, average_transaction_amount
            FROM customers
            WHERE customer_id = ?
        """, (customer_id,)).fetchone()

        if customer is None:
            return jsonify({
                "status": "error",
                "message": "Customer not found"
            }), 404

        rows = connection.execute("""
            SELECT transaction_id, customer_id, amount,
                   recipient, risk_level, status, created_at
            FROM transactions
            WHERE customer_id = ?
            ORDER BY transaction_id
        """, (customer_id,)).fetchall()

        transactions = [dict(row) for row in rows]

        return jsonify({
            "status": "success",
            "customer": dict(customer),
            "count": len(transactions),
            "transactions": transactions
        })

    finally:
        connection.close()


@app.route("/api/transactions/assess", methods=["POST"])
@login_required
def assess_transaction():
    data = request.get_json(silent=True)

    # 1. Validate the JSON request
    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "A JSON request body is required"
        }), 400

    customer_id = data.get("customer_id")
    amount = data.get("amount")
    recipient = data.get("recipient")

    if (
        isinstance(customer_id, bool)
        or not isinstance(customer_id, int)
    ):
        return jsonify({
            "status": "error",
            "message": "customer_id must be an integer"
        }), 400

    if (
        isinstance(amount, bool)
        or not isinstance(amount, (int, float))
        or amount <= 0
        or amount == float("inf")
        or amount != amount
    ):
        return jsonify({
            "status": "error",
            "message": "amount must be a positive, finite number"
        }), 400

    if not isinstance(recipient, str) or not recipient.strip():
        return jsonify({
            "status": "error",
            "message": "recipient must be a non-empty string"
        }), 400

    recipient = recipient.strip()
    amount = float(amount)

    connection = get_connection()

    try:
        # 2. Check whether the customer exists
        customer = connection.execute("""
            SELECT customer_id, name, average_transaction_amount
            FROM customers
            WHERE customer_id = ?
        """, (customer_id,)).fetchone()

        if customer is None:
            return jsonify({
                "status": "error",
                "message": "Customer not found"
            }), 404

        baseline = customer["average_transaction_amount"]

        # 3. Check whether this recipient appears in
        # the customer's historical records
        known_recipient = connection.execute("""
            SELECT 1
            FROM transactions
            WHERE customer_id = ?
              AND LOWER(recipient) = LOWER(?)
              AND status = 'HISTORICAL'
            LIMIT 1
        """, (customer_id, recipient)).fetchone()

        is_new_recipient = known_recipient is None

        # 4. Apply transparent preliminary risk rules
        risk_score = 0
        reasons = []

        if baseline <= 0:
            risk_score += 1
            reasons.append("Customer baseline is unavailable")
        elif amount >= 3 * baseline:
            risk_score += 2
            reasons.append(
                "Transfer amount is at least three times "
                "the customer's average"
            )

        if is_new_recipient:
            risk_score += 1
            reasons.append("Recipient is not in historical records")

        if risk_score >= 2:
            risk_level = "HIGH"
            recommended_action = "HOLD_FOR_REVIEW"
            transaction_status = "PENDING_REVIEW"
        elif risk_score == 1:
            risk_level = "MEDIUM"
            recommended_action = "VERIFY_RECIPIENT"
            transaction_status = "PENDING_VERIFICATION"
        else:
            risk_level = "LOW"
            recommended_action = "APPROVE"
            transaction_status = "SIMULATED_APPROVED"

        if not reasons:
            reasons.append(
                "No risk indicators were triggered by the current rules"
            )

        # 5. Store the transaction and assessment
        cursor = connection.execute("""
            INSERT INTO transactions
                (customer_id, amount, recipient, risk_level, status)
            VALUES (?, ?, ?, ?, ?)
        """, (
            customer_id,
            amount,
            recipient,
            risk_level,
            transaction_status
        ))

        ensure_support_tables(connection)
        if risk_level in {"HIGH", "MEDIUM"}:
            alert_type = "CRITICAL HIGH-RISK TRANSACTION" if risk_level == "HIGH" else "MEDIUM-RISK VERIFICATION"
            alert_message = "High-risk transaction requires review." if risk_level == "HIGH" else "Recipient verification is required."
            connection.execute("INSERT OR IGNORE INTO security_alerts (transaction_id, alert_type, message, status) VALUES (?, ?, ?, 'OPEN')", (cursor.lastrowid, alert_type, alert_message))
        write_audit(connection, "TRANSACTION_ASSESSED", f"TX-{cursor.lastrowid}", f"Risk={risk_level}; status={transaction_status}; amount={amount:.2f}; recipient={recipient}")
        connection.commit()

        # 6. Return the assessment to the caller
        return jsonify({
            "status": "success",
            "transaction_id": cursor.lastrowid,
            "customer_id": customer_id,
            "customer_name": customer["name"],
            "amount": amount,
            "recipient": recipient,
            "is_new_recipient": is_new_recipient,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "reasons": reasons,
            "recommended_action": recommended_action,
            "transaction_status": transaction_status,
            "assessment_type": "RULE_BASED_DEMO"
        }), 201

    finally:
        connection.close()


@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "A JSON request body is required"
        }), 400

    name = data.get("name")
    phone = data.get("phone")
    email = data.get("email")
    password = data.get("password")

    if not isinstance(name, str) or not name.strip():
        return jsonify({
            "status": "error",
            "message": "Name is required"
        }), 400

    if not isinstance(phone, str) or not phone.strip():
        return jsonify({
            "status": "error",
            "message": "Mobile number is required"
        }), 400

    phone = phone.strip()

    if not phone.isdigit() or len(phone) != 10 or phone[0] not in "6789":
        return jsonify({
            "status": "error",
            "message": "Enter a valid 10-digit Indian mobile number"
        }), 400

    if not isinstance(email, str) or not email.strip() or "@" not in email:
        return jsonify({
            "status": "error",
            "message": "A valid email is required"
        }), 400

    if not isinstance(password, str) or len(password) < 8:
        return jsonify({
            "status": "error",
            "message": "Password must contain at least 8 characters"
        }), 400

    name = name.strip()
    email = email.strip().lower()
    password_hash = generate_password_hash(password)

    connection = get_connection()

    try:
        ensure_support_tables(connection)
        connection.execute("""
        INSERT INTO users (name, phone, email, password_hash)
        VALUES (?, ?, ?, ?)
    """, (name, phone, email, password_hash))
        write_audit(connection, "OPERATOR_ACCOUNT_REGISTERED", email, "Application operator account registered.", actor=name)

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Registration successful. You can now log in."
        }), 201

    except sqlite3.IntegrityError:
        return jsonify({
            "status": "error",
            "message": "An account with this email or mobile number already exists"
        }), 409

    finally:
        connection.close()


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "A JSON request body is required"
        }), 400

    email = data.get("email")
    password = data.get("password")

    if (
        not isinstance(email, str)
        or not email.strip()
        or not isinstance(password, str)
        or not password
    ):
        return jsonify({
            "status": "error",
            "message": "Email and password are required"
        }), 400

    email = email.strip().lower()

    connection = get_connection()

    try:
        user = connection.execute("""
            SELECT user_id, name, email, password_hash
            FROM users
            WHERE email = ?
        """, (email,)).fetchone()

        if user is None or not check_password_hash(
            user["password_hash"], password
        ):
            return jsonify({
                "status": "error",
                "message": "Invalid email or password"
            }), 401

        ensure_support_tables(connection)
        write_audit(connection, "OPERATOR_LOGIN", user["email"], "Successful operator login.", actor=user["name"])
        connection.commit()
        session.clear()
        session["user_id"] = user["user_id"]
        session["user_name"] = user["name"]

        return jsonify({
            "status": "success",
            "message": "Login successful",
            "user": {
                "user_id": user["user_id"],
                "name": user["name"],
                "email": user["email"]
            }
        }), 200

    finally:
        connection.close()


@app.route("/api/auth/me", methods=["GET"])
def current_user():
    user_id = session.get("user_id")

    if user_id is None:
        return jsonify({
            "status": "error",
            "message": "Not authenticated"
        }), 401

    return jsonify({
        "status": "success",
        "user": {
            "user_id": user_id,
            "name": session.get("user_name")
        }
    }), 200


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    user_name = str(session.get("user_name") or "Operator")
    connection = get_connection()
    try:
        ensure_support_tables(connection)
        write_audit(connection, "OPERATOR_LOGOUT", None, "Operator ended the authenticated session.", actor=user_name)
        connection.commit()
    finally:
        connection.close()
    session.clear()

    return jsonify({
        "status": "success",
        "message": "Logged out successfully"
    }), 200


if __name__ == "__main__":
    app.run(debug=True)