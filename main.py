import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import hashlib
import secrets
import time
import datetime
import re
from PIL import Image, ImageTk
import os

# ══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════
APP_TITLE    = "Jollibee Point of Sale System"
DB_FILE      = "jollibee_pos.db"
VAT_RATE     = 0.12
MAX_ATTEMPTS = 5
LOCKOUT_SECS = 300
PBKDF2_ITERS = 200_000
SESSION_TIMEOUT = 3600

STORE_INFO = {
    "name":    "JOLLIBEE",
    "branch":  "Katipunan Branch",
    "address": "123 Katipunan Ave., Quezon City",
    "tel":     "(02) 8911-JOLLY",
    "tin":     "123-456-789-000",
}

# ══════════════════════════════════════════════════════════════════
# COLOR PALETTE
# ══════════════════════════════════════════════════════════════════
RED    = "#CC0000";  RED_D    = "#990000"
YELLOW = "#FFC200";  YELLOW_D = "#E5A800"
WHITE  = "#FFFFFF";  BLACK    = "#1A1A1A"
GRAY   = "#777777";  LGRAY    = "#F0F0F0"
BG     = "#F4F4F4";  CARD     = "#FFFFFF"
SIDEBAR= "#252525";  SIDEBAR2 = "#1A1A1A"
SUCC   = "#2E7D32";  SUCC_D   = "#1A5C22"
DANGER = "#C62828";  BORDER   = "#DDDDDD"
WARN   = "#E65100";  INFO     = "#1565C0"

# ══════════════════════════════════════════════════════════════════
# FONTS
# ══════════════════════════════════════════════════════════════════
F_TITLE = ("Helvetica", 20, "bold")
F_H1    = ("Helvetica", 15, "bold")
F_H2    = ("Helvetica", 12, "bold")
F_H3    = ("Helvetica", 11, "bold")
F_BODY  = ("Helvetica", 10)
F_SM    = ("Helvetica", 9)
F_MONO  = ("Courier New", 11)

# ══════════════════════════════════════════════════════════════════
# MENU DATA
# ══════════════════════════════════════════════════════════════════
CATEGORIES = [
    "🍗 Chickenjoy",
    "🍔 Burgers",
    "🍝 Pasta",
    "🌅 Breakfast",
    "🥤 Drinks",
    "🍨 Desserts",
    "🧸 Kids Meal",
]

MENU = {
    "🍗 Chickenjoy": [
        ("1-pc Chickenjoy w/ Rice",       155.00),
        ("1-pc Chickenjoy w/ Spaghetti",  175.00),
        ("2-pc Chickenjoy w/ Rice",       275.00),
        ("2-pc Chickenjoy w/ Spaghetti",  295.00),
        ("6-pc Chickenjoy Bucket",        620.00),
        ("8-pc Chickenjoy Bucket",        790.00),
        ("12-pc Chickenjoy Bucket",      1160.00),
    ],
    "🍔 Burgers": [
        ("Yumburger",                      55.00),
        ("Cheesy Yumburger",               69.00),
        ("Double Yumburger",               89.00),
        ("Burger Steak w/ Rice",           89.00),
        ("Cheesy Burger Steak w/ Rice",    99.00),
    ],
    "🍝 Pasta": [
        ("Jolly Spaghetti Solo",           79.00),
        ("Jolly Spaghetti Family",        249.00),
        ("Baked Macaroni Solo",            89.00),
        ("Baked Macaroni Family",         269.00),
    ],
    "🌅 Breakfast": [
        ("Jolly Hotdog w/ Rice",          109.00),
        ("Corned Beef w/ Rice",           109.00),
        ("Longganisa w/ Rice",            109.00),
        ("Bangus w/ Rice",                119.00),
        ("Tapa w/ Rice",                  119.00),
        ("Champorado",                     89.00),
    ],
    "🥤 Drinks": [
        ("Coke (Regular)",                 45.00),
        ("Coke (Large)",                   55.00),
        ("Coke Float (Regular)",           59.00),
        ("Coke Float (Large)",             69.00),
        ("Juice Drink",                    35.00),
        ("Hot Coffee",                     45.00),
        ("Iced Coffee",                    55.00),
        ("Hot Chocolate",                  55.00),
    ],
    "🍨 Desserts": [
        ("Peach Mango Pie",                59.00),
        ("Chocolate Sundae",               55.00),
        ("Strawberry Sundae",              55.00),
        ("Halo-Halo (Regular)",            79.00),
        ("Halo-Halo (Special)",            99.00),
        ("Cheese Sticks (4 pcs)",          59.00),
    ],
    "🧸 Kids Meal": [
        ("Chickenjoy Kids Meal",          145.00),
        ("Burger Steak Kids Meal",        135.00),
        ("Spaghetti Kids Meal",           125.00),
        ("Yumburger Kids Meal",           125.00),
    ],
}


# ══════════════════════════════════════════════════════════════════
# DATABASE LAYER
# ══════════════════════════════════════════════════════════════════
class Database:

    def __init__(self):
        self._init_tables()
        self._seed_users()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_tables(self):
        with self.connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    username      TEXT    UNIQUE NOT NULL,
                    password_hash TEXT    NOT NULL,
                    salt          TEXT    NOT NULL,
                    role          TEXT    NOT NULL DEFAULT 'cashier',
                    failed        INTEGER NOT NULL DEFAULT 0,
                    locked_until  REAL    NOT NULL DEFAULT 0,
                    last_login    TEXT,
                    created_at    TEXT    DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS orders (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_num    TEXT    UNIQUE NOT NULL,
                    cashier_id   INTEGER NOT NULL,
                    cashier_name TEXT    NOT NULL,
                    dine_option  TEXT    NOT NULL DEFAULT 'Dine In',
                    subtotal     REAL    NOT NULL,
                    vat          REAL    NOT NULL,
                    total        REAL    NOT NULL,
                    pay_method   TEXT    NOT NULL,
                    amount_paid  REAL    NOT NULL,
                    change_given REAL    NOT NULL,
                    created_at   TEXT    DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cashier_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS order_items (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id   INTEGER NOT NULL,
                    item_name  TEXT    NOT NULL,
                    quantity   INTEGER NOT NULL,
                    unit_price REAL    NOT NULL,
                    line_total REAL    NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES orders(id)
                );

                CREATE TABLE IF NOT EXISTS login_log (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    username   TEXT    NOT NULL,
                    success    INTEGER NOT NULL DEFAULT 0,
                    ip_hint    TEXT    NOT NULL DEFAULT 'localhost',
                    reason     TEXT,
                    session_id TEXT,
                    logged_at  TEXT    DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS session_log (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL,
                    username    TEXT    NOT NULL,
                    session_id  TEXT    NOT NULL,
                    login_at    TEXT    NOT NULL,
                    logout_at   TEXT,
                    duration_s  INTEGER,
                    logout_type TEXT    DEFAULT 'manual',
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS audit_log (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id    INTEGER,
                    username   TEXT    NOT NULL,
                    action     TEXT    NOT NULL,
                    detail     TEXT,
                    logged_at  TEXT    DEFAULT CURRENT_TIMESTAMP
                );
            """)

    def _seed_users(self):
        with self.connect() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM users")
            if c.fetchone()[0] == 0:
                seed = [
                    ("admin",    "Admin@123",   "admin"),
                    ("cashier1", "Cashier@123", "cashier"),
                    ("cashier2", "Cashier@123", "cashier"),
                ]
                for uname, pwd, role in seed:
                    salt  = secrets.token_hex(32)
                    phash = hashlib.pbkdf2_hmac(
                        "sha256", pwd.encode(), salt.encode(), PBKDF2_ITERS
                    ).hex()
                    c.execute(
                        "INSERT INTO users (username,password_hash,salt,role) VALUES (?,?,?,?)",
                        (uname, phash, salt, role)
                    )
                conn.commit()

    # ── Auth helpers ─────────────────────────────────────────────
    def get_user(self, username: str):
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM users WHERE username=?", (username,)
            ).fetchone()

    def get_user_by_id(self, uid: int):
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM users WHERE id=?", (uid,)
            ).fetchone()

    def record_fail(self, uid: int, locked_until: float = 0):
        with self.connect() as conn:
            conn.execute(
                "UPDATE users SET failed=failed+1, locked_until=? WHERE id=?",
                (locked_until, uid)
            )

    def record_success(self, uid: int):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.connect() as conn:
            conn.execute(
                "UPDATE users SET failed=0, locked_until=0, last_login=? WHERE id=?",
                (now, uid)
            )

    def get_all_users(self):
        with self.connect() as conn:
            return conn.execute("SELECT * FROM users ORDER BY id").fetchall()

    def add_user(self, username: str, password: str, role: str) -> tuple:
        """Returns (ok: bool, msg: str)."""
        salt  = secrets.token_hex(32)
        phash = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), PBKDF2_ITERS
        ).hex()
        try:
            with self.connect() as conn:
                conn.execute(
                    "INSERT INTO users (username,password_hash,salt,role) VALUES (?,?,?,?)",
                    (username, phash, salt, role)
                )
            return True, "User created successfully."
        except sqlite3.IntegrityError:
            return False, f"Username '{username}' already exists."

    def update_user_role(self, uid: int, new_role: str):
        with self.connect() as conn:
            conn.execute("UPDATE users SET role=? WHERE id=?", (new_role, uid))

    def update_user_password(self, uid: int, new_password: str):
        salt  = secrets.token_hex(32)
        phash = hashlib.pbkdf2_hmac(
            "sha256", new_password.encode(), salt.encode(), PBKDF2_ITERS
        ).hex()
        with self.connect() as conn:
            conn.execute(
                "UPDATE users SET password_hash=?,salt=? WHERE id=?",
                (phash, salt, uid)
            )

    def delete_user(self, uid: int):
        with self.connect() as conn:
            conn.execute("DELETE FROM users WHERE id=?", (uid,))

    def count_admins(self) -> int:
        with self.connect() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM users WHERE role='admin'"
            ).fetchone()[0]

    # ── Login log ─────────────────────────────────────────────────
    def log_login(self, username: str, success: bool, reason: str = None, session_id: str = None):
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO login_log (username,success,reason,session_id) VALUES (?,?,?,?)",
                (username, 1 if success else 0, reason, session_id)
            )

    def get_login_log(self, limit: int = 500):
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM login_log ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()

    def get_login_stats(self):
        today = datetime.date.today().isoformat()
        with self.connect() as conn:
            return conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(success) as successes,
                    COUNT(*) - SUM(success) as failures
                FROM login_log WHERE date(logged_at)=?
            """, (today,)).fetchone()

    # ── Session log ───────────────────────────────────────────────
    def start_session(self, user_id: int, username: str, session_id: str):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO session_log (user_id,username,session_id,login_at) VALUES (?,?,?,?)",
                (user_id, username, session_id, now)
            )

    def end_session(self, session_id: str, logout_type: str = "manual"):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.connect() as conn:
            row = conn.execute(
                "SELECT login_at FROM session_log WHERE session_id=? AND logout_at IS NULL",
                (session_id,)
            ).fetchone()
            if row:
                try:
                    login_dt  = datetime.datetime.strptime(row["login_at"], "%Y-%m-%d %H:%M:%S")
                    logout_dt = datetime.datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
                    dur       = int((logout_dt - login_dt).total_seconds())
                except Exception:
                    dur = None
                conn.execute(
                    "UPDATE session_log SET logout_at=?,duration_s=?,logout_type=? WHERE session_id=?",
                    (now, dur, logout_type, session_id)
                )

    def get_session_log(self, limit: int = 200):
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM session_log ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()

    # ── Audit log ─────────────────────────────────────────────────
    def audit(self, username: str, action: str, detail: str = None, user_id: int = None):
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO audit_log (user_id,username,action,detail) VALUES (?,?,?,?)",
                (user_id, username, action, detail)
            )

    def get_audit_log(self, limit: int = 500):
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()

    # ── Unlock user ───────────────────────────────────────────────
    def unlock_user(self, uid: int):
        with self.connect() as conn:
            conn.execute(
                "UPDATE users SET failed=0, locked_until=0 WHERE id=?", (uid,)
            )

    # ── Orders ────────────────────────────────────────────────────
    def save_order(self, data: dict) -> int:
        with self.connect() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO orders
                  (order_num,cashier_id,cashier_name,dine_option,
                   subtotal,vat,total,pay_method,amount_paid,change_given)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                data["order_num"], data["cashier_id"], data["cashier_name"],
                data["dine_option"], data["subtotal"], data["vat"],
                data["total"],      data["pay_method"],
                data["amount_paid"], data["change_given"]
            ))
            oid = c.lastrowid
            c.executemany("""
                INSERT INTO order_items (order_id,item_name,quantity,unit_price,line_total)
                VALUES (?,?,?,?,?)
            """, [
                (oid, i["name"], i["qty"], i["price"], i["total"])
                for i in data["items"]
            ])
            conn.commit()
            return oid

    def get_orders(self, limit: int = 500):
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()

    def get_order_items(self, order_id: int):
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM order_items WHERE order_id=?", (order_id,)
            ).fetchall()

    def get_today_summary(self):
        today = datetime.date.today().isoformat()
        with self.connect() as conn:
            return conn.execute("""
                SELECT COUNT(*) as cnt, COALESCE(SUM(total),0) as revenue
                FROM orders WHERE date(created_at)=?
            """, (today,)).fetchone()

    def next_order_num(self) -> str:
        today = datetime.date.today().strftime("%Y%m%d")
        with self.connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM orders WHERE order_num LIKE ?",
                (f"JB-{today}-%",)
            ).fetchone()
        return f"JB-{today}-{(row[0] or 0) + 1:04d}"


