from pathlib import Path
import sqlite3
from functools import wraps

from flask import Flask, flash, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "shoplab.db"

app = Flask(__name__)
app.config.update(SECRET_KEY="shoplab-local-lab-only", LAB_MODE=True)


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    connection = g.pop("db", None)
    if connection:
        connection.close()


def init_db():
    connection = sqlite3.connect(DATABASE)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'customer',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, description TEXT
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY, category_id INTEGER NOT NULL, name TEXT NOT NULL,
            description TEXT NOT NULL, price REAL NOT NULL, stock INTEGER NOT NULL,
            image_url TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(category_id) REFERENCES categories(id)
        );
        CREATE TABLE IF NOT EXISTS addresses (
            id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, recipient_name TEXT NOT NULL,
            phone TEXT NOT NULL, address TEXT NOT NULL, city TEXT NOT NULL, postal_code TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS carts (
            id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS cart_items (
            id INTEGER PRIMARY KEY, cart_id INTEGER NOT NULL, product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(cart_id) REFERENCES carts(id) ON DELETE CASCADE,
            FOREIGN KEY(product_id) REFERENCES products(id)
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, address_id INTEGER,
            total_price REAL NOT NULL, status TEXT NOT NULL DEFAULT 'Processing',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(address_id) REFERENCES addresses(id)
        );
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL, product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL, price REAL NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id), FOREIGN KEY(product_id) REFERENCES products(id)
        );
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL, payment_method TEXT NOT NULL,
            payment_status TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(order_id) REFERENCES orders(id)
        );
        CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
        CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
        """
    )
    if connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        users = [
            ("Alice Morgan", "alice@shoplab.test", "alice123", "customer"),
            ("Bob Carter", "bob@shoplab.test", "bob123", "customer"),
            ("Charlie Lee", "charlie@shoplab.test", "charlie123", "customer"),
            ("Lab Admin", "admin@shoplab.test", "admin123", "admin"),
        ]
        connection.executemany(
            "INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",
            [(n, e, generate_password_hash(p), r) for n, e, p, r in users],
        )
        categories = ["New arrivals", "Workspace", "Home", "Travel", "Accessories"]
        connection.executemany("INSERT INTO categories(name,description) VALUES(?,?)", [(c, "Curated ShopLab collection") for c in categories])
        products = [
            ("Canvas Tote", "A roomy everyday carryall.", 28, 38, "Workspace"),
            ("Daily Planner", "Undated planner for better days.", 22, 24, "Workspace"),
            ("Stone Mug", "Hand-finished ceramic mug.", 18, 30, "Home"),
            ("Desk Lamp", "Warm, focused light for late work.", 74, 12, "Home"),
            ("Linen Throw", "Soft textured layer for the sofa.", 96, 9, "Home"),
            ("Travel Bottle", "Insulated stainless steel bottle.", 32, 40, "Travel"),
            ("Weekender Bag", "Lightweight bag for short escapes.", 118, 11, "Travel"),
            ("Passport Wallet", "Slim recycled leather wallet.", 44, 18, "Travel"),
            ("Classic Cap", "Structured cotton cap.", 26, 22, "Accessories"),
            ("Everyday Socks", "Three pairs of organic cotton socks.", 20, 45, "Accessories"),
            ("Silver Hoops", "Minimal polished hoops.", 36, 16, "Accessories"),
            ("Leather Belt", "Vegetable-tanned leather belt.", 58, 13, "Accessories"),
            ("Relaxed Shirt", "Crisp cotton shirt with an easy fit.", 68, 20, "New arrivals"),
            ("Ribbed Sweater", "A soft layer for cooler evenings.", 84, 15, "New arrivals"),
            ("Utility Jacket", "Lightweight jacket with practical pockets.", 130, 8, "New arrivals"),
            ("Cotton Candle", "A clean, cedarwood scent.", 34, 27, "Home"),
            ("Journal Set", "Three notebooks for ideas and notes.", 24, 31, "Workspace"),
            ("Laptop Sleeve", "Padded sleeve in recycled fabric.", 52, 19, "Workspace"),
            ("Canvas Pouch", "Small pouch for daily essentials.", 18, 35, "Accessories"),
            ("Travel Blanket", "Compact blanket for long journeys.", 62, 14, "Travel"),
        ]
        category_ids = {row[1]: row[0] for row in connection.execute("SELECT id,name FROM categories")}
        connection.executemany(
            "INSERT INTO products(category_id,name,description,price,stock,image_url) VALUES(?,?,?,?,?,?)",
            [(category_ids[c], n, d, p, s, f"https://picsum.photos/seed/shoplab-{i}/700/850") for i, (n, d, p, s, c) in enumerate(products)],
        )
        for user_id, name, city in [(1, "Alice Morgan", "Bandung"), (2, "Bob Carter", "Jakarta"), (3, "Charlie Lee", "Surabaya")]:
            connection.execute(
                "INSERT INTO addresses(user_id,recipient_name,phone,address,city,postal_code) VALUES(?,?,?,?,?,?)",
                (user_id, name, "0812-0000-0000", f"Jl. Demo Lab No. {user_id}", city, "40111"),
            )
            connection.execute("INSERT OR IGNORE INTO carts(user_id) VALUES(?)", (user_id,))
            cart_id = connection.execute("SELECT id FROM carts WHERE user_id=?", (user_id,)).fetchone()[0]
            connection.execute("INSERT OR IGNORE INTO cart_items(cart_id,product_id,quantity) VALUES(?,?,?)", (cart_id, user_id, 1))
        for user_id in (1, 2, 3):
            for offset in range(3):
                item_id = (user_id - 1) * 3 + offset + 1
                product = connection.execute("SELECT id,price FROM products WHERE id=?", (item_id,)).fetchone()
                total = product[1] * (offset + 1)
                status = ("Delivered", "Processing", "Shipped")[offset]
                order_id = 1001 + offset * 3 + (user_id - 1)
                cursor = connection.execute("INSERT INTO orders(id,user_id,address_id,total_price,status) VALUES(?,?,?,?,?)", (order_id, user_id, user_id, total, status))
                connection.execute("INSERT INTO order_items(order_id,product_id,quantity,price) VALUES(?,?,?,?)", (cursor.lastrowid, product[0], offset + 1, product[1]))
                connection.execute("INSERT INTO payments(order_id,payment_method,payment_status) VALUES(?,?,?)", (cursor.lastrowid, "Virtual account", "Paid"))
    connection.commit()
    connection.close()


@app.before_request
def ensure_database():
    init_db()


def current_user():
    user_id = session.get("user_id")
    return db().execute("SELECT id,name,email,role FROM users WHERE id=?", (user_id,)).fetchone() if user_id else None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Silakan masuk terlebih dahulu.", "error")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_globals():
    return {"user": current_user(), "cart_count": sum(session.get("cart", {}).values())}


@app.route("/")
def home():
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "")
    sql = "SELECT p.*, c.name AS category FROM products p JOIN categories c ON c.id=p.category_id WHERE 1=1"
    params = []
    if query:
        sql += " AND (p.name LIKE ? OR p.description LIKE ?)"
        params.extend([f"%{query}%", f"%{query}%"])
    if category:
        sql += " AND c.name=?"
        params.append(category)
    products = db().execute(sql + " ORDER BY p.id DESC", params).fetchall()
    return render_template("index.html", products=products, categories=db().execute("SELECT * FROM categories").fetchall(), query=query, selected_category=category)


@app.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        user = db().execute("SELECT * FROM users WHERE email=?", (request.form["email"].strip(),)).fetchone()
        if user and check_password_hash(user["password_hash"], request.form["password"]):
            session["user_id"] = user["id"]
            return redirect(request.args.get("next") or url_for("home"))
        flash("Email atau password salah.", "error")
    return render_template("auth.html", mode="login")


@app.post("/api/auth/login")
def api_login():
    data = request.get_json(silent=True) or request.form
    email = str(data.get("email", "")).strip()
    password = str(data.get("password", ""))
    user = db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify(error="Email atau password salah"), 401
    session["user_id"] = user["id"]
    return jsonify({"authenticated": True, "user": {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"]}})


@app.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        try:
            cursor = db().execute("INSERT INTO users(name,email,password_hash) VALUES(?,?,?)", (request.form["name"], request.form["email"].lower(), generate_password_hash(request.form["password"])))
            db().execute("INSERT INTO addresses(user_id,recipient_name,phone,address,city,postal_code) VALUES(?,?,?,?,?,?)", (cursor.lastrowid, request.form["name"], "-", "Alamat belum diatur", "-", "-"))
            db().commit()
            flash("Akun berhasil dibuat. Silakan masuk.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email sudah digunakan.", "error")
    return render_template("auth.html", mode="register")


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.post("/cart/add/<int:product_id>")
def add_to_cart(product_id):
    if not db().execute("SELECT id FROM products WHERE id=?", (product_id,)).fetchone():
        return jsonify(error="Produk tidak ditemukan"), 404
    cart = session.setdefault("cart", {})
    key = str(product_id)
    cart[key] = cart.get(key, 0) + 1
    session.modified = True
    flash("Produk ditambahkan ke keranjang.", "success")
    return redirect(request.referrer or url_for("home"))


@app.get("/cart")
def cart():
    items = []
    for product_id, quantity in session.get("cart", {}).items():
        product = db().execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        if product:
            items.append({"product": product, "quantity": quantity, "subtotal": product["price"] * quantity})
    return render_template("cart.html", items=items, total=sum(item["subtotal"] for item in items))


@app.post("/cart/update/<int:product_id>")
def update_cart(product_id):
    quantity = request.form.get("quantity", type=int, default=1)
    cart = session.setdefault("cart", {})
    key = str(product_id)
    if quantity < 1:
        cart.pop(key, None)
    else:
        cart[key] = quantity
    session.modified = True
    return redirect(url_for("cart"))


@app.post("/cart/remove/<int:product_id>")
def remove_from_cart(product_id):
    cart = session.setdefault("cart", {})
    cart.pop(str(product_id), None)
    session.modified = True
    flash("Produk dihapus dari keranjang.", "success")
    return redirect(url_for("cart"))


@app.get("/product/<int:product_id>")
def product_detail(product_id):
    product = db().execute(
        "SELECT p.*, c.name AS category FROM products p JOIN categories c ON c.id=p.category_id WHERE p.id=?",
        (product_id,),
    ).fetchone()
    if not product:
        return "Produk tidak ditemukan.", 404
    related = db().execute(
        "SELECT p.*, c.name AS category FROM products p JOIN categories c ON c.id=p.category_id WHERE p.category_id=? AND p.id!=? LIMIT 4",
        (product["category_id"], product_id),
    ).fetchall()
    return render_template("product_detail.html", product=product, related=related)


@app.get("/profile")
@login_required
def profile():
    address = db().execute("SELECT * FROM addresses WHERE user_id=? LIMIT 1", (session["user_id"],)).fetchone()
    return render_template("profile.html", address=address)


@app.post("/profile")
@login_required
def update_profile():
    connection = db()
    connection.execute("UPDATE users SET name=? WHERE id=?", (request.form["name"], session["user_id"]))
    address = connection.execute("SELECT id FROM addresses WHERE user_id=? LIMIT 1", (session["user_id"],)).fetchone()
    values = (request.form["recipient_name"], request.form["phone"], request.form["address"], request.form["city"], request.form["postal_code"])
    if address:
        connection.execute("UPDATE addresses SET recipient_name=?,phone=?,address=?,city=?,postal_code=? WHERE id=?", (*values, address["id"]))
    else:
        connection.execute("INSERT INTO addresses(user_id,recipient_name,phone,address,city,postal_code) VALUES(?,?,?,?,?,?)", (session["user_id"], *values))
    connection.commit()
    flash("Profil berhasil diperbarui.", "success")
    return redirect(url_for("profile"))


@app.post("/checkout")
@login_required
def checkout():
    cart_items = session.get("cart", {})
    if not cart_items:
        flash("Keranjang masih kosong.", "error")
        return redirect(url_for("cart"))
    connection = db()
    total = 0
    products = []
    for product_id, quantity in cart_items.items():
        product = connection.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        if product and product["stock"] >= quantity:
            products.append((product, quantity))
            total += product["price"] * quantity
    if not products:
        flash("Produk dalam keranjang sudah tidak tersedia.", "error")
        return redirect(url_for("cart"))
    address = connection.execute("SELECT id FROM addresses WHERE user_id=? LIMIT 1", (session["user_id"],)).fetchone()
    order = connection.execute("INSERT INTO orders(user_id,address_id,total_price,status) VALUES(?,?,?,?)", (session["user_id"], address["id"], total, "Processing"))
    for product, quantity in products:
        connection.execute("INSERT INTO order_items(order_id,product_id,quantity,price) VALUES(?,?,?,?)", (order.lastrowid, product["id"], quantity, product["price"]))
        connection.execute("UPDATE products SET stock=stock-? WHERE id=?", (quantity, product["id"]))
    connection.execute("INSERT INTO payments(order_id,payment_method,payment_status) VALUES(?,?,?)", (order.lastrowid, "Virtual account", "Paid"))
    connection.commit()
    session["cart"] = {}
    flash(f"Pesanan #{order.lastrowid} berhasil dibuat.", "success")
    return redirect(url_for("order_detail", order_id=order.lastrowid))


@app.get("/orders")
@login_required
def orders():
    return render_template("orders.html", orders=db().execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC", (session["user_id"],)).fetchall())


def order_payload(order_id, enforce_owner=True):
    sql = """SELECT o.*, u.name, a.recipient_name, a.phone, a.address, a.city, a.postal_code
             FROM orders o JOIN users u ON u.id=o.user_id LEFT JOIN addresses a ON a.id=o.address_id
             WHERE o.id=?"""
    params = [order_id]
    if enforce_owner:
        sql += " AND o.user_id=?"
        params.append(session["user_id"])
    order = db().execute(sql, params).fetchone()
    if not order:
        return None
    return {"order": order, "items": db().execute("SELECT oi.*, p.name FROM order_items oi JOIN products p ON p.id=oi.product_id WHERE oi.order_id=?", (order_id,)).fetchall()}


@app.get("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    payload = order_payload(order_id)
    if not payload:
        return "Order tidak ditemukan atau akses ditolak.", 404
    return render_template("order_detail.html", **payload)


@app.get("/api/products/search")
def secure_product_search():
    q = request.args.get("q", "")
    return jsonify([dict(row) for row in db().execute("SELECT id,name,price FROM products WHERE name LIKE ? LIMIT 50", (f"%{q}%",)).fetchall()])


@app.get("/api/products")
def api_products():
    rows = db().execute(
        "SELECT p.*, c.name AS category FROM products p JOIN categories c ON c.id=p.category_id ORDER BY p.id"
    ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.get("/api/orders")
@login_required
def api_orders():
    rows = db().execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC", (session["user_id"],)).fetchall()
    return jsonify([dict(row) for row in rows])


@app.get("/api/lab/products/search")
def vulnerable_product_search():
    q = request.args.get("q", "")
    if ";" in q or any(word in q.lower().split() for word in ("drop", "delete", "update", "insert", "attach", "pragma")):
        return jsonify(error="Lab route hanya mengizinkan demonstrasi SELECT terkontrol."), 400
    try:
        rows = db().execute(f"SELECT id,name,price FROM products WHERE name LIKE '%{q}%' LIMIT 50").fetchall()
        return jsonify([dict(row) for row in rows])
    except sqlite3.Error as error:
        return jsonify(error=str(error)), 400


@app.post("/api/lab/login")
def vulnerable_login():
    email, password = request.form.get("email", ""), request.form.get("password", "")
    if ";" in email or ";" in password:
        return jsonify(error="Stacked queries tidak diizinkan di lab."), 400
    try:
        user = db().execute(f"SELECT id,name,email,role,password_hash FROM users WHERE email='{email}' AND password_hash='{password}'").fetchone()
    except sqlite3.Error as error:
        return jsonify(error=str(error)), 400
    safe_user = {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"]} if user else None
    return jsonify({"authenticated": bool(user), "user": safe_user})


@app.get("/api/lab/orders/<int:order_id>")
@login_required
def vulnerable_order(order_id):
    payload = order_payload(order_id, enforce_owner=False)
    return jsonify(error="Order tidak ditemukan") if not payload else jsonify({"order": dict(payload["order"]), "items": [dict(row) for row in payload["items"]], "lab": "IDOR vulnerable"})


@app.patch("/api/lab/orders/<int:order_id>")
@login_required
def vulnerable_order_update(order_id):
    status = request.form.get("status") or (request.get_json(silent=True) or {}).get("status")
    if status not in {"Processing", "Shipped", "Delivered", "Cancelled"}:
        return jsonify(error="Status tidak valid"), 400
    order = db().execute("SELECT id FROM orders WHERE id=?", (order_id,)).fetchone()
    if not order:
        return jsonify(error="Order tidak ditemukan"), 404
    db().execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    db().commit()
    return jsonify({"updated": True, "order_id": order_id, "status": status, "lab": "IDOR vulnerable"})


@app.get("/api/orders/<int:order_id>")
@login_required
def secure_order(order_id):
    payload = order_payload(order_id)
    if not payload:
        return jsonify(error="Akses ditolak atau order tidak ditemukan"), 403
    return jsonify({"order": dict(payload["order"]), "items": [dict(row) for row in payload["items"]]})


@app.patch("/api/orders/<int:order_id>")
@login_required
def secure_order_status(order_id):
    user = current_user()
    if user["role"] != "admin":
        return jsonify(error="Hanya admin yang boleh mengubah status"), 403
    data = request.get_json(silent=True) or request.form
    status = data.get("status")
    if status not in {"Processing", "Shipped", "Delivered", "Cancelled"}:
        return jsonify(error="Status tidak valid"), 400
    order = db().execute("SELECT id FROM orders WHERE id=?", (order_id,)).fetchone()
    if not order:
        return jsonify(error="Order tidak ditemukan"), 404
    db().execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    db().commit()
    return jsonify({"updated": True, "order_id": order_id, "status": status})


def admin_required():
    user = current_user()
    if not user:
        return jsonify(error="Silakan login"), 401
    if user["role"] != "admin":
        return jsonify(error="Akses admin diperlukan"), 403
    return None


@app.post("/api/admin/products")
@login_required
def api_create_product():
    denied = admin_required()
    if denied:
        return denied
    data = request.get_json(silent=True) or request.form
    category = db().execute("SELECT id FROM categories WHERE id=?", (data.get("category_id"),)).fetchone()
    if not category:
        return jsonify(error="Kategori tidak valid"), 400
    cursor = db().execute(
        "INSERT INTO products(category_id,name,description,price,stock,image_url) VALUES(?,?,?,?,?,?)",
        (category["id"], data["name"], data.get("description", ""), float(data["price"]), int(data.get("stock", 0)), data.get("image_url", "")),
    )
    db().commit()
    return jsonify({"created": True, "id": cursor.lastrowid}), 201


@app.patch("/api/admin/products/<int:product_id>")
@login_required
def api_update_product(product_id):
    denied = admin_required()
    if denied:
        return denied
    data = request.get_json(silent=True) or request.form
    product = db().execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    if not product:
        return jsonify(error="Produk tidak ditemukan"), 404
    db().execute(
        "UPDATE products SET name=?,description=?,price=?,stock=?,image_url=? WHERE id=?",
        (
            data.get("name", product["name"]),
            data.get("description", product["description"]),
            float(data.get("price", product["price"])),
            int(data.get("stock", product["stock"])),
            data.get("image_url", product["image_url"]),
            product_id,
        ),
    )
    db().commit()
    return jsonify({"updated": True, "id": product_id})


@app.delete("/api/admin/products/<int:product_id>")
@login_required
def api_delete_product(product_id):
    denied = admin_required()
    if denied:
        return denied
    product = db().execute("SELECT id FROM products WHERE id=?", (product_id,)).fetchone()
    if not product:
        return jsonify(error="Produk tidak ditemukan"), 404
    db().execute("DELETE FROM products WHERE id=?", (product_id,))
    db().commit()
    return jsonify({"deleted": True, "id": product_id})


@app.get("/api/admin/users")
@login_required
def api_admin_users():
    denied = admin_required()
    if denied:
        return denied
    rows = db().execute("SELECT id,name,email,role,created_at FROM users ORDER BY id").fetchall()
    return jsonify([dict(row) for row in rows])


@app.get("/admin")
@login_required
def admin():
    if current_user()["role"] != "admin":
        return "Akses admin diperlukan.", 403
    return render_template(
        "admin.html",
        products=db().execute("SELECT p.*, c.name category FROM products p JOIN categories c ON c.id=p.category_id ORDER BY p.id DESC").fetchall(),
        users=db().execute("SELECT id,name,email,role FROM users").fetchall(),
        orders=db().execute("SELECT * FROM orders ORDER BY id DESC LIMIT 20").fetchall(),
        categories=db().execute("SELECT * FROM categories ORDER BY id").fetchall(),
    )


if __name__ == "__main__":
    if not app.config["LAB_MODE"]:
        raise RuntimeError("ShopLab hanya boleh berjalan dalam LAB_MODE.")
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)
