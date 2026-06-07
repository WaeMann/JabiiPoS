import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import hashlib
import secrets
import time
import datetime
from PIL import Image, ImageTk
import os

# ══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════
APP_TITLE    = "Jollibee Point of Sale System"
DB_FILE      = "jollibee_pos.db"
VAT_RATE     = 0.12        # 12% Philippine VAT
MAX_ATTEMPTS = 5           # Login attempts before lockout
LOCKOUT_SECS = 300         # 5-minute account lockout
PBKDF2_ITERS = 200_000     # Password hashing iterations

STORE_INFO = {
    "name":    "JOLLIBEE",
    "branch":  "Katipunan Branch",
    "address": "123 Katipunan Ave., Quezon City",
    "tel":     "(02) 8911-JOLLY",
    "tin":     "123-456-789-000",
}

# ══════════════════════════════════════════════════════════════════
# COLOR PALETTE  (Jollibee brand)
# ══════════════════════════════════════════════════════════════════
RED    = "#CC0000";  RED_D    = "#990000"
YELLOW = "#FFC200";  YELLOW_D = "#E5A800"
WHITE  = "#FFFFFF";  BLACK    = "#1A1A1A"
GRAY   = "#777777";  LGRAY    = "#F0F0F0"
BG     = "#F4F4F4";  CARD     = "#FFFFFF"
SIDEBAR= "#252525";  SIDEBAR2 = "#1A1A1A"
SUCC   = "#2E7D32";  SUCC_D   = "#1A5C22"
DANGER = "#C62828";  BORDER   = "#DDDDDD"

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
# MENU DATA  (Jollibee Philippines)
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
    """Handles all SQLite operations."""

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
# AUTHENTICATION MANAGER
# ══════════════════════════════════════════════════════════════════
class AuthManager:
    """Handles login, logout, and session state."""

    def __init__(self, db: Database):
        self.db   = db
        self.user = None   # dict of logged-in user on success

    @staticmethod
    def _hash(password: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), PBKDF2_ITERS
        ).hex()

    def login(self, username: str, password: str):
        """Returns (success: bool, message: str). Sets self.user on success."""
        row = self.db.get_user(username)
        if row is None:
            # Perform dummy hash to prevent user-enumeration via timing
            hashlib.pbkdf2_hmac("sha256", password.encode(), b"dummy", PBKDF2_ITERS)
            return False, "Invalid username or password."

        uid = row["id"]
        now = time.time()

        # Check lockout
        if row["locked_until"] and now < row["locked_until"]:
            remaining = int(row["locked_until"] - now)
            m, s = divmod(remaining, 60)
            return False, f"Account locked. Try again in {m}m {s}s."

        # Verify password (constant-time comparison)
        expected = self._hash(password, row["salt"])
        if not secrets.compare_digest(expected, row["password_hash"]):
            new_fails = row["failed"] + 1
            if new_fails >= MAX_ATTEMPTS:
                self.db.record_fail(uid, now + LOCKOUT_SECS)
                return False, (
                    f"Too many failed attempts. "
                    f"Account locked for {LOCKOUT_SECS // 60} minutes."
                )
            self.db.record_fail(uid, 0)
            left = MAX_ATTEMPTS - new_fails
            return False, (
                f"Invalid username or password. "
                f"{left} attempt{'s' if left != 1 else ''} remaining."
            )

        # Success
        self.db.record_success(uid)
        self.user = dict(row)
        return True, "OK"

    def logout(self):
        self.user = None

    @property
    def is_admin(self) -> bool:
        return bool(self.user and self.user.get("role") == "admin")