# ══════════════════════════════════════════════════════════════════
# PASSWORD VALIDATOR
# ══════════════════════════════════════════════════════════════════
def validate_password(pwd: str) -> tuple:
    """Returns (ok: bool, message: str)."""
    if len(pwd) < 8:
        return False, "Password must be at least 8 characters."
    if not re.search(r"[A-Z]", pwd):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", pwd):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"\d", pwd):
        return False, "Password must contain at least one number."
    if not re.search(r"[^A-Za-z0-9]", pwd):
        return False, "Password must contain at least one special character."
    return True, "OK"

def validate_username(uname: str) -> tuple:
    """Returns (ok: bool, message: str)."""
    if len(uname) < 3:
        return False, "Username must be at least 3 characters."
    if len(uname) > 32:
        return False, "Username must be 32 characters or fewer."
    if not re.match(r"^[A-Za-z0-9_]+$", uname):
        return False, "Username may only contain letters, numbers, and underscores."
    return True, "OK"


# ══════════════════════════════════════════════════════════════════
# AUTHENTICATION MANAGER
# ══════════════════════════════════════════════════════════════════
class AuthManager:

    def __init__(self, db: Database):
        self.db         = db
        self.user       = None
        self.session_id = None
        self.login_time = None

    @staticmethod
    def _hash(password: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), PBKDF2_ITERS
        ).hex()

    def login(self, username: str, password: str):
        row = self.db.get_user(username)
        if row is None:
            hashlib.pbkdf2_hmac("sha256", password.encode(), b"dummy", PBKDF2_ITERS)
            self.db.log_login(username, False, "User not found")
            return False, "Invalid username or password."

        uid = row["id"]
        now = time.time()

        if row["locked_until"] and now < row["locked_until"]:
            remaining = int(row["locked_until"] - now)
            m, s = divmod(remaining, 60)
            self.db.log_login(username, False, f"Account locked ({m}m {s}s remaining)")
            return False, f"Account locked. Try again in {m}m {s}s."

        expected = self._hash(password, row["salt"])
        if not secrets.compare_digest(expected, row["password_hash"]):
            new_fails = row["failed"] + 1
            if new_fails >= MAX_ATTEMPTS:
                self.db.record_fail(uid, now + LOCKOUT_SECS)
                self.db.log_login(username, False, "Account locked after max failed attempts")
                return False, (
                    f"Too many failed attempts. "
                    f"Account locked for {LOCKOUT_SECS // 60} minutes."
                )
            self.db.record_fail(uid, 0)
            left = MAX_ATTEMPTS - new_fails
            self.db.log_login(username, False, f"Wrong password ({new_fails}/{MAX_ATTEMPTS} attempts)")
            return False, (
                f"Invalid username or password. "
                f"{left} attempt{'s' if left != 1 else ''} remaining."
            )

        self.db.record_success(uid)
        self.session_id = secrets.token_hex(16)
        self.login_time = time.time()
        self.user       = dict(row)
        self.db.log_login(username, True, "Login successful", self.session_id)
        self.db.start_session(uid, username, self.session_id)
        self.db.audit(username, "LOGIN", f"Session {self.session_id}", uid)
        return True, "OK"

    def logout(self, logout_type: str = "manual"):
        if self.session_id:
            self.db.end_session(self.session_id, logout_type)
            if self.user:
                self.db.audit(self.user["username"], "LOGOUT",
                              f"Session {self.session_id} | Type: {logout_type}",
                              self.user["id"])
        self.user       = None
        self.session_id = None
        self.login_time = None

    @property
    def is_admin(self) -> bool:
        return bool(self.user and self.user.get("role") == "admin")

    def session_age(self) -> float:
        if self.login_time is None:
            return 0.0
        return time.time() - self.login_time


# ══════════════════════════════════════════════════════════════════
# USER FORM DIALOG  (shared by Add & Edit)
# ══════════════════════════════════════════════════════════════════
class UserFormDialog(tk.Toplevel):
    """
    Modal dialog for creating or editing a user account.
    mode = "add"  → all fields active, password required
    mode = "edit" → username disabled, password optional (leave blank to keep)
    """

    def __init__(self, parent, db: Database, auth: AuthManager,
                 mode: str = "add", user_row=None, on_save=None):
        super().__init__(parent)
        self.db       = db
        self.auth     = auth
        self.mode     = mode          # "add" | "edit"
        self.user_row = user_row      # sqlite3.Row for edit mode
        self.on_save  = on_save       # callback after successful save

        title = "➕  Add New User" if mode == "add" else "✏️  Edit User"
        self.title(title)
        self.configure(bg=WHITE)
        self.resizable(False, False)
        self.grab_set()

        w, h = 420, 520 if mode == "add" else 500
        x = parent.winfo_x() + (parent.winfo_width()  - w) // 2
        y = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{max(0,x)}+{max(0,y)}")

        self._build()

    # ── UI ───────────────────────────────────────────────────────
    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=SIDEBAR, pady=12)
        hdr.pack(fill="x")
        icon = "➕" if self.mode == "add" else "✏️"
        lbl  = "Add New User" if self.mode == "add" else \
               f"Edit User: {self.user_row['username']}"
        tk.Label(hdr, text=f"{icon}  {lbl}",
                 font=F_H2, bg=SIDEBAR, fg=YELLOW).pack(padx=16)

        # Body
        body = tk.Frame(self, bg=WHITE, padx=30, pady=20)
        body.pack(fill="both", expand=True)

        def field(label, row_idx):
            tk.Label(body, text=label, font=F_H3, bg=WHITE, fg=BLACK,
                     anchor="w").grid(row=row_idx, column=0, sticky="w",
                                      pady=(10, 2), columnspan=2)

        # ── Username ────────────────────────────────────────────
        field("Username", 0)
        self._uname_var = tk.StringVar()
        uname_e = tk.Entry(body, textvariable=self._uname_var, font=F_BODY,
                           relief="solid", bd=1, width=34)
        uname_e.grid(row=1, column=0, columnspan=2, sticky="ew")
        if self.mode == "edit":
            self._uname_var.set(self.user_row["username"])
            uname_e.configure(state="disabled", bg=LGRAY, fg=GRAY)

        # ── Role ────────────────────────────────────────────────
        field("Role", 2)
        self._role_var = tk.StringVar(
            value=self.user_row["role"] if self.mode == "edit" else "cashier")
        role_f = tk.Frame(body, bg=WHITE)
        role_f.grid(row=3, column=0, columnspan=2, sticky="w")
        for val, lbl in [("cashier", "👷 Cashier"), ("admin", "🔑 Admin")]:
            tk.Radiobutton(role_f, text=lbl, variable=self._role_var, value=val,
                           font=F_BODY, bg=WHITE, selectcolor=YELLOW,
                           activebackground=WHITE).pack(side="left", padx=(0, 16))

        # ── Password ────────────────────────────────────────────
        pwd_lbl = "Password" if self.mode == "add" else \
                  "New Password  (leave blank to keep current)"
        field(pwd_lbl, 4)

        pwd_row = tk.Frame(body, bg=WHITE)
        pwd_row.grid(row=5, column=0, columnspan=2, sticky="ew")
        self._pwd_var = tk.StringVar()
        self._pwd_e   = tk.Entry(pwd_row, textvariable=self._pwd_var,
                                 show="●", font=F_BODY, relief="solid", bd=1, width=30)
        self._pwd_e.pack(side="left", fill="x", expand=True, ipady=6)
        self._eye1 = False
        tk.Button(pwd_row, text="👁", font=("Helvetica", 11), bg=WHITE, fg=GRAY,
                  relief="flat", cursor="hand2",
                  command=lambda: self._toggle_eye(self._pwd_e, "_eye1")
                  ).pack(side="right", padx=(4, 0))

        # ── Confirm Password ────────────────────────────────────
        field("Confirm Password", 6)
        cpwd_row = tk.Frame(body, bg=WHITE)
        cpwd_row.grid(row=7, column=0, columnspan=2, sticky="ew")
        self._cpwd_var = tk.StringVar()
        self._cpwd_e   = tk.Entry(cpwd_row, textvariable=self._cpwd_var,
                                  show="●", font=F_BODY, relief="solid", bd=1, width=30)
        self._cpwd_e.pack(side="left", fill="x", expand=True, ipady=6)
        self._eye2 = False
        tk.Button(cpwd_row, text="👁", font=("Helvetica", 11), bg=WHITE, fg=GRAY,
                  relief="flat", cursor="hand2",
                  command=lambda: self._toggle_eye(self._cpwd_e, "_eye2")
                  ).pack(side="right", padx=(4, 0))

        # Password strength meter
        self._strength_lbl = tk.Label(body, text="", font=F_SM, bg=WHITE, fg=GRAY,
                                      anchor="w", wraplength=340, justify="left")
        self._strength_lbl.grid(row=8, column=0, columnspan=2, sticky="w", pady=(4, 0))
        self._pwd_var.trace_add("write", lambda *_: self._check_strength())

        # Status
        self._status_var = tk.StringVar()
        tk.Label(body, textvariable=self._status_var,
                 font=F_SM, bg=WHITE, fg=DANGER,
                 wraplength=340, justify="left"
                 ).grid(row=9, column=0, columnspan=2, sticky="w", pady=(6, 0))

        body.columnconfigure(0, weight=1)

        # ── Buttons ─────────────────────────────────────────────
        btn_f = tk.Frame(self, bg=LGRAY, pady=12, padx=20)
        btn_f.pack(fill="x", side="bottom")

        tk.Button(btn_f, text="✖  Cancel",
                  font=F_SM, bg=WHITE, fg=BLACK, relief="flat", cursor="hand2",
                  command=self.destroy
                  ).pack(side="right", padx=(6, 0), ipadx=12, ipady=4)

        save_lbl = "➕  Create User" if self.mode == "add" else "💾  Save Changes"
        tk.Button(btn_f, text=save_lbl,
                  font=("Helvetica", 10, "bold"),
                  bg=SUCC, fg=WHITE, activebackground=SUCC_D,
                  relief="flat", cursor="hand2",
                  command=self._save
                  ).pack(side="right", ipadx=12, ipady=4)

        self.bind("<Return>", lambda e: self._save())

    def _toggle_eye(self, entry, attr):
        current = getattr(self, attr)
        setattr(self, attr, not current)
        entry.configure(show="" if not current else "●")

    def _check_strength(self):
        pwd = self._pwd_var.get()
        if not pwd:
            self._strength_lbl.configure(text="", fg=GRAY)
            return
        ok, msg = validate_password(pwd)
        if ok:
            self._strength_lbl.configure(text="✅  Strong password", fg=SUCC)
        else:
            self._strength_lbl.configure(text=f"⚠  {msg}", fg=WARN)

    def _save(self):
        uname = self._uname_var.get().strip()
        role  = self._role_var.get()
        pwd   = self._pwd_var.get()
        cpwd  = self._cpwd_var.get()

        # ── Validate username (add mode only) ───────────────────
        if self.mode == "add":
            ok, msg = validate_username(uname)
            if not ok:
                self._status_var.set(f"✖  {msg}")
                return

        # ── Validate password ───────────────────────────────────
        if self.mode == "add" and not pwd:
            self._status_var.set("✖  Password is required.")
            return

        if pwd:
            ok, msg = validate_password(pwd)
            if not ok:
                self._status_var.set(f"✖  {msg}")
                return
            if pwd != cpwd:
                self._status_var.set("✖  Passwords do not match.")
                return

        # ── Guard: cannot demote the last admin ─────────────────
        if self.mode == "edit" and \
           self.user_row["role"] == "admin" and \
           role != "admin" and \
           self.db.count_admins() <= 1:
            self._status_var.set("✖  Cannot demote the last admin account.")
            return

        # ── Persist ─────────────────────────────────────────────
        if self.mode == "add":
            ok, msg = self.db.add_user(uname, pwd, role)
            if not ok:
                self._status_var.set(f"✖  {msg}")
                return
            self.db.audit(
                self.auth.user["username"], "USER_CREATED",
                f"Created user '{uname}' with role '{role}'",
                self.auth.user["id"]
            )
        else:
            uid = self.user_row["id"]
            changes = []
            if role != self.user_row["role"]:
                self.db.update_user_role(uid, role)
                changes.append(f"role → {role}")
            if pwd:
                self.db.update_user_password(uid, pwd)
                changes.append("password changed")
            detail = f"Edited '{self.user_row['username']}': " + \
                     (", ".join(changes) if changes else "no changes")
            self.db.audit(
                self.auth.user["username"], "USER_EDITED",
                detail, self.auth.user["id"]
            )

        if self.on_save:
            self.on_save()
        self.destroy()


