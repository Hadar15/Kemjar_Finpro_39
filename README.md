# ShopLab

ShopLab is a functional local e-commerce lab built with Flask and SQLite. It contains only fictional users and products. It intentionally exposes two vulnerable learning endpoints: SQL Injection and IDOR.

## Isolation

- Binds only to `127.0.0.1:5000`.
- Contains an explicit `LAB_MODE=True` configuration.
- Refuses to run if `LAB_MODE` is disabled.
- Vulnerable routes are under `/api/lab/*`.
- Do not deploy this application to the internet or production.

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

To reset the database:

```powershell
python reset_db.py
```

## Test accounts

| Name | Email | Password | Role |
|---|---|---|---|
| Alice Morgan | alice@shoplab.test | alice123 | customer |
| Bob Carter | bob@shoplab.test | bob123 | customer |
| Charlie Lee | charlie@shoplab.test | charlie123 | customer |
| Lab Admin | admin@shoplab.test | admin123 | admin |

## Database

SQLite file: `shoplab.db`

- `users`: accounts and hashed passwords
- `categories`: product categories
- `products`: catalog and stock
- `carts`: per-user shopping carts
- `cart_items`: cart contents
- `addresses`: shipping addresses
- `orders`: customer orders
- `order_items`: purchased products
- `payments`: simulated payment records

Foreign keys and indexes are enabled. Seeded data includes 5 categories, 20 products, 3 orders per customer, addresses, order items, and payments.

Seeded order IDs:

- Alice: 1001, 1004, 1007
- Bob: 1002, 1005, 1008
- Charlie: 1003, 1006, 1009

## API

| Method | Endpoint | Behavior |
|---|---|---|
| POST | `/api/auth/login` | Secure parameterized login |
| POST | `/api/lab/login` | Vulnerable SQLi login demonstration |
| GET | `/api/products` | Secure product list |
| GET | `/api/products/search?q=...` | Secure parameterized search |
| GET | `/api/lab/products/search?q=...` | Vulnerable SQLi search |
| GET | `/orders` | Current user's order history |
| GET | `/api/orders/:id` | Secure owner-only order detail |
| PATCH | `/api/orders/:id` | Secure admin-only status update |
| GET | `/api/lab/orders/:id` | Vulnerable IDOR order detail |
| PATCH | `/api/lab/orders/:id` | Vulnerable IDOR status update |
| POST | `/api/admin/products` | Admin create product |
| PATCH | `/api/admin/products/:id` | Admin edit product |
| DELETE | `/api/admin/products/:id` | Admin delete product |
| GET | `/api/admin/users` | Admin list users |

## SQL Injection demonstration

Secure search:

```http
GET /api/products/search?q=Lamp
```

The secure route uses `WHERE name LIKE ?` with a bound value.

Vulnerable search:

```http
GET /api/lab/products/search?q=%27%20OR%201=1%20--%20
```

Decoded input:

```text
' OR 1=1 -- 
```

The vulnerable route concatenates input into:

```sql
SELECT id,name,price FROM products
WHERE name LIKE '%<input>%'
LIMIT 50
```

Stacked statements and destructive SQL words are blocked. Only controlled `SELECT` demonstrations are permitted.

For login, log in first if testing sessions, then send:

```http
POST /api/lab/login
Content-Type: application/x-www-form-urlencoded

email=' OR 1=1 -- &password=x
```

This changes the WHERE clause and demonstrates unsafe authentication SQL. Normal secure login uses `/api/auth/login` and password verification with a bcrypt hash.

## IDOR demonstration

1. Login as Alice.
2. Open `/orders` and identify order `1001`.
3. Login as Bob and note order `1002`.
4. As Alice, call:

```http
GET /api/lab/orders/1002
Cookie: <Alice session cookie>
```

Vulnerable result: `200 OK` and Bob's customer/address/product/payment information.

Comparison:

```http
GET /api/orders/1002
Cookie: <Alice session cookie>
```

Secure result: `403` because the query checks both `order.id` and `order.user_id`.

### IDOR update

As Alice, update Bob's order with the lab route:

```http
PATCH /api/lab/orders/1002
Content-Type: application/json

{"status":"Shipped"}
```

The lab route omits ownership checks. This is limited to harmless status values.

Secure status update requires an admin session and is available at `PATCH /api/orders/1002`.