# ══════════════════════════════════════════════════════════════════
# APP  (root Tk window)
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

    # ── Frame switching ───────────────────────────────────────────
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
        if isinstance(self._frame, POSFrame) and self._frame._clock_job:
            try:
                self._frame.after_cancel(self._frame._clock_job)
            except Exception:
                pass
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
        # Grid weights to center the card
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)
        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)
        self.columnconfigure(2, weight=1)

        # Card
        card = tk.Frame(self, bg=WHITE, padx=52, pady=44)
        card.grid(row=1, column=1)

        # ── Logo ────────────────────────────────────────────────
        logo_f = tk.Frame(card, bg=WHITE)
        logo_f.pack(pady=(0, 22))

        logo_img = Image.open("JollibeeLogo.png")  # Path to your PNG
        logo_img = logo_img.resize((100, 100))  # Adjust size as needed
        self.logo_photo = ImageTk.PhotoImage(logo_img)

        tk.Label(
            logo_f,
            image=self.logo_photo,
            bg=WHITE
        ).pack()

        # ── Form ────────────────────────────────────────────────
        form = tk.Frame(card, bg=WHITE)
        form.pack()

        # Username
        tk.Label(form, text="Username", font=F_H3, bg=WHITE, fg=BLACK, anchor="w").pack(
            fill="x", pady=(0, 4))
        self._uname = tk.StringVar()
        self._uname_e = tk.Entry(
            form, textvariable=self._uname, font=F_BODY,
            relief="solid", bd=1, width=30, bg=WHITE)
        self._uname_e.pack(fill="x", ipady=8, pady=(0, 14))

        # Password
        tk.Label(form, text="Password", font=F_H3, bg=WHITE, fg=BLACK, anchor="w").pack(
            fill="x", pady=(0, 4))
        pwd_row = tk.Frame(form, bg=WHITE)
        pwd_row.pack(fill="x", pady=(0, 4))

        self._pwd = tk.StringVar()
        self._pwd_e = tk.Entry(
            pwd_row, textvariable=self._pwd, font=F_BODY,
            show="●", relief="solid", bd=1, bg=WHITE)
        self._pwd_e.pack(side="left", fill="x", expand=True, ipady=8)

        self._eye_on = False
        tk.Button(
            pwd_row, text="👁", font=("Helvetica", 12),
            bg=WHITE, fg=GRAY, relief="flat", cursor="hand2",
            command=self._toggle_eye
        ).pack(side="right", padx=(5, 0))

        # Status label
        self._status = tk.StringVar()
        tk.Label(
            form, textvariable=self._status,
            font=F_SM, bg=WHITE, fg=DANGER,
            wraplength=290, justify="center"
        ).pack(fill="x", pady=(8, 0))

        # Login button
        self._login_btn = tk.Button(
            form, text="LOG IN",
            font=("Helvetica", 13, "bold"),
            bg=RED, fg=WHITE, activebackground=RED_D, activeforeground=WHITE,
            relief="flat", cursor="hand2",
            command=self._do_login, pady=11, width=28)
        self._login_btn.pack(pady=(16, 0))

        # Key bindings
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
# POS FRAME  (main screen)
# ══════════════════════════════════════════════════════════════════
class POSFrame(tk.Frame):
    def __init__(self, parent, db: Database, auth: AuthManager, on_logout):
        super().__init__(parent, bg=BG)
        self.db        = db
        self.auth      = auth
        self.on_logout = on_logout

        # State
        self.cart       = {}    # {item_name: {"price": float, "qty": int}}
        self._pay_meth  = "Cash"
        self._dine_var  = tk.StringVar(value="Dine In")
        self._clock_job = None
        self._cat_btns  = {}
        self._cur_cat   = CATEGORIES[0]

        self._setup_styles()
        self._build()
        self._update_clock()
        self._load_category(CATEGORIES[0])

    # ── Styles ───────────────────────────────────────────────────
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

    # ── Layout ───────────────────────────────────────────────────
    def _build(self):
        self._build_header()

        content = tk.Frame(self, bg=BG)
        content.pack(fill="both", expand=True)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)

        # Left: category sidebar
        sidebar = tk.Frame(content, bg=SIDEBAR, width=175)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        self._build_sidebar(sidebar)

        # Middle: menu items (scrollable)
        self._menu_frame = tk.Frame(content, bg=BG)
        self._menu_frame.grid(row=0, column=1, sticky="nsew")
        self._build_menu_area(self._menu_frame)

        # Right: order cart + payment
        right = tk.Frame(content, bg=CARD, width=345)
        right.grid(row=0, column=2, sticky="nsew")
        right.grid_propagate(False)
        self._build_right_panel(right)

    # ── Header ────────────────────────────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self, bg=RED)
        hdr.pack(fill="x", side="top")
        logo_img = Image.open("JollibeeMascot.png")
        logo_img = logo_img.resize((45, 45))  # Adjust size for header
        self.logo_photo = ImageTk.PhotoImage(logo_img)

        # Left
        left = tk.Frame(hdr, bg=RED)
        left.pack(side="left", padx=14, pady=8)
        tk.Label(
            left,
            image=self.logo_photo,
            bg=RED
        ).pack(side="left", padx=(0, 6))

        # Title
        tk.Label(
            left,
            text="Jollibee",
            font=("Helvetica", 15, "bold"),
            bg=RED,
            fg=WHITE
        ).pack(side="left")
        tk.Label(left, text=f"  │  {STORE_INFO['branch']}",
                 font=("Helvetica", 10), bg=RED, fg="#FFBBBB").pack(side="left")

        # Right
        right = tk.Frame(hdr, bg=RED)
        right.pack(side="right", padx=14, pady=8)

        if self.auth.is_admin:
            tk.Button(right, text="⚙ Admin",
                      font=F_SM, bg=YELLOW_D, fg=BLACK,
                      relief="flat", cursor="hand2",
                      command=self._show_admin
                      ).pack(side="right", padx=(6, 0))

        tk.Button(right, text="⏻ Logout",
                  font=F_SM, bg=RED_D, fg=WHITE, activebackground="#660000",
                  relief="flat", cursor="hand2",
                  command=self._logout
                  ).pack(side="right", padx=(6, 0))

        self._today_lbl = tk.Label(right, text="", font=F_SM, bg=RED, fg="#FFBBBB")
        self._today_lbl.pack(side="right", padx=(6, 0))

        self._clock_lbl = tk.Label(right, text="", font=("Courier New", 10), bg=RED, fg=WHITE)
        self._clock_lbl.pack(side="right", padx=(6, 0))

        tk.Label(right, text=f"👤  {self.auth.user['username'].title()}",
                 font=("Helvetica", 11, "bold"), bg=RED, fg=YELLOW
                 ).pack(side="right", padx=(6, 0))

        self._refresh_today_counter()

    # ── Sidebar ───────────────────────────────────────────────────
    def _build_sidebar(self, parent):
        tk.Label(parent, text="MENU CATEGORIES",
                 font=("Helvetica", 8), bg=SIDEBAR2, fg="#666666",
                 pady=7).pack(fill="x")

        for cat in CATEGORIES:
            btn = tk.Button(
                parent, text=cat,
                font=("Helvetica", 10, "bold"), anchor="w",
                padx=14, pady=11,
                bg=SIDEBAR, fg=WHITE,
                activebackground=YELLOW, activeforeground=BLACK,
                relief="flat", cursor="hand2",
                command=lambda c=cat: self._load_category(c))
            btn.pack(fill="x")

            def _enter(e, b=btn, c=cat):
                if c != self._cur_cat:
                    b.configure(bg="#3C3C3C")

            def _leave(e, b=btn, c=cat):
                if c != self._cur_cat:
                    b.configure(bg=SIDEBAR)

            btn.bind("<Enter>", _enter)
            btn.bind("<Leave>", _leave)
            self._cat_btns[cat] = btn

        # Footer
        foot = tk.Frame(parent, bg=SIDEBAR)
        foot.pack(side="bottom", fill="x", pady=10)
        tk.Label(foot, text=f"VAT: {int(VAT_RATE*100)}% inclusive",
                 font=F_SM, bg=SIDEBAR, fg="#555555").pack()
        tk.Label(foot, text="v2.0  © Jollibee POS",
                 font=("Helvetica", 8), bg=SIDEBAR, fg="#3A3A3A").pack()

    # ── Menu area (scrollable) ─────────────────────────────────────
    def _build_menu_area(self, parent):
        self._cat_title = tk.Label(parent, text="",
                                   font=F_H1, bg=BG, fg=BLACK,
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

        # Mouse-wheel scrolling (cross-platform)
        def _mw(e):
            self._items_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        self._items_canvas.bind("<MouseWheel>", _mw)
        self._items_canvas.bind("<Button-4>",
                                lambda e: self._items_canvas.yview_scroll(-1, "units"))
        self._items_canvas.bind("<Button-5>",
                                lambda e: self._items_canvas.yview_scroll(1, "units"))

    # ── Right panel ───────────────────────────────────────────────
    def _build_right_panel(self, parent):
        # Header
        rh = tk.Frame(parent, bg=RED, pady=7)
        rh.pack(fill="x", side="top")
        tk.Label(rh, text="ORDER", font=F_H2, bg=RED, fg=WHITE).pack(side="left", padx=12)
        self._badge = tk.Label(rh, text="0 items",
                               font=F_SM, bg=RED_D, fg=WHITE, padx=8, pady=2)
        self._badge.pack(side="right", padx=8)

        # Bottom controls (pack BEFORE cart so they stay pinned)
        bottom = tk.Frame(parent, bg=CARD)
        bottom.pack(fill="x", side="bottom")
        self._build_controls(bottom)

        # Cart (fills remaining space)
        cart_f = tk.Frame(parent, bg=CARD)
        cart_f.pack(fill="both", expand=True)
        self._build_cart_tree(cart_f)

    def _build_cart_tree(self, parent):
        self._cart_tree = ttk.Treeview(
            parent,
            columns=("name", "qty", "price", "total"),
            show="headings",
            style="Cart.Treeview",
            selectmode="browse")

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
        # Qty row
        qty_f = tk.Frame(parent, bg=LGRAY, pady=5)
        qty_f.pack(fill="x")

        tk.Button(qty_f, text=" − ", font=F_H2,
                  bg=WHITE, fg=DANGER, relief="flat", cursor="hand2",
                  command=lambda: self._adjust_qty(-1)
                  ).pack(side="left", padx=(8, 4))

        self._sel_lbl = tk.Label(qty_f, text="Select an item",
                                  font=F_SM, bg=LGRAY, fg=GRAY)
        self._sel_lbl.pack(side="left", fill="x", expand=True)

        tk.Button(qty_f, text=" + ", font=F_H2,
                  bg=WHITE, fg=SUCC, relief="flat", cursor="hand2",
                  command=lambda: self._adjust_qty(1)
                  ).pack(side="right", padx=(4, 8))

        # Remove / Clear
        act_f = tk.Frame(parent, bg=CARD, pady=4, padx=8)
        act_f.pack(fill="x")

        tk.Button(act_f, text="🗑  Remove",
                  font=F_SM, bg=DANGER, fg=WHITE, activebackground="#8B0000",
                  relief="flat", cursor="hand2",
                  command=self._remove_selected
                  ).pack(side="left", ipadx=8, ipady=3)

        tk.Button(act_f, text="✖  Clear All",
                  font=F_SM, bg="#555555", fg=WHITE, activebackground="#333333",
                  relief="flat", cursor="hand2",
                  command=self._clear_cart
                  ).pack(side="right", ipadx=8, ipady=3)

        ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=4)

        # Dine option
        dine_f = tk.Frame(parent, bg=CARD, padx=10, pady=3)
        dine_f.pack(fill="x")
        tk.Label(dine_f, text="Order Type:", font=F_H3, bg=CARD, fg=BLACK).pack(side="left")
        for opt in ("Dine In", "Take Out"):
            tk.Radiobutton(dine_f, text=opt, variable=self._dine_var, value=opt,
                           font=F_BODY, bg=CARD, fg=BLACK,
                           selectcolor=YELLOW, activebackground=CARD
                           ).pack(side="left", padx=(8, 0))

        ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=4)

        # Totals
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
        tk.Label(total_row, text="TOTAL",
                 font=("Helvetica", 13, "bold"), bg=CARD, fg=BLACK).pack(side="left")
        self._total_lbl = tk.Label(total_row, text="₱0.00",
                                    font=("Helvetica", 17, "bold"), bg=CARD, fg=RED)
        self._total_lbl.pack(side="right")

        ttk.Separator(parent, orient="horizontal").pack(fill="x", padx=8, pady=5)

        # Payment method
        pay_f = tk.Frame(parent, bg=CARD, padx=10, pady=2)
        pay_f.pack(fill="x")
        tk.Label(pay_f, text="Payment Method:", font=F_H3, bg=CARD, fg=BLACK).pack(anchor="w", pady=(0, 5))

        btn_row = tk.Frame(pay_f, bg=CARD)
        btn_row.pack(fill="x")

        self._pay_btns = {}
        for lbl, val in [("💵 Cash", "Cash"), ("💳 Card", "Card"), ("📱 E-Wallet", "E-Wallet")]:
            b = tk.Button(btn_row, text=lbl,
                          font=("Helvetica", 9, "bold"),
                          bg=LGRAY, fg=BLACK, activebackground=YELLOW_D,
                          relief="flat", cursor="hand2",
                          command=lambda v=val: self._set_pay_method(v))
            b.pack(side="left", fill="x", expand=True, padx=2)
            self._pay_btns[val] = b

        self._set_pay_method("Cash")

        # Process button
        self._process_btn = tk.Button(
            parent, text="💳   PROCESS PAYMENT",
            font=("Helvetica", 12, "bold"),
            bg=SUCC, fg=WHITE, activebackground=SUCC_D,
            relief="flat", cursor="hand2",
            command=self._process_payment, pady=12, state="disabled")
        self._process_btn.pack(fill="x", padx=10, pady=(8, 5))

    # ── Category loading ─────────────────────────────────────────
    def _load_category(self, category: str):
        # Update sidebar highlights
        for cat, btn in self._cat_btns.items():
            btn.configure(bg=YELLOW if cat == category else SIDEBAR,
                          fg=BLACK  if cat == category else WHITE)
        self._cur_cat = category
        self._cat_title.configure(text=category)

        # Repopulate items
        for w in self._items_frame.winfo_children():
            w.destroy()

        items = MENU[category]
        cols  = 3

        for i, (name, price) in enumerate(items):
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
                orig = frm.cget("highlightbackground")
                frm.configure(highlightbackground=SUCC)
                frm.after(250, lambda: frm.configure(highlightbackground=BORDER))

            tk.Button(card, text="＋ ADD TO ORDER",
                      font=("Helvetica", 9, "bold"),
                      bg=YELLOW, fg=BLACK, activebackground=YELLOW_D,
                      relief="flat", cursor="hand2",
                      command=_add_item
                      ).pack(fill="x", padx=10, pady=(6, 10), ipady=5)

        self._items_canvas.yview_moveto(0)

    # ── Cart operations ───────────────────────────────────────────
    def _add_to_cart(self, name: str, price: float):
        if name in self.cart:
            self.cart[name]["qty"] += 1
        else:
            self.cart[name] = {"price": price, "qty": 1}
        self._refresh_cart()

    def _refresh_cart(self):
        # Preserve selection
        sel = self._get_selected_name()

        for item in self._cart_tree.get_children():
            self._cart_tree.delete(item)

        subtotal   = 0.0
        item_count = 0
        for name, data in self.cart.items():
            qty   = data["qty"]
            price = data["price"]
            line  = qty * price
            subtotal   += line
            item_count += qty
            self._cart_tree.insert("", "end", iid=name, values=(
                name, qty, f"₱{price:,.2f}", f"₱{line:,.2f}"))

        vat   = round(subtotal * VAT_RATE, 2)
        total = round(subtotal + vat, 2)

        self._sub_lbl.configure(text=f"₱{subtotal:,.2f}")
        self._vat_lbl.configure(text=f"₱{vat:,.2f}")
        self._total_lbl.configure(text=f"₱{total:,.2f}")

        self._badge.configure(
            text=f"{item_count} item{'s' if item_count != 1 else ''}")

        self._process_btn.configure(state="normal" if self.cart else "disabled")

        # Restore selection
        if sel and sel in self.cart:
            try:
                self._cart_tree.selection_set(sel)
            except Exception:
                pass
        self._update_sel_label()

    def _get_selected_name(self):
        sel = self._cart_tree.selection()
        return sel[0] if sel else None

    def _update_sel_label(self):
        name = self._get_selected_name()
        if name and name in self.cart:
            qty   = self.cart[name]["qty"]
            short = (name[:18] + "…") if len(name) > 18 else name
            self._sel_lbl.configure(text=f"{short}  ×{qty}")
        elif self.cart:
            self._sel_lbl.configure(text="← Select an item")
        else:
            self._sel_lbl.configure(text="Cart is empty")

    def _adjust_qty(self, delta: int):
        name = self._get_selected_name()
        if not name:
            messagebox.showinfo("No Selection", "Please select an item in the cart first.",
                                parent=self)
            return
        new_qty = self.cart[name]["qty"] + delta
        if new_qty <= 0:
            del self.cart[name]
        else:
            self.cart[name]["qty"] = new_qty
        self._refresh_cart()
        if name in self.cart:
            try:
                self._cart_tree.selection_set(name)
            except Exception:
                pass

    def _remove_selected(self):
        name = self._get_selected_name()
        if not name:
            messagebox.showinfo("No Selection", "Please select an item to remove.",
                                parent=self)
            return
        del self.cart[name]
        self._refresh_cart()

    def _clear_cart(self):
        if not self.cart:
            return
        if messagebox.askyesno("Clear Order",
                               "Remove all items from the current order?",
                               parent=self):
            self.cart.clear()
            self._refresh_cart()

    def _edit_qty_dialog(self, event):
        """Double-click cart item → open qty editor."""
        name = self._get_selected_name()
        if not name or name not in self.cart:
            return

        win = tk.Toplevel(self)
        win.title("Edit Quantity")
        win.configure(bg=WHITE)
        win.resizable(False, False)
        win.grab_set()

        w, h = 300, 190
        x = self.winfo_x() + (self.winfo_width()  - w) // 2
        y = self.winfo_y() + (self.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{max(0,x)}+{max(0,y)}")

        tk.Label(win, text="Edit Quantity", font=F_H2, bg=WHITE, fg=BLACK).pack(pady=(14, 4))
        short = (name[:30] + "…") if len(name) > 30 else name
        tk.Label(win, text=short, font=F_SM, bg=WHITE, fg=GRAY,
                 wraplength=260, justify="center").pack()

        qty_var = tk.IntVar(value=self.cart[name]["qty"])
        spin = tk.Spinbox(win, from_=1, to=99, textvariable=qty_var,
                          font=F_H1, width=7, justify="center")
        spin.pack(pady=10)

        def apply():
            try:
                q = int(qty_var.get())
                if q < 1 or q > 99:
                    raise ValueError
                self.cart[name]["qty"] = q
                self._refresh_cart()
                try:
                    self._cart_tree.selection_set(name)
                except Exception:
                    pass
                win.destroy()
            except Exception:
                messagebox.showerror("Invalid", "Enter a valid quantity (1–99).", parent=win)

        tk.Button(win, text="✓  Update", font=F_H3,
                  bg=SUCC, fg=WHITE, activebackground=SUCC_D,
                  relief="flat", cursor="hand2", command=apply
                  ).pack(ipadx=24, ipady=6)

        spin.focus_set()
        win.bind("<Return>", lambda e: apply())

    # ── Payment ───────────────────────────────────────────────────
    def _set_pay_method(self, method: str):
        self._pay_meth = method
        for val, btn in self._pay_btns.items():
            btn.configure(bg=YELLOW if val == method else LGRAY,
                          fg=BLACK)

    def _get_totals(self):
        subtotal = sum(d["price"] * d["qty"] for d in self.cart.values())
        vat      = round(subtotal * VAT_RATE, 2)
        total    = round(subtotal + vat, 2)
        return subtotal, vat, total

    def _process_payment(self):
        if not self.cart:
            return
        _, _, total = self._get_totals()
        PaymentDialog(self, total, self._pay_meth, self._complete_order)

    def _complete_order(self, pay_data: dict):
        order_num = self.db.next_order_num()
        now       = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        items = [
            {"name": n, "qty": d["qty"], "price": d["price"],
             "total": round(d["qty"] * d["price"], 2)}
            for n, d in self.cart.items()
        ]
        subtotal = sum(i["total"] for i in items)
        vat      = round(subtotal * VAT_RATE, 2)
        total    = round(subtotal + vat, 2)

        order_data = {
            "order_num":    order_num,
            "cashier_id":   self.auth.user["id"],
            "cashier_name": self.auth.user["username"],
            "dine_option":  self._dine_var.get(),
            "subtotal":     subtotal,
            "vat":          vat,
            "total":        total,
            "pay_method":   pay_data["method"],
            "amount_paid":  pay_data["paid"],
            "change_given": pay_data["change"],
            "items":        items,
            "datetime":     now,
        }

        self.db.save_order(order_data)
        ReceiptWindow(self, order_data)

        self.cart.clear()
        self._refresh_cart()
        self._refresh_today_counter()

    # ── Admin / Logout ─────────────────────────────────────────────
    def _show_admin(self):
        AdminPanel(self, self.db, self.auth)

    def _logout(self):
        if self.cart:
            if not messagebox.askyesno(
                "Logout", "You have unsaved items in the cart.\nLogout anyway?",
                    parent=self):
                return
        if self._clock_job:
            self.after_cancel(self._clock_job)
            self._clock_job = None
        self.auth.logout()
        self.on_logout()

    # ── Helpers ───────────────────────────────────────────────────
    def _update_clock(self):
        now = datetime.datetime.now().strftime("%b %d, %Y  %I:%M:%S %p")
        self._clock_lbl.configure(text=now)
        self._clock_job = self.after(1000, self._update_clock)

    def _refresh_today_counter(self):
        try:
            s   = self.db.get_today_summary()
            cnt = s["cnt"] or 0
            rev = s["revenue"] or 0.0
            self._today_lbl.configure(
                text=f"Today: {cnt} orders  ₱{rev:,.2f}")
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════
# PAYMENT DIALOG
# ══════════════════════════════════════════════════════════════════
class PaymentDialog(tk.Toplevel):
    def __init__(self, parent, total: float, method: str, on_complete):
        super().__init__(parent)
        self.total       = total
        self.method      = method
        self.on_complete = on_complete
        self._amount_str = ""
        self._cash_paid  = 0.0
        self._change     = 0.0

        self.title("Process Payment")
        self.configure(bg=WHITE)
        self.update_idletasks()
        self.grab_set()
        self.resizable(False, False)

        self.update_idletasks()

        w = 430
        h = 700 if method == "Cash" else 400

        self.geometry(f"{w}x{h}")
        self.minsize(w, h)
        x = parent.winfo_x() + (parent.winfo_width()  - 390) // 2
        y = parent.winfo_y() + (parent.winfo_height() - h)   // 2
        self.geometry(f"+{max(0,x)}+{max(0,y)}")

        self._build()
        self.focus_set()

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=RED, pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="💳  PROCESS PAYMENT", font=F_H1, bg=RED, fg=WHITE).pack()

        badge_col = {"Cash": "#1B6630", "Card": "#1565C0", "E-Wallet": "#6A1B9A"}.get(
            self.method, GRAY)
        tk.Label(hdr, text=f"  {self.method}  ",
                 font=("Helvetica", 10, "bold"), bg=badge_col, fg=WHITE,
                 pady=3).pack(pady=(4, 0))

        # Amount due
        due = tk.Frame(self, bg=LGRAY, pady=12)
        due.pack(fill="x")
        tk.Label(due, text="AMOUNT DUE", font=F_SM, bg=LGRAY, fg=GRAY).pack()
        tk.Label(due, text=f"₱{self.total:,.2f}",
                 font=("Helvetica", 28, "bold"), bg=LGRAY, fg=RED).pack()

        if self.method == "Cash":
            self._build_cash()
        else:
            self._build_digital()

    # ── Cash UI ────────────────────────────────────────────────────
    def _build_cash(self):
        entry_f = tk.Frame(self, bg=WHITE, padx=20, pady=8)
        entry_f.pack(fill="x")
        tk.Label(entry_f, text="Cash Received:", font=F_H3, bg=WHITE, fg=BLACK, anchor="w").pack(
            fill="x")

        self._display = tk.Label(
            entry_f, text="₱0",
            font=("Helvetica", 22, "bold"), bg=LGRAY, fg=BLACK,
            anchor="e", padx=12, pady=6, relief="groove")
        self._display.pack(fill="x")

        self._chg_lbl = tk.Label(entry_f, text="Change: ₱0.00",
                                  font=("Helvetica", 12, "bold"), bg=WHITE, fg=GRAY)
        self._chg_lbl.pack(anchor="e", pady=(4, 0))

        # Quick amounts
        quick_f = tk.Frame(self, bg=WHITE, padx=20, pady=4)
        quick_f.pack(fill="x")
        tk.Label(quick_f, text="Quick: ", font=F_SM, bg=WHITE, fg=GRAY).pack(side="left")

        for amt in self._quick_amounts():
            tk.Button(quick_f, text=f"₱{amt:,}",
                      font=("Helvetica", 9, "bold"),
                      bg=YELLOW, fg=BLACK, relief="flat", cursor="hand2",
                      command=lambda a=amt: self._set_quick(a)
                      ).pack(side="left", padx=2, ipadx=5, ipady=2)

        # Numpad
        np_f = tk.Frame(self, bg=WHITE)
        np_f.pack(padx=20, pady=6)

        keys = [("7","8","9"), ("4","5","6"), ("1","2","3"), ("C","0","⌫")]
        for r, row in enumerate(keys):
            for c, key in enumerate(row):
                special = key in ("C", "⌫")
                tk.Button(
                    np_f, text=key,
                    font=("Helvetica", 14, "bold"),
                    bg=LGRAY if special else WHITE,
                    fg=DANGER if special else BLACK,
                    relief="groove", cursor="hand2",
                    width=5, height=2,
                    command=lambda k=key: self._numpad(k)
                ).grid(row=r, column=c, padx=3, pady=3)

        # Keyboard input support
        self.bind("<Key>", self._key_press)

        self._confirm_btn = tk.Button(
            self, text="✓   CONFIRM PAYMENT",
            font=("Helvetica", 12, "bold"),
            bg=SUCC, fg=WHITE, activebackground=SUCC_D,
            relief="flat", cursor="hand2",
            command=self._confirm, pady=10, state="disabled")
        self._confirm_btn.pack(fill="x", padx=20, pady=(4, 15))

    def _build_digital(self):
        body = tk.Frame(self, bg=WHITE)
        body.pack(fill="both", expand=True, padx=20, pady=20)

        icon = {"Card": "💳", "E-Wallet": "📱"}.get(self.method, "💰")
        tk.Label(body, text=icon, font=("Helvetica", 52), bg=WHITE).pack(pady=8)
        tk.Label(body,
                 text=f"Process {self.method} payment\non the terminal, then confirm.",
                 font=("Helvetica", 12), bg=WHITE, fg=GRAY, justify="center").pack()

        tk.Button(
            self, text="✓   PAYMENT RECEIVED",
            font=("Helvetica", 12, "bold"),
            bg=SUCC, fg=WHITE, activebackground=SUCC_D,
            relief="flat", cursor="hand2",
            command=self._confirm, pady=12
        ).pack(fill="x", padx=20, pady=(10, 20))

    def _quick_amounts(self):
        t, seen = self.total, set()
        result  = []
        for mult in (50, 100, 200, 500, 1000):
            v = (int(t) // mult + 1) * mult
            if v >= t and v not in seen:
                seen.add(v)
                result.append(v)
        return sorted(result)[:4]

    def _numpad(self, key: str):
        if key == "C":
            self._amount_str = ""
        elif key == "⌫":
            self._amount_str = self._amount_str[:-1]
        elif key.isdigit() and len(self._amount_str) < 6:
            if self._amount_str == "" and key == "0":
                return
            self._amount_str += key
        val = float(self._amount_str) if self._amount_str else 0.0
        self._update_display(val)

    def _key_press(self, event):
        k = event.char
        if k.isdigit():
            self._numpad(k)
        elif k in ("\x08", "\x7f"):   # Backspace / Delete
            self._numpad("⌫")
        elif k.lower() == "c":
            self._numpad("C")
        elif event.keysym == "Return" and self._confirm_btn["state"] == "normal":
            self._confirm()

    def _set_quick(self, amount: float):
        self._amount_str = str(int(amount))
        self._update_display(float(amount))

    def _update_display(self, val: float):
        self._display.configure(text=f"₱{val:,.0f}")
        change = val - self.total
        if change >= 0:
            self._chg_lbl.configure(text=f"Change: ₱{change:,.2f}", fg=SUCC)
            self._confirm_btn.configure(state="normal")
            self._cash_paid = val
            self._change    = change
        else:
            self._chg_lbl.configure(text=f"Short:  ₱{abs(change):,.2f}", fg=DANGER)
            self._confirm_btn.configure(state="disabled")

    def _confirm(self):
        if self.method == "Cash":
            self.on_complete({"method": "Cash",
                              "paid":   self._cash_paid,
                              "change": self._change})
        else:
            self.on_complete({"method": self.method,
                              "paid":   self.total,
                              "change": 0.0})
        self.destroy()


# ══════════════════════════════════════════════════════════════════
# RECEIPT WINDOW
# ══════════════════════════════════════════════════════════════════
class ReceiptWindow(tk.Toplevel):
    def __init__(self, parent, order_data: dict):
        super().__init__(parent)
        self.order = order_data
        self.title(f"Receipt – {order_data['order_num']}")
        self.configure(bg=WHITE)
        self.resizable(False, True)
        self.overrideredirect(True)

        w, h = 430, 600
        x = parent.winfo_x() + (parent.winfo_width()  - w) // 2
        y = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{max(0,x)}+{max(0,y)}")
        self.minsize(w, 400)

        self._build()

    def _build(self):
        bar = tk.Frame(self, bg=LGRAY, pady=7)
        bar.pack(fill="x")

        tk.Button(bar, text="🖨  Print / Save", font=F_BODY,
                  bg=WHITE, relief="groove", cursor="hand2",
                  command=self._print).pack(side="left", padx=10)

        tk.Button(bar, text="New Order  →", font=F_BODY,
                  bg=SUCC, fg=WHITE, relief="flat", cursor="hand2",
                  command=self.destroy).pack(side="right", padx=10)

        txt_f = tk.Frame(self, bg=WHITE)
        txt_f.pack(fill="both", expand=True, padx=12, pady=(4, 12))

        vsb = tk.Scrollbar(txt_f)
        vsb.pack(side="right", fill="y")

        self._txt = tk.Text(txt_f, font=F_MONO, bg=WHITE, fg=BLACK,
                             relief="flat", yscrollcommand=vsb.set,
                             width=44, state="normal", wrap="none")
        self._txt.pack(fill="both", expand=True)
        vsb.configure(command=self._txt.yview)

        self._render()
        self._txt.configure(state="disabled")

    def _render(self):
        o = self.order
        W = 44   # receipt width

        def ln(text="", align="l"):
            if align == "c":
                out = text.center(W)
            elif align == "r":
                out = text.rjust(W)
            else:
                out = text
            self._txt.insert("end", out + "\n")

        def div(ch="─"):
            self._txt.insert("end", ch * W + "\n")

        def two_col(left, right):
            gap = max(1, W - len(left) - len(right))
            self._txt.insert("end", left + " " * gap + right + "\n")

        div("═")
        ln(STORE_INFO["name"],    "c")
        ln(STORE_INFO["branch"],  "c")
        ln(STORE_INFO["address"], "c")
        ln(f"Tel: {STORE_INFO['tel']}", "c")
        ln(f"TIN: {STORE_INFO['tin']}", "c")
        div("═")
        ln()
        two_col("Order  :", o["order_num"])
        two_col("Date   :", o["datetime"])
        two_col("Cashier:", o["cashier_name"])
        two_col("Type   :", o["dine_option"])
        ln()
        div()
        self._txt.insert("end", f"{'ITEM':<26} {'QTY':>3} {'TOTAL':>12}\n")
        div()

        for itm in o["items"]:
            name  = itm["name"][:24]
            right = f"₱{itm['total']:>8,.2f}"
            label = f"{name} x{itm['qty']}"
            gap   = max(1, W - len(label) - len(right))
            self._txt.insert("end", label + " " * gap + right + "\n")

        div()
        two_col("Subtotal",  f"₱{o['subtotal']:>8,.2f}")
        two_col("VAT (12%)", f"₱{o['vat']:>8,.2f}")
        div("═")
        two_col("TOTAL",     f"₱{o['total']:>8,.2f}")
        div("═")
        ln()
        ln(f"Payment : {o['pay_method']}")

        if o["pay_method"] == "Cash":
            two_col("Cash Received", f"₱{o['amount_paid']:>8,.2f}")
            two_col("Change",        f"₱{o['change_given']:>8,.2f}")

        ln()
        div()
        ln("Thank you for dining at JOLLIBEE!", "c")
        ln('"Bida ang saya!"', "c")
        div()
        ln("*** Customer Copy ***", "c")
        ln()

    def _print(self):
        messagebox.showinfo(
            "Print Receipt",
            f"Receipt {self.order['order_num']} sent to printer.\n\n"
            "(Connect a receipt printer and configure it\n"
            "in the system settings to enable printing.)",
            parent=self)


# ══════════════════════════════════════════════════════════════════
# ADMIN PANEL
# ══════════════════════════════════════════════════════════════════
class AdminPanel(tk.Toplevel):
    def __init__(self, parent, db: Database, auth: AuthManager):
        super().__init__(parent)
        self.db   = db
        self.auth = auth
        self.overrideredirect(True)

        self.title("Admin Panel – Jollibee POS")
        self.configure(bg=BG)

        w, h = 960, 630
        x = parent.winfo_x() + max(0, (parent.winfo_width()  - w) // 2)
        y = parent.winfo_y() + max(0, (parent.winfo_height() - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(800, 500)

        self._build()
        self._load_orders()

    def _build(self):
        hdr = tk.Frame(self, bg=SIDEBAR, pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="⚙   ADMIN PANEL",
                 font=F_H1, bg=SIDEBAR, fg=YELLOW).pack(side="left", padx=20)
        tk.Label(hdr, text=f"Logged in as: {self.auth.user['username']}",
                 font=F_SM, bg=SIDEBAR, fg="#888888").pack(side="left", padx=10)
        tk.Button(hdr, text="✖  Close",
                  font=F_SM, bg=DANGER, fg=WHITE, relief="flat", cursor="hand2",
                  command=self.destroy).pack(side="right", padx=20)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        # ── Orders tab ──────────────────────────────────────────
        self._ord_tab = tk.Frame(nb, bg=BG)
        nb.add(self._ord_tab, text="📋  Orders")
        self._build_orders_tab()

        # ── Summary tab ─────────────────────────────────────────
        self._sum_tab = tk.Frame(nb, bg=BG)
        nb.add(self._sum_tab, text="📊  Today's Summary")
        self._sum_content = tk.Frame(self._sum_tab, bg=BG)
        self._sum_content.pack(fill="both", expand=True, padx=20, pady=20)
        self._refresh_summary()

        # ── Users tab ────────────────────────────────────────────
        self._usr_tab = tk.Frame(nb, bg=BG)
        nb.add(self._usr_tab, text="👤  Users")
        self._build_users_tab()

    # ── Orders tab ────────────────────────────────────────────────
    def _build_orders_tab(self):
        bar = tk.Frame(self._ord_tab, bg=BG, pady=6)
        bar.pack(fill="x", padx=8)

        tk.Button(bar, text="🔄  Refresh", font=F_SM,
                  bg=LGRAY, fg=BLACK, relief="flat", cursor="hand2",
                  command=self._load_orders).pack(side="left")

        self._ord_count_lbl = tk.Label(bar, text="", font=F_SM, bg=BG, fg=GRAY)
        self._ord_count_lbl.pack(side="right")

        frm = tk.Frame(self._ord_tab, bg=BG)
        frm.pack(fill="both", expand=True, padx=8)

        self._ord_tree = ttk.Treeview(
            frm,
            columns=("num","date","cashier","type","items","total","method"),
            show="headings",
            style="Orders.Treeview")

        specs = [
            ("num",     "Order #",       120, "w"),
            ("date",    "Date / Time",   145, "w"),
            ("cashier", "Cashier",        85, "center"),
            ("type",    "Type",           72, "center"),
            ("items",   "# Items",        55, "center"),
            ("total",   "Total",           90, "e"),
            ("method",  "Payment",         80, "center"),
        ]
        for col, hdg, w, anch in specs:
            self._ord_tree.heading(col, text=hdg, anchor=anch)
            self._ord_tree.column(col, width=w,  anchor=anch)

        vs = ttk.Scrollbar(frm, orient="vertical",   command=self._ord_tree.yview)
        hs = ttk.Scrollbar(frm, orient="horizontal", command=self._ord_tree.xview)
        self._ord_tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)

        vs.pack(side="right",  fill="y")
        hs.pack(side="bottom", fill="x")
        self._ord_tree.pack(fill="both", expand=True)

        self._ord_tree.bind("<Double-1>", self._view_order_detail)
        tk.Label(self._ord_tab, text="Double-click an order to view full details",
                 font=F_SM, bg=BG, fg=GRAY).pack(pady=4)

    def _load_orders(self):
        for item in self._ord_tree.get_children():
            self._ord_tree.delete(item)

        orders = self.db.get_orders(500)
        for row in orders:
            items = self.db.get_order_items(row["id"])
            cnt   = sum(i["quantity"] for i in items)
            self._ord_tree.insert("", "end", iid=str(row["id"]), values=(
                row["order_num"],
                row["created_at"],
                row["cashier_name"],
                row["dine_option"],
                cnt,
                f"₱{row['total']:,.2f}",
                row["pay_method"],
            ))

        self._ord_count_lbl.configure(text=f"{len(orders)} order(s)")
        self._refresh_summary()

    def _view_order_detail(self, event):
        sel = self._ord_tree.selection()
        if not sel:
            return
        oid = int(sel[0])

        with self.db.connect() as conn:
            order = conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
        items = self.db.get_order_items(oid)

        win = tk.Toplevel(self)
        self.overrideredirect(True)
        win.title(f"Order Detail – {order['order_num']}")
        win.configure(bg=WHITE)
        win.geometry("440x540")
        win.grab_set()

        vsb = tk.Scrollbar(win)
        vsb.pack(side="right", fill="y")

        txt = tk.Text(win, font=F_MONO, bg=WHITE, fg=BLACK,
                      relief="flat", yscrollcommand=vsb.set, state="normal",
                      width=44, padx=10, pady=10)
        txt.pack(fill="both", expand=True)
        vsb.configure(command=txt.yview)

        W = 42
        def ln(t=""): txt.insert("end", t + "\n")
        def div(c="─"): txt.insert("end", c * W + "\n")
        def two(l, r): txt.insert("end", l + " "*(max(1,W-len(l)-len(r))) + r + "\n")

        div("═")
        txt.insert("end", STORE_INFO["name"].center(W) + "\n")
        div("═")
        two("Order  :", order["order_num"])
        two("Date   :", order["created_at"])
        two("Cashier:", order["cashier_name"])
        two("Type   :", order["dine_option"])
        ln()
        div()
        txt.insert("end", f"{'ITEM':<26} {'QTY':>3} {'TOTAL':>10}\n")
        div()
        for itm in items:
            name  = itm["item_name"][:24]
            right = f"₱{itm['line_total']:>7,.2f}"
            label = f"{name} x{itm['quantity']}"
            two(label, right)
        div()
        two("Subtotal",  f"₱{order['subtotal']:>8,.2f}")
        two("VAT (12%)", f"₱{order['vat']:>8,.2f}")
        div("═")
        two("TOTAL",     f"₱{order['total']:>8,.2f}")
        div("═")
        ln()
        ln(f"Payment : {order['pay_method']}")
        if order["pay_method"] == "Cash":
            two("Cash",   f"₱{order['amount_paid']:>8,.2f}")
            two("Change", f"₱{order['change_given']:>8,.2f}")

        txt.configure(state="disabled")

    # ── Summary tab ───────────────────────────────────────────────
    def _refresh_summary(self):
        for w in self._sum_content.winfo_children():
            w.destroy()

        s   = self.db.get_today_summary()
        cnt = s["cnt"] or 0
        rev = s["revenue"] or 0.0
        avg = rev / cnt if cnt else 0.0

        tk.Label(self._sum_content, text="Today's Sales Summary",
                 font=F_H1, bg=BG, fg=BLACK).pack(pady=(0, 20))

        for label, value, color in [
            ("Total Orders",   str(cnt),        BLACK),
            ("Total Revenue",  f"₱{rev:,.2f}",  RED),
            ("Average Order",  f"₱{avg:,.2f}",  SUCC),
        ]:
            card = tk.Frame(self._sum_content, bg=CARD,
                            padx=20, pady=16, relief="solid", bd=1)
            card.pack(fill="x", pady=6)
            tk.Label(card, text=label, font=F_BODY, bg=CARD, fg=GRAY, anchor="w").pack(fill="x")
            tk.Label(card, text=value, font=("Helvetica", 26, "bold"),
                     bg=CARD, fg=color, anchor="w").pack(fill="x")

        tk.Button(self._sum_content, text="🔄  Refresh",
                  font=F_SM, bg=LGRAY, relief="flat", cursor="hand2",
                  command=self._refresh_summary).pack(pady=14)

    # ── Users tab ─────────────────────────────────────────────────
    def _build_users_tab(self):
        frm = tk.Frame(self._usr_tab, bg=BG)
        frm.pack(fill="both", expand=True, padx=8, pady=8)

        utree = ttk.Treeview(
            frm,
            columns=("id","user","role","last","fails","status"),
            show="headings",
            style="Orders.Treeview")

        for col, hdg, w, anch in [
            ("id",     "ID",         40, "center"),
            ("user",   "Username",  110, "w"),
            ("role",   "Role",       80, "center"),
            ("last",   "Last Login",170, "w"),
            ("fails",  "Fails",      50, "center"),
            ("status", "Status",    110, "center"),
        ]:
            utree.heading(col, text=hdg, anchor=anch)
            utree.column(col, width=w,   anchor=anch)

        vs = ttk.Scrollbar(frm, orient="vertical", command=utree.yview)
        utree.configure(yscrollcommand=vs.set)
        vs.pack(side="right", fill="y")
        utree.pack(fill="both", expand=True)

        now = time.time()
        for row in self.db.get_all_users():
            locked = bool(row["locked_until"] and now < row["locked_until"])
            status = "🔒 Locked" if locked else "✅ Active"
            utree.insert("", "end", values=(
                row["id"],
                row["username"],
                row["role"].title(),
                row["last_login"] or "Never",
                row["failed"],
                status,
            ))

        tk.Label(self._usr_tab,
                 text="User management (add/edit/delete) available via DB administration tools.",
                 font=F_SM, bg=BG, fg=GRAY).pack(pady=6)


# ══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════
def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