# ══════════════════════════════════════════════════════════════════
# APP
# ══════════════════════════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.state("zoomed")
        self.overrideredirect(True)

        self.db   = Database()
        self.auth = AuthManager(self.db)

        self._frame = None
        self.show_login()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def show_login(self):
        if self._frame:
            self._frame.destroy()
        self._frame = LoginFrame(self, self.auth, on_login=self.show_pos)
        self._frame.pack(fill="both", expand=True)

    def show_pos(self):
        if self._frame:
            self._frame.destroy()
        self._frame = POSFrame(self, self.db, self.auth, on_logout=self.show_login)
        self._frame.pack(fill="both", expand=True)

    def _on_close(self):
        if isinstance(self._frame, POSFrame):
            if self._frame._clock_job:
                try:
                    self._frame.after_cancel(self._frame._clock_job)
                except Exception:
                    pass
            if self._frame._session_job:
                try:
                    self._frame.after_cancel(self._frame._session_job)
                except Exception:
                    pass
        self.auth.logout("app_close")
        self.destroy()


# ══════════════════════════════════════════════════════════════════
# LOGIN FRAME
# ══════════════════════════════════════════════════════════════════
class LoginFrame(tk.Frame):
    def __init__(self, parent, auth: AuthManager, on_login):
        super().__init__(parent, bg=RED)
        self.auth     = auth
        self.on_login = on_login
        self._build()

    def _build(self):
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)
        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)
        self.columnconfigure(2, weight=1)

        card = tk.Frame(self, bg=WHITE, padx=52, pady=44)
        card.grid(row=1, column=1)

        logo_f = tk.Frame(card, bg=WHITE)
        logo_f.pack(pady=(0, 22))
        try:
            logo_img = Image.open("JollibeeLogo.png")
            logo_img = logo_img.resize((100, 100))
            self.logo_photo = ImageTk.PhotoImage(logo_img)
            tk.Label(logo_f, image=self.logo_photo, bg=WHITE).pack()
        except Exception:
            tk.Label(logo_f, text="🐝", font=("Helvetica", 52), bg=WHITE).pack()

        form = tk.Frame(card, bg=WHITE)
        form.pack()

        tk.Label(form, text="Username", font=F_H3, bg=WHITE, fg=BLACK, anchor="w").pack(
            fill="x", pady=(0, 4))
        self._uname = tk.StringVar()
        self._uname_e = tk.Entry(form, textvariable=self._uname, font=F_BODY,
                                  relief="solid", bd=1, width=30, bg=WHITE)
        self._uname_e.pack(fill="x", ipady=8, pady=(0, 14))

        tk.Label(form, text="Password", font=F_H3, bg=WHITE, fg=BLACK, anchor="w").pack(
            fill="x", pady=(0, 4))
        pwd_row = tk.Frame(form, bg=WHITE)
        pwd_row.pack(fill="x", pady=(0, 4))

        self._pwd = tk.StringVar()
        self._pwd_e = tk.Entry(pwd_row, textvariable=self._pwd, font=F_BODY,
                                show="●", relief="solid", bd=1, bg=WHITE)
        self._pwd_e.pack(side="left", fill="x", expand=True, ipady=8)
        self._eye_on = False
        tk.Button(pwd_row, text="👁", font=("Helvetica", 12), bg=WHITE, fg=GRAY,
                  relief="flat", cursor="hand2", command=self._toggle_eye
                  ).pack(side="right", padx=(5, 0))

        self._status = tk.StringVar()
        tk.Label(form, textvariable=self._status, font=F_SM, bg=WHITE, fg=DANGER,
                 wraplength=290, justify="center").pack(fill="x", pady=(8, 0))

        self._login_btn = tk.Button(
            form, text="LOG IN",
            font=("Helvetica", 13, "bold"),
            bg=RED, fg=WHITE, activebackground=RED_D, activeforeground=WHITE,
            relief="flat", cursor="hand2",
            command=self._do_login, pady=11, width=28)
        self._login_btn.pack(pady=(16, 0))

        self.bind_all("<Return>", lambda e: self._do_login())
        self._uname_e.focus_set()

    def _toggle_eye(self):
        self._eye_on = not self._eye_on
        self._pwd_e.configure(show="" if self._eye_on else "●")

    def _do_login(self):
        uname = self._uname.get().strip()
        pwd   = self._pwd.get()
        if not uname:
            self._status.set("⚠  Please enter your username.")
            return
        if not pwd:
            self._status.set("⚠  Please enter your password.")
            return

        self._login_btn.configure(state="disabled", text="Verifying…")
        self.update()
        ok, msg = self.auth.login(uname, pwd)
        if ok:
            self.unbind_all("<Return>")
            self._status.set("")
            self.on_login()
        else:
            self._status.set(f"✖  {msg}")
            self._login_btn.configure(state="normal", text="LOG IN")
            self._pwd.set("")
            self._pwd_e.focus_set()


# ══════════════════════════════════════════════════════════════════
# POS FRAME
# ══════════════════════════════════════════════════════════════════
class POSFrame(tk.Frame):
    def __init__(self, parent, db: Database, auth: AuthManager, on_logout):
        super().__init__(parent, bg=BG)
        self.db          = db
        self.auth        = auth
        self.on_logout   = on_logout
        self.cart         = {}
        self._pay_meth    = "Cash"
        self._dine_var    = tk.StringVar(value="Dine In")
        self._clock_job   = None
        self._session_job = None
        self._cat_btns    = {}
        self._cur_cat     = CATEGORIES[0]

        self._setup_styles()
        self._build()
        self._update_clock()
        self._check_session_timeout()
        self._load_category(CATEGORIES[0])

    def _setup_styles(self):
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except Exception:
            pass
        for name in ("Cart", "Orders"):
            s.configure(f"{name}.Treeview",
                        background=WHITE, foreground=BLACK,
                        fieldbackground=WHITE, rowheight=28, font=F_SM)
            s.configure(f"{name}.Treeview.Heading",
                        background=LGRAY, foreground=BLACK, font=F_H3)
            s.map(f"{name}.Treeview",
                  background=[("selected", YELLOW)],
                  foreground=[("selected", BLACK)])

    def _build(self):
        self._build_header()
        content = tk.Frame(self, bg=BG)
        content.pack(fill="both", expand=True)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)

        sidebar = tk.Frame(content, bg=SIDEBAR, width=175)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        self._build_sidebar(sidebar)

        self._menu_frame_outer = tk.Frame(content, bg=BG)
        self._menu_frame_outer.grid(row=0, column=1, sticky="nsew")
        self._build_menu_area(self._menu_frame_outer)

        right = tk.Frame(content, bg=CARD, width=345)
        right.grid(row=0, column=2, sticky="nsew")
        right.grid_propagate(False)
        self._build_right_panel(right)

    def _build_header(self):
        hdr = tk.Frame(self, bg=RED)
        hdr.pack(fill="x", side="top")
        try:
            logo_img = Image.open("JollibeeMascot.png")
            logo_img = logo_img.resize((45, 45))
            self.logo_photo = ImageTk.PhotoImage(logo_img)
            tk.Label(hdr, image=self.logo_photo, bg=RED).pack(side="left", padx=(14, 4), pady=8)
        except Exception:
            pass

        left = tk.Frame(hdr, bg=RED)
        left.pack(side="left", padx=6, pady=8)
        tk.Label(left, text="Jollibee", font=("Helvetica", 15, "bold"), bg=RED, fg=WHITE).pack(side="left")
        tk.Label(left, text=f"  │  {STORE_INFO['branch']}",
                 font=("Helvetica", 10), bg=RED, fg="#FFBBBB").pack(side="left")

        right = tk.Frame(hdr, bg=RED)
        right.pack(side="right", padx=14, pady=8)

        if self.auth.is_admin:
            tk.Button(right, text="⚙ Admin", font=F_SM, bg=YELLOW_D, fg=BLACK,
                      relief="flat", cursor="hand2", command=self._show_admin
                      ).pack(side="right", padx=(6, 0))

        tk.Button(right, text="⏻ Logout", font=F_SM, bg=RED_D, fg=WHITE,
                  activebackground="#660000", relief="flat", cursor="hand2",
                  command=self._logout).pack(side="right", padx=(6, 0))

        self._today_lbl = tk.Label(right, text="", font=F_SM, bg=RED, fg="#FFBBBB")
        self._today_lbl.pack(side="right", padx=(6, 0))

        self._clock_lbl = tk.Label(right, text="", font=("Courier New", 10), bg=RED, fg=WHITE)
        self._clock_lbl.pack(side="right", padx=(6, 0))

        self._session_lbl = tk.Label(right, text="", font=("Helvetica", 8), bg=RED, fg="#FFBBBB")
        self._session_lbl.pack(side="right", padx=(6, 0))

        tk.Label(right, text=f"👤  {self.auth.user['username'].title()}",
                 font=("Helvetica", 11, "bold"), bg=RED, fg=YELLOW
                 ).pack(side="right", padx=(6, 0))

        self._refresh_today_counter()

    def _build_sidebar(self, parent):
        tk.Label(parent, text="MENU CATEGORIES",
                 font=("Helvetica", 8), bg=SIDEBAR2, fg="#666666", pady=7).pack(fill="x")

        for cat in CATEGORIES:
            btn = tk.Button(
                parent, text=cat,
                font=("Helvetica", 10, "bold"), anchor="w", padx=14, pady=11,
                bg=SIDEBAR, fg=WHITE, activebackground=YELLOW, activeforeground=BLACK,
                relief="flat", cursor="hand2",
                command=lambda c=cat: self._load_category(c))
            btn.pack(fill="x")

            def _enter(e, b=btn, c=cat):
                if c != self._cur_cat: b.configure(bg="#3C3C3C")
            def _leave(e, b=btn, c=cat):
                if c != self._cur_cat: b.configure(bg=SIDEBAR)
            btn.bind("<Enter>", _enter)
            btn.bind("<Leave>", _leave)
            self._cat_btns[cat] = btn

        foot = tk.Frame(parent, bg=SIDEBAR)
        foot.pack(side="bottom", fill="x", pady=10)
        tk.Label(foot, text=f"VAT: {int(VAT_RATE*100)}% inclusive",
                 font=F_SM, bg=SIDEBAR, fg="#555555").pack()
        tk.Label(foot, text="v2.2  © Jollibee POS",
                 font=("Helvetica", 8), bg=SIDEBAR, fg="#3A3A3A").pack()

    def _build_menu_area(self, parent):
        self._cat_title = tk.Label(parent, text="", font=F_H1, bg=BG, fg=BLACK,
                                   padx=16, pady=12, anchor="w")
        self._cat_title.pack(fill="x", side="top")
        ttk.Separator(parent, orient="horizontal").pack(fill="x", side="top")

        wrap = tk.Frame(parent, bg=BG)
        wrap.pack(fill="both", expand=True, side="top")

        self._items_canvas = tk.Canvas(wrap, bg=BG, highlightthickness=0)
        vscroll = ttk.Scrollbar(wrap, orient="vertical", command=self._items_canvas.yview)

        self._items_frame = tk.Frame(self._items_canvas, bg=BG)
        self._items_frame.bind(
            "<Configure>",
            lambda e: self._items_canvas.configure(
                scrollregion=self._items_canvas.bbox("all")))

        self._canvas_win = self._items_canvas.create_window(
            (0, 0), window=self._items_frame, anchor="nw")

        def _resize_inner(e):
            self._items_canvas.itemconfig(self._canvas_win, width=e.width)
        self._items_canvas.bind("<Configure>", _resize_inner)
        self._items_canvas.configure(yscrollcommand=vscroll.set)
        vscroll.pack(side="right", fill="y")
        self._items_canvas.pack(side="left", fill="both", expand=True)

        def _mw(e):
            self._items_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        self._items_canvas.bind("<MouseWheel>", _mw)
        self._items_canvas.bind("<Button-4>",
                                lambda e: self._items_canvas.yview_scroll(-1, "units"))
        self._items_canvas.bind("<Button-5>",
                                lambda e: self._items_canvas.yview_scroll(1, "units"))

    def _build_right_panel(self, parent):
        rh = tk.Frame(parent, bg=RED, pady=7)
        rh.pack(fill="x", side="top")
        tk.Label(rh, text="ORDER", font=F_H2, bg=RED, fg=WHITE).pack(side="left", padx=12)
        self._badge = tk.Label(rh, text="0 items", font=F_SM, bg=RED_D, fg=WHITE, padx=8, pady=2)
        self._badge.pack(side="right", padx=8)

        bottom = tk.Frame(parent, bg=CARD)
        bottom.pack(fill="x", side="bottom")
        self._build_controls(bottom)

        cart_f = tk.Frame(parent, bg=CARD)
        cart_f.pack(fill="both", expand=True)
        self._build_cart_tree(cart_f)

    def _build_cart_tree(self, parent):
        self._cart_tree = ttk.Treeview(
            parent, columns=("name","qty","price","total"),
            show="headings", style="Cart.Treeview", selectmode="browse")
        self._cart_tree.heading("name",  text="Item",  anchor="w")
        self._cart_tree.heading("qty",   text="Qty",   anchor="center")
        self._cart_tree.heading("price", text="Price", anchor="e")
        self._cart_tree.heading("total", text="Total", anchor="e")
        self._cart_tree.column("name",  width=145, stretch=True,  anchor="w")
        self._cart_tree.column("qty",   width=38,  stretch=False, anchor="center")
        self._cart_tree.column("price", width=70,  stretch=False, anchor="e")
        self._cart_tree.column("total", width=72,  stretch=False, anchor="e")

        vsb = ttk.Scrollbar(parent, orient="vertical", command=self._cart_tree.yview)
        self._cart_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._cart_tree.pack(fill="both", expand=True)
        self._cart_tree.bind("<Double-1>", self._edit_qty_dialog)
        self._cart_tree.bind("<<TreeviewSelect>>", lambda e: self._update_sel_label())

    def _build_controls(self, parent):
        qty_f = tk.Frame(parent, bg=LGRAY, pady=5)
        qty_f.pack(fill="x")
        tk.Button(qty_f, text=" − ", font=F_H2, bg=WHITE, fg=DANGER, relief="flat",
                  cursor="hand2", command=lambda: self._adjust_qty(-1)
                  ).pack(side="left", padx=(8, 4))
        self._sel_lbl = tk.Label(qty_f, text="Select an item", font=F_SM, bg=LGRAY, fg=GRAY)
        self._sel_lbl.pack(side="left", fill="x", expand=True)
        tk.Button(qty_f, text=" + ", font=F_H2, bg=WHITE, fg=SUCC, relief="flat",
                  cursor="hand2", command=lambda: self._adjust_qty(1)
                  ).pack(side="right", padx=(4, 8))

        act_f = tk.Frame(parent, bg=CARD, pady=4, padx=8)
        act_f.pack(fill="x")
        tk.Button(act_f, text="🗑  Remove", font=F_SM, bg=DANGER, fg=WHITE,
                  activebackground="#8B0000", relief="flat", cursor="hand2",
                  command=self._remove_selected).pack(side="left", ipadx=8, ipady=3)
        tk.Button(act_f, text="✖  Clear All", font=F_SM, bg="#555555", fg=WHITE,
                  activebackground="#333333", relief="flat", cursor="hand2",
                  command=self._clear_cart).pack(side="right", ipadx=8, ipady=3)

        ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=4)

        dine_f = tk.Frame(parent, bg=CARD, padx=10, pady=3)
        dine_f.pack(fill="x")
        tk.Label(dine_f, text="Order Type:", font=F_H3, bg=CARD, fg=BLACK).pack(side="left")
        for opt in ("Dine In", "Take Out"):
            tk.Radiobutton(dine_f, text=opt, variable=self._dine_var, value=opt,
                           font=F_BODY, bg=CARD, fg=BLACK,
                           selectcolor=YELLOW, activebackground=CARD
                           ).pack(side="left", padx=(8, 0))

        ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=4)

        tot_f = tk.Frame(parent, bg=CARD, padx=12, pady=2)
        tot_f.pack(fill="x")
        for attr, lbl_text in [("_sub_lbl", "Subtotal:"), ("_vat_lbl", "VAT (12%):")]:
            row = tk.Frame(tot_f, bg=CARD)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=lbl_text, font=F_BODY, bg=CARD, fg=GRAY, anchor="w").pack(side="left")
            lbl = tk.Label(row, text="₱0.00", font=F_BODY, bg=CARD, fg=BLACK, anchor="e")
            lbl.pack(side="right")
            setattr(self, attr, lbl)

        ttk.Separator(parent, orient="horizontal").pack(fill="x", padx=8, pady=3)

        total_row = tk.Frame(parent, bg=CARD, padx=12, pady=2)
        total_row.pack(fill="x")
        tk.Label(total_row, text="TOTAL", font=("Helvetica", 13, "bold"), bg=CARD, fg=BLACK).pack(side="left")
        self._total_lbl = tk.Label(total_row, text="₱0.00",
                                    font=("Helvetica", 17, "bold"), bg=CARD, fg=RED)
        self._total_lbl.pack(side="right")

        ttk.Separator(parent, orient="horizontal").pack(fill="x", padx=8, pady=5)

        pay_f = tk.Frame(parent, bg=CARD, padx=10, pady=2)
        pay_f.pack(fill="x")
        tk.Label(pay_f, text="Payment Method:", font=F_H3, bg=CARD, fg=BLACK).pack(anchor="w", pady=(0, 5))
        btn_row = tk.Frame(pay_f, bg=CARD)
        btn_row.pack(fill="x")
        self._pay_btns = {}
        for lbl, val in [("💵 Cash","Cash"),("💳 Card","Card"),("📱 E-Wallet","E-Wallet")]:
            b = tk.Button(btn_row, text=lbl, font=("Helvetica", 9, "bold"),
                          bg=LGRAY, fg=BLACK, activebackground=YELLOW_D,
                          relief="flat", cursor="hand2",
                          command=lambda v=val: self._set_pay_method(v))
            b.pack(side="left", fill="x", expand=True, padx=2)
            self._pay_btns[val] = b
        self._set_pay_method("Cash")

        self._process_btn = tk.Button(
            parent, text="💳   PROCESS PAYMENT",
            font=("Helvetica", 12, "bold"),
            bg=SUCC, fg=WHITE, activebackground=SUCC_D,
            relief="flat", cursor="hand2",
            command=self._process_payment, pady=12, state="disabled")
        self._process_btn.pack(fill="x", padx=10, pady=(8, 5))

    def _load_category(self, category: str):
        for cat, btn in self._cat_btns.items():
            btn.configure(bg=YELLOW if cat == category else SIDEBAR,
                          fg=BLACK  if cat == category else WHITE)
        self._cur_cat = category
        self._cat_title.configure(text=category)
        for w in self._items_frame.winfo_children():
            w.destroy()

        cols = 3
        for i, (name, price) in enumerate(MENU[category]):
            r, c = divmod(i, cols)
            card = tk.Frame(self._items_frame, bg=CARD,
                            highlightbackground=BORDER, highlightthickness=1)
            card.grid(row=r, column=c, padx=10, pady=10, sticky="nsew")
            self._items_frame.columnconfigure(c, weight=1)
            tk.Label(card, text=name, font=F_H3, bg=CARD, fg=BLACK,
                     wraplength=158, justify="center", pady=10).pack(fill="x", padx=8)
            tk.Label(card, text=f"₱{price:,.2f}",
                     font=("Helvetica", 12, "bold"), bg=CARD, fg=RED).pack()
            def _add_item(n=name, p=price, frm=card):
                self._add_to_cart(n, p)
                frm.configure(highlightbackground=SUCC)
                frm.after(250, lambda: frm.configure(highlightbackground=BORDER))
            tk.Button(card, text="＋ ADD TO ORDER", font=("Helvetica", 9, "bold"),
                      bg=YELLOW, fg=BLACK, activebackground=YELLOW_D,
                      relief="flat", cursor="hand2", command=_add_item
                      ).pack(fill="x", padx=10, pady=(6, 10), ipady=5)

        self._items_canvas.yview_moveto(0)

    def _add_to_cart(self, name: str, price: float):
        if name in self.cart:
            self.cart[name]["qty"] += 1
        else:
            self.cart[name] = {"price": price, "qty": 1}
        self._refresh_cart()

    def _refresh_cart(self):
        sel = self._get_selected_name()
        for item in self._cart_tree.get_children():
            self._cart_tree.delete(item)
        subtotal = 0.0; item_count = 0
        for name, data in self.cart.items():
            qty = data["qty"]; price = data["price"]; line = qty * price
            subtotal += line; item_count += qty
            self._cart_tree.insert("", "end", iid=name,
                                   values=(name, qty, f"₱{price:,.2f}", f"₱{line:,.2f}"))
        vat = round(subtotal * VAT_RATE, 2); total = round(subtotal + vat, 2)
        self._sub_lbl.configure(text=f"₱{subtotal:,.2f}")
        self._vat_lbl.configure(text=f"₱{vat:,.2f}")
        self._total_lbl.configure(text=f"₱{total:,.2f}")
        self._badge.configure(text=f"{item_count} item{'s' if item_count != 1 else ''}")
        self._process_btn.configure(state="normal" if self.cart else "disabled")
        if sel and sel in self.cart:
            try: self._cart_tree.selection_set(sel)
            except Exception: pass
        self._update_sel_label()

    def _get_selected_name(self):
        sel = self._cart_tree.selection()
        return sel[0] if sel else None

    def _update_sel_label(self):
        name = self._get_selected_name()
        if name and name in self.cart:
            qty = self.cart[name]["qty"]
            short = (name[:18] + "…") if len(name) > 18 else name
            self._sel_lbl.configure(text=f"{short}  ×{qty}")
        elif self.cart:
            self._sel_lbl.configure(text="← Select an item")
        else:
            self._sel_lbl.configure(text="Cart is empty")

    def _adjust_qty(self, delta: int):
        name = self._get_selected_name()
        if not name:
            messagebox.showinfo("No Selection", "Please select an item in the cart first.", parent=self)
            return
        new_qty = self.cart[name]["qty"] + delta
        if new_qty <= 0:
            del self.cart[name]
        else:
            self.cart[name]["qty"] = new_qty
        self._refresh_cart()
        if name in self.cart:
            try: self._cart_tree.selection_set(name)
            except Exception: pass

    def _remove_selected(self):
        name = self._get_selected_name()
        if not name:
            messagebox.showinfo("No Selection", "Please select an item to remove.", parent=self)
            return
        del self.cart[name]
        self._refresh_cart()

    def _clear_cart(self):
        if not self.cart: return
        if messagebox.askyesno("Clear Order", "Remove all items from the current order?", parent=self):
            self.cart.clear(); self._refresh_cart()

    def _edit_qty_dialog(self, event):
        name = self._get_selected_name()
        if not name or name not in self.cart: return
        win = tk.Toplevel(self)
        win.title("Edit Quantity"); win.configure(bg=WHITE)
        win.resizable(False, False); win.grab_set()
        w, h = 300, 190
        x = self.winfo_x() + (self.winfo_width()  - w) // 2
        y = self.winfo_y() + (self.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{max(0,x)}+{max(0,y)}")
        tk.Label(win, text="Edit Quantity", font=F_H2, bg=WHITE, fg=BLACK).pack(pady=(14, 4))
        short = (name[:30] + "…") if len(name) > 30 else name
        tk.Label(win, text=short, font=F_SM, bg=WHITE, fg=GRAY,
                 wraplength=260, justify="center").pack()
        qty_var = tk.IntVar(value=self.cart[name]["qty"])
        spin = tk.Spinbox(win, from_=1, to=99, textvariable=qty_var, font=F_H1, width=7, justify="center")
        spin.pack(pady=10)
        def apply():
            try:
                q = int(qty_var.get())
                if q < 1 or q > 99: raise ValueError
                self.cart[name]["qty"] = q; self._refresh_cart()
                try: self._cart_tree.selection_set(name)
                except Exception: pass
                win.destroy()
            except Exception:
                messagebox.showerror("Invalid", "Enter a valid quantity (1–99).", parent=win)
        tk.Button(win, text="✓  Update", font=F_H3, bg=SUCC, fg=WHITE,
                  activebackground=SUCC_D, relief="flat", cursor="hand2", command=apply
                  ).pack(ipadx=24, ipady=6)
        spin.focus_set(); win.bind("<Return>", lambda e: apply())

    def _set_pay_method(self, method: str):
        self._pay_meth = method
        for val, btn in self._pay_btns.items():
            btn.configure(bg=YELLOW if val == method else LGRAY, fg=BLACK)

    def _get_totals(self):
        subtotal = sum(d["price"] * d["qty"] for d in self.cart.values())
        vat      = round(subtotal * VAT_RATE, 2)
        total    = round(subtotal + vat, 2)
        return subtotal, vat, total

    def _process_payment(self):
        if not self.cart: return
        _, _, total = self._get_totals()
        PaymentDialog(self, total, self._pay_meth, self._complete_order)

    def _complete_order(self, pay_data: dict):
        order_num = self.db.next_order_num()
        now       = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        items = [{"name": n, "qty": d["qty"], "price": d["price"],
                  "total": round(d["qty"] * d["price"], 2)} for n, d in self.cart.items()]
        subtotal = sum(i["total"] for i in items)
        vat      = round(subtotal * VAT_RATE, 2)
        total    = round(subtotal + vat, 2)
        order_data = {
            "order_num": order_num, "cashier_id": self.auth.user["id"],
            "cashier_name": self.auth.user["username"], "dine_option": self._dine_var.get(),
            "subtotal": subtotal, "vat": vat, "total": total,
            "pay_method": pay_data["method"], "amount_paid": pay_data["paid"],
            "change_given": pay_data["change"], "items": items, "datetime": now,
        }
        self.db.save_order(order_data)
        self.db.audit(self.auth.user["username"], "ORDER_PLACED",
                      f"{order_num}  ₱{total:,.2f}  {pay_data['method']}",
                      self.auth.user["id"])
        ReceiptWindow(self, order_data)
        self.cart.clear(); self._refresh_cart(); self._refresh_today_counter()

    def _show_admin(self):
        AdminPanel(self, self.db, self.auth)

    def _logout(self):
        if self.cart:
            if not messagebox.askyesno("Logout",
                "You have unsaved items in the cart.\nLogout anyway?", parent=self):
                return
        if self._clock_job:
            self.after_cancel(self._clock_job); self._clock_job = None
        if self._session_job:
            self.after_cancel(self._session_job); self._session_job = None
        self.auth.logout("manual"); self.on_logout()

    def _update_clock(self):
        now = datetime.datetime.now().strftime("%b %d, %Y  %I:%M:%S %p")
        self._clock_lbl.configure(text=now)
        self._clock_job = self.after(1000, self._update_clock)

    def _check_session_timeout(self):
        age = self.auth.session_age(); remaining = SESSION_TIMEOUT - age
        if remaining <= 0:
            if self._clock_job: self.after_cancel(self._clock_job)
            self.auth.logout("timeout")
            messagebox.showwarning("Session Expired",
                "Your session has expired due to inactivity.\nPlease log in again.", parent=self)
            self.on_logout(); return
        m, s = divmod(int(remaining), 60)
        if remaining < 300:
            self._session_lbl.configure(text=f"⏱ Session: {m}m {s}s", fg=YELLOW)
        else:
            self._session_lbl.configure(text=f"⏱ {m}m", fg="#FFBBBB")
        self._session_job = self.after(10000, self._check_session_timeout)

    def _refresh_today_counter(self):
        try:
            s = self.db.get_today_summary()
            cnt = s["cnt"] or 0; rev = s["revenue"] or 0.0
            self._today_lbl.configure(text=f"Today: {cnt} orders  ₱{rev:,.2f}")
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════
# PAYMENT DIALOG
# ══════════════════════════════════════════════════════════════════
class PaymentDialog(tk.Toplevel):
    def __init__(self, parent, total: float, method: str, on_complete):
        super().__init__(parent)
        self.total = total; self.method = method; self.on_complete = on_complete
        self._amount_str = ""; self._cash_paid = 0.0; self._change = 0.0
        self.title("Process Payment"); self.configure(bg=WHITE)
        self.grab_set(); self.resizable(False, False)
        w = 430; h = 700 if method == "Cash" else 400
        self.geometry(f"{w}x{h}"); self.minsize(w, h)
        x = parent.winfo_x() + (parent.winfo_width()  - 390) // 2
        y = parent.winfo_y() + (parent.winfo_height() - h)   // 2
        self.geometry(f"+{max(0,x)}+{max(0,y)}")
        self._build(); self.focus_set()

    def _build(self):
        hdr = tk.Frame(self, bg=RED, pady=10); hdr.pack(fill="x")
        tk.Label(hdr, text="💳  PROCESS PAYMENT", font=F_H1, bg=RED, fg=WHITE).pack()
        badge_col = {"Cash":"#1B6630","Card":"#1565C0","E-Wallet":"#6A1B9A"}.get(self.method, GRAY)
        tk.Label(hdr, text=f"  {self.method}  ",
                 font=("Helvetica", 10, "bold"), bg=badge_col, fg=WHITE, pady=3).pack(pady=(4,0))
        due = tk.Frame(self, bg=LGRAY, pady=12); due.pack(fill="x")
        tk.Label(due, text="AMOUNT DUE", font=F_SM, bg=LGRAY, fg=GRAY).pack()
        tk.Label(due, text=f"₱{self.total:,.2f}",
                 font=("Helvetica", 28, "bold"), bg=LGRAY, fg=RED).pack()
        if self.method == "Cash": self._build_cash()
        else: self._build_digital()

    def _build_cash(self):
        entry_f = tk.Frame(self, bg=WHITE, padx=20, pady=8); entry_f.pack(fill="x")
        tk.Label(entry_f, text="Cash Received:", font=F_H3, bg=WHITE, fg=BLACK, anchor="w").pack(fill="x")
        self._display = tk.Label(entry_f, text="₱0", font=("Helvetica", 22, "bold"),
                                  bg=LGRAY, fg=BLACK, anchor="e", padx=12, pady=6, relief="groove")
        self._display.pack(fill="x")
        self._chg_lbl = tk.Label(entry_f, text="Change: ₱0.00",
                                  font=("Helvetica", 12, "bold"), bg=WHITE, fg=GRAY)
        self._chg_lbl.pack(anchor="e", pady=(4,0))
        quick_f = tk.Frame(self, bg=WHITE, padx=20, pady=4); quick_f.pack(fill="x")
        tk.Label(quick_f, text="Quick: ", font=F_SM, bg=WHITE, fg=GRAY).pack(side="left")
        for amt in self._quick_amounts():
            tk.Button(quick_f, text=f"₱{amt:,}", font=("Helvetica", 9, "bold"),
                      bg=YELLOW, fg=BLACK, relief="flat", cursor="hand2",
                      command=lambda a=amt: self._set_quick(a)
                      ).pack(side="left", padx=2, ipadx=5, ipady=2)
        np_f = tk.Frame(self, bg=WHITE); np_f.pack(padx=20, pady=6)
        keys = [("7","8","9"),("4","5","6"),("1","2","3"),("C","0","⌫")]
        for r, row in enumerate(keys):
            for c, key in enumerate(row):
                special = key in ("C","⌫")
                tk.Button(np_f, text=key, font=("Helvetica", 14, "bold"),
                          bg=LGRAY if special else WHITE, fg=DANGER if special else BLACK,
                          relief="groove", cursor="hand2", width=5, height=2,
                          command=lambda k=key: self._numpad(k)
                          ).grid(row=r, column=c, padx=3, pady=3)
        self.bind("<Key>", self._key_press)
        self._confirm_btn = tk.Button(self, text="✓   CONFIRM PAYMENT",
                                       font=("Helvetica", 12, "bold"),
                                       bg=SUCC, fg=WHITE, activebackground=SUCC_D,
                                       relief="flat", cursor="hand2",
                                       command=self._confirm, pady=10, state="disabled")
        self._confirm_btn.pack(fill="x", padx=20, pady=(4,15))

    def _build_digital(self):
        body = tk.Frame(self, bg=WHITE); body.pack(fill="both", expand=True, padx=20, pady=20)
        icon = {"Card":"💳","E-Wallet":"📱"}.get(self.method,"💰")
        tk.Label(body, text=icon, font=("Helvetica", 52), bg=WHITE).pack(pady=8)
        tk.Label(body, text=f"Process {self.method} payment\non the terminal, then confirm.",
                 font=("Helvetica", 12), bg=WHITE, fg=GRAY, justify="center").pack()
        tk.Button(self, text="✓   PAYMENT RECEIVED", font=("Helvetica", 12, "bold"),
                  bg=SUCC, fg=WHITE, activebackground=SUCC_D, relief="flat", cursor="hand2",
                  command=self._confirm, pady=12).pack(fill="x", padx=20, pady=(10,20))

    def _quick_amounts(self):
        t, seen = self.total, set(); result = []
        for mult in (50,100,200,500,1000):
            v = (int(t)//mult+1)*mult
            if v >= t and v not in seen: seen.add(v); result.append(v)
        return sorted(result)[:4]

    def _numpad(self, key: str):
        if key == "C": self._amount_str = ""
        elif key == "⌫": self._amount_str = self._amount_str[:-1]
        elif key.isdigit() and len(self._amount_str) < 6:
            if self._amount_str == "" and key == "0": return
            self._amount_str += key
        val = float(self._amount_str) if self._amount_str else 0.0
        self._update_display(val)

    def _key_press(self, event):
        k = event.char
        if k.isdigit(): self._numpad(k)
        elif k in ("\x08","\x7f"): self._numpad("⌫")
        elif k.lower() == "c": self._numpad("C")
        elif event.keysym == "Return" and self._confirm_btn["state"] == "normal": self._confirm()

    def _set_quick(self, amount: float):
        self._amount_str = str(int(amount)); self._update_display(float(amount))

    def _update_display(self, val: float):
        self._display.configure(text=f"₱{val:,.0f}")
        change = val - self.total
        if change >= 0:
            self._chg_lbl.configure(text=f"Change: ₱{change:,.2f}", fg=SUCC)
            self._confirm_btn.configure(state="normal")
            self._cash_paid = val; self._change = change
        else:
            self._chg_lbl.configure(text=f"Short:  ₱{abs(change):,.2f}", fg=DANGER)
            self._confirm_btn.configure(state="disabled")

    def _confirm(self):
        if self.method == "Cash":
            self.on_complete({"method":"Cash","paid":self._cash_paid,"change":self._change})
        else:
            self.on_complete({"method":self.method,"paid":self.total,"change":0.0})
        self.destroy()


# ══════════════════════════════════════════════════════════════════
# RECEIPT WINDOW
# ══════════════════════════════════════════════════════════════════
class ReceiptWindow(tk.Toplevel):
    def __init__(self, parent, order_data: dict):
        super().__init__(parent)
        self.order = order_data
        self.title(f"Receipt – {order_data['order_num']}")
        self.configure(bg=WHITE); self.resizable(False, True); self.overrideredirect(True)
        w, h = 430, 600
        x = parent.winfo_x() + (parent.winfo_width()  - w) // 2
        y = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{max(0,x)}+{max(0,y)}"); self.minsize(w, 400)
        self._build()

    def _build(self):
        bar = tk.Frame(self, bg=LGRAY, pady=7); bar.pack(fill="x")
        tk.Button(bar, text="🖨  Print / Save", font=F_BODY, bg=WHITE, relief="groove",
                  cursor="hand2", command=self._print).pack(side="left", padx=10)
        tk.Button(bar, text="New Order  →", font=F_BODY, bg=SUCC, fg=WHITE, relief="flat",
                  cursor="hand2", command=self.destroy).pack(side="right", padx=10)
        txt_f = tk.Frame(self, bg=WHITE); txt_f.pack(fill="both", expand=True, padx=12, pady=(4,12))
        vsb = tk.Scrollbar(txt_f); vsb.pack(side="right", fill="y")
        self._txt = tk.Text(txt_f, font=F_MONO, bg=WHITE, fg=BLACK, relief="flat",
                             yscrollcommand=vsb.set, width=44, state="normal", wrap="none")
        self._txt.pack(fill="both", expand=True); vsb.configure(command=self._txt.yview)
        self._render(); self._txt.configure(state="disabled")

    def _render(self):
        o = self.order; W = 44
        def ln(text="", align="l"):
            out = text.center(W) if align=="c" else (text.rjust(W) if align=="r" else text)
            self._txt.insert("end", out+"\n")
        def div(ch="─"): self._txt.insert("end", ch*W+"\n")
        def two_col(left, right):
            gap = max(1, W-len(left)-len(right))
            self._txt.insert("end", left+" "*gap+right+"\n")
        div("═"); ln(STORE_INFO["name"],"c"); ln(STORE_INFO["branch"],"c")
        ln(STORE_INFO["address"],"c"); ln(f"Tel: {STORE_INFO['tel']}","c")
        ln(f"TIN: {STORE_INFO['tin']}","c"); div("═"); ln()
        two_col("Order  :", o["order_num"]); two_col("Date   :", o["datetime"])
        two_col("Cashier:", o["cashier_name"]); two_col("Type   :", o["dine_option"]); ln()
        div(); self._txt.insert("end", f"{'ITEM':<26} {'QTY':>3} {'TOTAL':>12}\n"); div()
        for itm in o["items"]:
            name = itm["name"][:24]; right = f"₱{itm['total']:>8,.2f}"
            label = f"{name} x{itm['qty']}"; gap = max(1, W-len(label)-len(right))
            self._txt.insert("end", label+" "*gap+right+"\n")
        div(); two_col("Subtotal", f"₱{o['subtotal']:>8,.2f}")
        two_col("VAT (12%)", f"₱{o['vat']:>8,.2f}"); div("═")
        two_col("TOTAL", f"₱{o['total']:>8,.2f}"); div("═"); ln()
        ln(f"Payment : {o['pay_method']}")
        if o["pay_method"] == "Cash":
            two_col("Cash Received", f"₱{o['amount_paid']:>8,.2f}")
            two_col("Change", f"₱{o['change_given']:>8,.2f}")
        ln(); div(); ln("Thank you for dining at JOLLIBEE!", "c")
        ln('"Bida ang saya!"', "c"); div(); ln("*** Customer Copy ***", "c"); ln()

    def _print(self):
        messagebox.showinfo("Print Receipt",
            f"Receipt {self.order['order_num']} sent to printer.\n\n"
            "(Connect a receipt printer and configure it\n"
            "in the system settings to enable printing.)", parent=self)


# ══════════════════════════════════════════════════════════════════
# ADMIN PANEL
# ══════════════════════════════════════════════════════════════════
class AdminPanel(tk.Toplevel):
    def __init__(self, parent, db: Database, auth: AuthManager):
        super().__init__(parent)
        self.db = db; self.auth = auth
        self.overrideredirect(True)
        self.title("Admin Panel"); self.configure(bg=BG)
        w, h = 1040, 650
        x = parent.winfo_x() + max(0, (parent.winfo_width()  - w) // 2)
        y = parent.winfo_y() + max(0, (parent.winfo_height() - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}"); self.minsize(860, 520)
        self._build(); self._load_orders()

    def _build(self):
        hdr = tk.Frame(self, bg=SIDEBAR, pady=10); hdr.pack(fill="x")
        tk.Label(hdr, text="⚙   ADMIN PANEL", font=F_H1, bg=SIDEBAR, fg=YELLOW
                 ).pack(side="left", padx=20)
        tk.Label(hdr, text=f"Logged in as: {self.auth.user['username']}",
                 font=F_SM, bg=SIDEBAR, fg="#888888").pack(side="left", padx=10)
        tk.Button(hdr, text="✖  Close", font=F_SM, bg=DANGER, fg=WHITE,
                  relief="flat", cursor="hand2", command=self.destroy
                  ).pack(side="right", padx=20)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        self._ord_tab = tk.Frame(nb, bg=BG)
        nb.add(self._ord_tab, text="📋  Orders")
        self._build_orders_tab()

        self._sum_tab = tk.Frame(nb, bg=BG)
        nb.add(self._sum_tab, text="📊  Today's Summary")
        self._sum_content = tk.Frame(self._sum_tab, bg=BG)
        self._sum_content.pack(fill="both", expand=True, padx=20, pady=20)
        self._refresh_summary()

        self._usr_tab = tk.Frame(nb, bg=BG)
        nb.add(self._usr_tab, text="👤  Users")
        self._build_users_tab()

        self._log_tab = tk.Frame(nb, bg=BG)
        nb.add(self._log_tab, text="🔐  Login Log")
        self._build_login_log_tab()

        self._ses_tab = tk.Frame(nb, bg=BG)
        nb.add(self._ses_tab, text="⏱  Sessions")
        self._build_session_tab()

        self._aud_tab = tk.Frame(nb, bg=BG)
        nb.add(self._aud_tab, text="📜  Audit Log")
        self._build_audit_tab()

    # ─────────────────────────────────────────────────────────────
    # ORDERS TAB
    # ─────────────────────────────────────────────────────────────
    def _build_orders_tab(self):
        bar = tk.Frame(self._ord_tab, bg=BG, pady=6); bar.pack(fill="x", padx=8)
        tk.Button(bar, text="🔄  Refresh", font=F_SM, bg=LGRAY, fg=BLACK,
                  relief="flat", cursor="hand2", command=self._load_orders).pack(side="left")
        self._ord_count_lbl = tk.Label(bar, text="", font=F_SM, bg=BG, fg=GRAY)
        self._ord_count_lbl.pack(side="right")

        frm = tk.Frame(self._ord_tab, bg=BG); frm.pack(fill="both", expand=True, padx=8)
        self._ord_tree = ttk.Treeview(frm,
            columns=("num","date","cashier","type","items","total","method"),
            show="headings", style="Orders.Treeview")
        specs = [("num","Order #",120,"w"),("date","Date / Time",145,"w"),
                 ("cashier","Cashier",85,"center"),("type","Type",72,"center"),
                 ("items","# Items",55,"center"),("total","Total",90,"e"),
                 ("method","Payment",80,"center")]
        for col, hdg, w, anch in specs:
            self._ord_tree.heading(col, text=hdg, anchor=anch)
            self._ord_tree.column(col, width=w, anchor=anch)
        vs = ttk.Scrollbar(frm, orient="vertical",   command=self._ord_tree.yview)
        hs = ttk.Scrollbar(frm, orient="horizontal", command=self._ord_tree.xview)
        self._ord_tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        vs.pack(side="right", fill="y"); hs.pack(side="bottom", fill="x")
        self._ord_tree.pack(fill="both", expand=True)
        self._ord_tree.bind("<Double-1>", self._view_order_detail)
        tk.Label(self._ord_tab, text="Double-click an order to view full details",
                 font=F_SM, bg=BG, fg=GRAY).pack(pady=4)

    def _load_orders(self):
        for item in self._ord_tree.get_children(): self._ord_tree.delete(item)
        orders = self.db.get_orders(500)
        for row in orders:
            items = self.db.get_order_items(row["id"])
            cnt = sum(i["quantity"] for i in items)
            self._ord_tree.insert("", "end", iid=str(row["id"]), values=(
                row["order_num"], row["created_at"], row["cashier_name"],
                row["dine_option"], cnt, f"₱{row['total']:,.2f}", row["pay_method"]))
        self._ord_count_lbl.configure(text=f"{len(orders)} order(s)")
        self._refresh_summary()

    def _view_order_detail(self, event):
        sel = self._ord_tree.selection()
        if not sel: return
        oid = int(sel[0])
        with self.db.connect() as conn:
            order = conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
        items = self.db.get_order_items(oid)
        win = tk.Toplevel(self)
        win.title(f"Order Detail – {order['order_num']}")
        win.configure(bg=WHITE); win.geometry("440x540"); win.grab_set()
        vsb = tk.Scrollbar(win); vsb.pack(side="right", fill="y")
        txt = tk.Text(win, font=F_MONO, bg=WHITE, fg=BLACK, relief="flat",
                      yscrollcommand=vsb.set, state="normal", width=44, padx=10, pady=10)
        txt.pack(fill="both", expand=True); vsb.configure(command=txt.yview)
        W = 42
        def ln(t=""): txt.insert("end", t+"\n")
        def div(c="─"): txt.insert("end", c*W+"\n")
        def two(l, r): txt.insert("end", l+" "*(max(1,W-len(l)-len(r)))+r+"\n")
        div("═"); txt.insert("end", STORE_INFO["name"].center(W)+"\n"); div("═")
        two("Order  :", order["order_num"]); two("Date   :", order["created_at"])
        two("Cashier:", order["cashier_name"]); two("Type   :", order["dine_option"]); ln()
        div(); txt.insert("end", f"{'ITEM':<26} {'QTY':>3} {'TOTAL':>10}\n"); div()
        for itm in items:
            name = itm["item_name"][:24]; right = f"₱{itm['line_total']:>7,.2f}"
            two(f"{name} x{itm['quantity']}", right)
        div(); two("Subtotal", f"₱{order['subtotal']:>8,.2f}")
        two("VAT (12%)", f"₱{order['vat']:>8,.2f}"); div("═")
        two("TOTAL", f"₱{order['total']:>8,.2f}"); div("═"); ln()
        ln(f"Payment : {order['pay_method']}")
        if order["pay_method"] == "Cash":
            two("Cash", f"₱{order['amount_paid']:>8,.2f}")
            two("Change", f"₱{order['change_given']:>8,.2f}")
        txt.configure(state="disabled")

    # ─────────────────────────────────────────────────────────────
    # SUMMARY TAB
    # ─────────────────────────────────────────────────────────────
    def _refresh_summary(self):
        for w in self._sum_content.winfo_children(): w.destroy()
        s = self.db.get_today_summary()
        cnt = s["cnt"] or 0; rev = s["revenue"] or 0.0; avg = rev/cnt if cnt else 0.0
        tk.Label(self._sum_content, text="Today's Sales Summary",
                 font=F_H1, bg=BG, fg=BLACK).pack(pady=(0,20))
        for label, value, color in [
            ("Total Orders", str(cnt), BLACK),
            ("Total Revenue", f"₱{rev:,.2f}", RED),
            ("Average Order", f"₱{avg:,.2f}", SUCC),
        ]:
            card = tk.Frame(self._sum_content, bg=CARD, padx=20, pady=16, relief="solid", bd=1)
            card.pack(fill="x", pady=6)
            tk.Label(card, text=label, font=F_BODY, bg=CARD, fg=GRAY, anchor="w").pack(fill="x")
            tk.Label(card, text=value, font=("Helvetica", 26, "bold"),
                     bg=CARD, fg=color, anchor="w").pack(fill="x")
        tk.Button(self._sum_content, text="🔄  Refresh", font=F_SM, bg=LGRAY,
                  relief="flat", cursor="hand2", command=self._refresh_summary).pack(pady=14)

    # ─────────────────────────────────────────────────────────────
    # USERS TAB  (full CRUD)
    # ─────────────────────────────────────────────────────────────
    def _build_users_tab(self):
        frm = tk.Frame(self._usr_tab, bg=BG)
        frm.pack(fill="both", expand=True, padx=8, pady=8)

        # ── Toolbar ─────────────────────────────────────────────
        bar = tk.Frame(frm, bg=BG, pady=4)
        bar.pack(fill="x")

        tk.Button(bar, text="➕  Add User",
                  font=("Helvetica", 9, "bold"),
                  bg=SUCC, fg=WHITE, activebackground=SUCC_D,
                  relief="flat", cursor="hand2",
                  command=self._add_user
                  ).pack(side="left", ipadx=8, ipady=3)

        tk.Button(bar, text="✏️  Edit Selected",
                  font=("Helvetica", 9, "bold"),
                  bg=INFO, fg=WHITE,
                  relief="flat", cursor="hand2",
                  command=self._edit_user
                  ).pack(side="left", padx=(6, 0), ipadx=8, ipady=3)

        tk.Button(bar, text="🗑  Delete Selected",
                  font=("Helvetica", 9, "bold"),
                  bg=DANGER, fg=WHITE, activebackground="#8B0000",
                  relief="flat", cursor="hand2",
                  command=self._delete_user
                  ).pack(side="left", padx=(6, 0), ipadx=8, ipady=3)

        tk.Button(bar, text="🔓  Unlock Selected",
                  font=("Helvetica", 9, "bold"),
                  bg=WARN, fg=WHITE,
                  relief="flat", cursor="hand2",
                  command=self._unlock_selected_user
                  ).pack(side="left", padx=(6, 0), ipadx=8, ipady=3)

        tk.Button(bar, text="🔄  Refresh",
                  font=F_SM, bg=LGRAY, fg=BLACK,
                  relief="flat", cursor="hand2",
                  command=self._reload_users
                  ).pack(side="right")

        # ── Tree ────────────────────────────────────────────────
        tree_frm = tk.Frame(frm, bg=BG)
        tree_frm.pack(fill="both", expand=True, pady=(6, 0))

        self._usr_tree = ttk.Treeview(
            tree_frm,
            columns=("id","user","role","created","last","fails","status"),
            show="headings",
            style="Orders.Treeview")

        for col, hdg, w, anch in [
            ("id",      "ID",          40, "center"),
            ("user",    "Username",   120, "w"),
            ("role",    "Role",        80, "center"),
            ("created", "Created",    145, "w"),
            ("last",    "Last Login", 145, "w"),
            ("fails",   "Fails",       50, "center"),
            ("status",  "Status",     100, "center"),
        ]:
            self._usr_tree.heading(col, text=hdg, anchor=anch)
            self._usr_tree.column(col, width=w, anchor=anch)

        vs = ttk.Scrollbar(tree_frm, orient="vertical", command=self._usr_tree.yview)
        self._usr_tree.configure(yscrollcommand=vs.set)
        vs.pack(side="right", fill="y")
        self._usr_tree.pack(fill="both", expand=True)

        # Double-click → quick edit
        self._usr_tree.bind("<Double-1>", lambda e: self._edit_user())

        self._reload_users()

        tk.Label(self._usr_tab,
                 text="Double-click a row to edit  •  Last admin account cannot be deleted or demoted",
                 font=F_SM, bg=BG, fg=GRAY).pack(pady=5)

    def _reload_users(self):
        for item in self._usr_tree.get_children():
            self._usr_tree.delete(item)
        now = time.time()
        for row in self.db.get_all_users():
            locked = bool(row["locked_until"] and now < row["locked_until"])
            status = "🔒 Locked" if locked else "✅ Active"
            tag    = "locked"   if locked else \
                     ("admin_row" if row["role"] == "admin" else "")
            self._usr_tree.insert("", "end", iid=str(row["id"]), tags=(tag,), values=(
                row["id"], row["username"], row["role"].title(),
                row["created_at"] or "—",
                row["last_login"] or "Never",
                row["failed"], status,
            ))
        self._usr_tree.tag_configure("locked",    background="#FFEBEE")
        self._usr_tree.tag_configure("admin_row", background="#FFFDE7")

    def _get_selected_user_row(self):
        """Returns the selected user's sqlite3.Row or None."""
        sel = self._usr_tree.selection()
        if not sel:
            return None
        uid = int(sel[0])
        return self.db.get_user_by_id(uid)

    def _add_user(self):
        UserFormDialog(self, self.db, self.auth, mode="add",
                       on_save=self._reload_users)

    def _edit_user(self):
        row = self._get_selected_user_row()
        if row is None:
            messagebox.showinfo("No Selection",
                                "Please select a user to edit.", parent=self)
            return
        UserFormDialog(self, self.db, self.auth, mode="edit",
                       user_row=row, on_save=self._reload_users)

    def _delete_user(self):
        row = self._get_selected_user_row()
        if row is None:
            messagebox.showinfo("No Selection",
                                "Please select a user to delete.", parent=self)
            return

        uname = row["username"]
        uid   = row["id"]

        # Prevent deleting your own account
        if uid == self.auth.user["id"]:
            messagebox.showwarning("Cannot Delete",
                "You cannot delete your own account while logged in.", parent=self)
            return

        # Prevent deleting the last admin
        if row["role"] == "admin" and self.db.count_admins() <= 1:
            messagebox.showwarning("Cannot Delete",
                "Cannot delete the last admin account.\n"
                "Promote another user to admin first.", parent=self)
            return

        # Confirmation — extra explicit for destructive action
        confirm = messagebox.askyesno(
            "⚠  Confirm Deletion",
            f"Permanently delete user '{uname}'?\n\n"
            "This action cannot be undone.\n"
            "Their order history will be preserved.",
            icon="warning", parent=self)
        if not confirm:
            return

        self.db.delete_user(uid)
        self.db.audit(self.auth.user["username"], "USER_DELETED",
                      f"Deleted user '{uname}' (id={uid})", self.auth.user["id"])
        self._reload_users()
        messagebox.showinfo("Deleted",
                            f"User '{uname}' has been deleted.", parent=self)

    def _unlock_selected_user(self):
        row = self._get_selected_user_row()
        if row is None:
            messagebox.showinfo("No Selection",
                                "Please select a user to unlock.", parent=self)
            return
        name = row["username"]; uid = row["id"]
        if messagebox.askyesno("Unlock User",
                               f"Unlock account '{name}' and reset failed attempts?",
                               parent=self):
            self.db.unlock_user(uid)
            self.db.audit(self.auth.user["username"], "USER_UNLOCKED",
                          f"Unlocked account: {name}", self.auth.user["id"])
            self._reload_users()
            messagebox.showinfo("Success",
                                f"Account '{name}' has been unlocked.", parent=self)

    # ─────────────────────────────────────────────────────────────
    # LOGIN LOG TAB
    # ─────────────────────────────────────────────────────────────
    def _build_login_log_tab(self):
        self._log_stats_frame = tk.Frame(self._log_tab, bg=BG, padx=10, pady=8)
        self._log_stats_frame.pack(fill="x")
        self._build_login_stats()
        ttk.Separator(self._log_tab, orient="horizontal").pack(fill="x", padx=8)

        bar = tk.Frame(self._log_tab, bg=BG, pady=6); bar.pack(fill="x", padx=8)
        tk.Button(bar, text="🔄  Refresh", font=F_SM, bg=LGRAY, fg=BLACK,
                  relief="flat", cursor="hand2", command=self._reload_login_log).pack(side="left")
        tk.Label(bar, text="  Filter:", font=F_SM, bg=BG, fg=GRAY).pack(side="left")
        self._log_filter = tk.StringVar(value="All")
        for txt, val in [("All","All"),("✅ Success","Success"),("✖ Failed","Failed")]:
            tk.Radiobutton(bar, text=txt, variable=self._log_filter, value=val,
                           font=F_SM, bg=BG, fg=BLACK, selectcolor=YELLOW,
                           activebackground=BG, command=self._reload_login_log
                           ).pack(side="left", padx=(4,0))
        self._log_count_lbl = tk.Label(bar, text="", font=F_SM, bg=BG, fg=GRAY)
        self._log_count_lbl.pack(side="right")

        frm = tk.Frame(self._log_tab, bg=BG); frm.pack(fill="both", expand=True, padx=8, pady=(0,4))
        self._log_tree = ttk.Treeview(frm,
            columns=("id","username","result","reason","session","timestamp"),
            show="headings", style="Orders.Treeview", selectmode="browse")
        for col, hdg, w, anch in [
            ("id","#",40,"center"),("username","Username",110,"w"),
            ("result","Result",80,"center"),("reason","Reason / Info",330,"w"),
            ("session","Session ID",200,"w"),("timestamp","Timestamp",145,"w")]:
            self._log_tree.heading(col, text=hdg, anchor=anch)
            self._log_tree.column(col, width=w, anchor=anch)
        vs = ttk.Scrollbar(frm, orient="vertical",   command=self._log_tree.yview)
        hs = ttk.Scrollbar(frm, orient="horizontal", command=self._log_tree.xview)
        self._log_tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        vs.pack(side="right", fill="y"); hs.pack(side="bottom", fill="x")
        self._log_tree.pack(fill="both", expand=True)
        self._log_tree.tag_configure("success", background="#E8F5E9")
        self._log_tree.tag_configure("fail",    background="#FFEBEE")
        self._reload_login_log()

    def _build_login_stats(self):
        for w in self._log_stats_frame.winfo_children(): w.destroy()
        s = self.db.get_login_stats()
        tot = s["total"] if s else 0; ok = s["successes"] if s else 0; bad = s["failures"] if s else 0
        tk.Label(self._log_stats_frame, text="Today's Login Activity",
                 font=F_H2, bg=BG, fg=BLACK).pack(side="left", padx=(0,16))
        for label, value, color in [
            ("Total Attempts", str(tot), BLACK),
            ("✅ Successful",   str(ok),  SUCC),
            ("✖ Failed",        str(bad), DANGER),
        ]:
            pill = tk.Frame(self._log_stats_frame, bg=CARD, padx=12, pady=6, relief="solid", bd=1)
            pill.pack(side="left", padx=6)
            tk.Label(pill, text=label, font=F_SM, bg=CARD, fg=GRAY).pack()
            tk.Label(pill, text=value, font=("Helvetica", 18, "bold"), bg=CARD, fg=color).pack()

    def _reload_login_log(self):
        self._build_login_stats(); flt = self._log_filter.get()
        for item in self._log_tree.get_children(): self._log_tree.delete(item)
        rows = self.db.get_login_log(500); shown = 0
        for row in rows:
            success = bool(row["success"])
            if flt == "Success" and not success: continue
            if flt == "Failed" and success: continue
            result_txt = "✅ Success" if success else "✖ Failed"
            tag        = "success"   if success else "fail"
            self._log_tree.insert("", "end", tags=(tag,), values=(
                row["id"], row["username"], result_txt,
                row["reason"] or "—", row["session_id"] or "—", row["logged_at"]))
            shown += 1
        self._log_count_lbl.configure(text=f"{shown} record(s)")

    # ─────────────────────────────────────────────────────────────
    # SESSION LOG TAB
    # ─────────────────────────────────────────────────────────────
    def _build_session_tab(self):
        bar = tk.Frame(self._ses_tab, bg=BG, pady=6); bar.pack(fill="x", padx=8)
        tk.Button(bar, text="🔄  Refresh", font=F_SM, bg=LGRAY, fg=BLACK,
                  relief="flat", cursor="hand2", command=self._reload_sessions).pack(side="left")
        self._ses_count_lbl = tk.Label(bar, text="", font=F_SM, bg=BG, fg=GRAY)
        self._ses_count_lbl.pack(side="right")

        frm = tk.Frame(self._ses_tab, bg=BG); frm.pack(fill="both", expand=True, padx=8, pady=(0,4))
        self._ses_tree = ttk.Treeview(frm,
            columns=("id","user","session","login_at","logout_at","duration","type"),
            show="headings", style="Orders.Treeview", selectmode="browse")
        for col, hdg, w, anch in [
            ("id","#",40,"center"),("user","Username",100,"w"),
            ("session","Session ID",200,"w"),("login_at","Login Time",145,"w"),
            ("logout_at","Logout Time",145,"w"),("duration","Duration",90,"center"),
            ("type","Logout Type",95,"center")]:
            self._ses_tree.heading(col, text=hdg, anchor=anch)
            self._ses_tree.column(col, width=w, anchor=anch)
        vs = ttk.Scrollbar(frm, orient="vertical",   command=self._ses_tree.yview)
        hs = ttk.Scrollbar(frm, orient="horizontal", command=self._ses_tree.xview)
        self._ses_tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        vs.pack(side="right", fill="y"); hs.pack(side="bottom", fill="x")
        self._ses_tree.pack(fill="both", expand=True)
        self._ses_tree.tag_configure("active",  background="#E3F2FD")
        self._ses_tree.tag_configure("timeout", background="#FFF3E0")
        self._reload_sessions()
        tk.Label(self._ses_tab,
                 text="Blue = active session  |  Orange = session ended by timeout",
                 font=F_SM, bg=BG, fg=GRAY).pack(pady=4)

    def _reload_sessions(self):
        for item in self._ses_tree.get_children(): self._ses_tree.delete(item)
        rows = self.db.get_session_log(200)
        for row in rows:
            dur_s = row["duration_s"]
            dur_t = f"{dur_s//60}m {dur_s%60}s" if dur_s is not None else "Active"
            ltype = row["logout_type"] or "—"
            tag   = "active"  if row["logout_at"] is None else \
                    ("timeout" if ltype == "timeout" else "")
            self._ses_tree.insert("", "end", tags=(tag,), values=(
                row["id"], row["username"], row["session_id"],
                row["login_at"], row["logout_at"] or "—", dur_t, ltype))
        self._ses_count_lbl.configure(text=f"{len(rows)} record(s)")

    # ─────────────────────────────────────────────────────────────
    # AUDIT LOG TAB
    # ─────────────────────────────────────────────────────────────
    def _build_audit_tab(self):
        bar = tk.Frame(self._aud_tab, bg=BG, pady=6); bar.pack(fill="x", padx=8)
        tk.Button(bar, text="🔄  Refresh", font=F_SM, bg=LGRAY, fg=BLACK,
                  relief="flat", cursor="hand2", command=self._reload_audit).pack(side="left")
        tk.Label(bar, text="  Filter:", font=F_SM, bg=BG, fg=GRAY).pack(side="left")
        self._aud_filter = tk.StringVar(value="All")
        for txt in ["All","LOGIN","LOGOUT","ORDER_PLACED","USER_CREATED","USER_EDITED","USER_DELETED","USER_UNLOCKED"]:
            tk.Radiobutton(bar, text=txt, variable=self._aud_filter, value=txt,
                           font=F_SM, bg=BG, fg=BLACK, selectcolor=YELLOW,
                           activebackground=BG, command=self._reload_audit
                           ).pack(side="left", padx=(4,0))
        self._aud_count_lbl = tk.Label(bar, text="", font=F_SM, bg=BG, fg=GRAY)
        self._aud_count_lbl.pack(side="right")

        frm = tk.Frame(self._aud_tab, bg=BG); frm.pack(fill="both", expand=True, padx=8, pady=(0,4))
        self._aud_tree = ttk.Treeview(frm,
            columns=("id","user","action","detail","timestamp"),
            show="headings", style="Orders.Treeview", selectmode="browse")
        for col, hdg, w, anch in [
            ("id","#",40,"center"),("user","User",100,"w"),
            ("action","Action",140,"center"),("detail","Details",420,"w"),
            ("timestamp","Time",145,"w")]:
            self._aud_tree.heading(col, text=hdg, anchor=anch)
            self._aud_tree.column(col, width=w, anchor=anch)
        vs = ttk.Scrollbar(frm, orient="vertical",   command=self._aud_tree.yview)
        hs = ttk.Scrollbar(frm, orient="horizontal", command=self._aud_tree.xview)
        self._aud_tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        vs.pack(side="right", fill="y"); hs.pack(side="bottom", fill="x")
        self._aud_tree.pack(fill="both", expand=True)
        AUDIT_COLORS = {
            "LOGIN":         "#E8F5E9",
            "LOGOUT":        "#F3E5F5",
            "ORDER_PLACED":  "#E3F2FD",
            "USER_CREATED":  "#E0F7FA",
            "USER_EDITED":   "#FFF8E1",
            "USER_DELETED":  "#FFEBEE",
            "USER_UNLOCKED": "#FFF3E0",
        }
        for action, bg in AUDIT_COLORS.items():
            self._aud_tree.tag_configure(action, background=bg)
        self._reload_audit()
        tk.Label(self._aud_tab,
                 text="Full immutable record of all significant system actions.",
                 font=F_SM, bg=BG, fg=GRAY).pack(pady=4)

    def _reload_audit(self):
        flt = self._aud_filter.get()
        for item in self._aud_tree.get_children(): self._aud_tree.delete(item)
        rows = self.db.get_audit_log(500); shown = 0
        for row in rows:
            action = row["action"]
            if flt != "All" and action != flt: continue
            self._aud_tree.insert("", "end", tags=(action,), values=(
                row["id"], row["username"], action,
                row["detail"] or "—", row["logged_at"]))
            shown += 1
        self._aud_count_lbl.configure(text=f"{shown} record(s)")


# ══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════
def main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()