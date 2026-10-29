from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import random
import string

app = Flask(__name__)
app.secret_key = 'smart_gifting_secret_key'

DATABASE = 'gifting.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def unsplash_image(photo_id):
    """Build a consistent high-resolution Unsplash URL for seeded catalogue images."""
    return f"https://images.unsplash.com/{photo_id}?auto=format&fit=crop&w=1200&q=85"


def init_db():
    """Create the gift-voucher schema and add image support to existing catalogues."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS merchants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            image_url TEXT,
            description TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            merchant_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            monetary_value INTEGER NOT NULL,
            description TEXT,
            image_url TEXT,
            FOREIGN KEY (merchant_id) REFERENCES merchants (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vouchers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voucher_code TEXT UNIQUE NOT NULL,
            merchant_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            sender_name TEXT NOT NULL,
            recipient_phone TEXT NOT NULL,
            message TEXT,
            monetary_value INTEGER NOT NULL,
            status TEXT DEFAULT 'ACTIVE',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (merchant_id) REFERENCES merchants (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')

    for table_name in ("merchants", "products"):
        columns = {column["name"] for column in cursor.execute(f"PRAGMA table_info({table_name})")}
        if "image_url" not in columns:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN image_url TEXT")

    conn.commit()
    conn.close()


def seed_db():
    """Insert or refresh all partner stores and products without duplicating seed rows."""
    conn = get_db()
    cursor = conn.cursor()
    merchants_data = [
        ("KFC Uganda", "Fast Food", "photo-1561758033-d89a9ad46330", "Crispy chicken, burgers, and family meal combos."),
        ("The Cake Studio", "Cake & Bakery", "photo-1509440159596-0249088772ff", "Custom birthday, graduation, and celebration cakes."),
        ("Planet Ice Cream", "Desserts", "photo-1560008511-11c63416e52d", "Scoops, frozen yoghurt, and sweet treat buckets."),
        ("Luigi's Pizza", "Pizza Outlet", "photo-1513104890138-7c749659a591", "Wood-fired pizzas and family sharing deals."),
        ("Urban Fashion Hub", "Fashion Boutique", "photo-1441986300917-64674bd600d8", "Trending apparel, streetwear, and accessories."),
    ]
    products_data = [
        ("KFC Uganda", "Streetwise 3 Meal Package", 28000, "3 pieces of crispy chicken, large chips, and 500ml soda.", "photo-1626082927389-6cd097cdc6ec"),
        ("KFC Uganda", "Zinger Burger Feast", 35000, "Zinger burger, regular chips, wingman, and drink.", "photo-1568901346375-23c9450c58cd"),
        ("KFC Uganda", "Mega Family Bucket Voucher", 85000, "9 pieces of crispy chicken, 2 large chips, and 1.25L soda.", "photo-1626082927389-6cd097cdc6ec"),
        ("The Cake Studio", "Bento Birthday Mini Cake (1/2 kg)", 45000, "Cute custom bento cake in chocolate or vanilla.", "photo-1578985545062-69928b1d9587"),
        ("The Cake Studio", "Deluxe Black Forest Cake (1 kg)", 90000, "Rich chocolate sponge with fresh cherries and cream.", "photo-1606313564200-e75d5e30476c"),
        ("The Cake Studio", "Celebration Cupcake Box (6 pcs)", 35000, "Assorted flavored cupcakes with custom icing tags.", "photo-1576618148400-f54bed99fcfd"),
        ("Planet Ice Cream", "Double Scoop Waffle Cone Voucher", 15000, "Choice of 2 premium flavors with topping in a waffle cone.", "photo-1560008511-11c63416e52d"),
        ("Planet Ice Cream", "Family Sundae Dessert Bucket", 40000, "1-liter ice cream tub with hot fudge and sprinkles.", "photo-1563805042-7684c019e1cb"),
        ("Luigi's Pizza", "Medium Pizza + 2L Soda Combo", 45000, "Any medium pizza (Pepperoni, Chicken BBQ, or Hawaiian) plus soda.", "photo-1513104890138-7c749659a591"),
        ("Luigi's Pizza", "Large Stuffed Crust Feast", 65000, "Large stuffed crust pizza with garlic bread and dips.", "photo-1574071318508-1cdbab80d002"),
        ("Urban Fashion Hub", "Streetwear Hoodie / Sweatshirt Voucher", 75000, "Redeemable for any branded premium hoodie or sweatshirt.", "photo-1556905055-8f358a7a47b2"),
        ("Urban Fashion Hub", "Custom Jersey / Arsenal Kit Voucher", 60000, "Redeemable for standard club sports jerseys.", "photo-1589487391730-58f20eb2c308"),
    ]

    try:
        merchant_ids = {}
        for name, category, photo_id, description in merchants_data:
            image_url = unsplash_image(photo_id)
            merchant = cursor.execute(
                "SELECT id FROM merchants WHERE name = ?",
                (name,),
            ).fetchone()
            if merchant:
                merchant_id = merchant["id"]
                cursor.execute(
                    "UPDATE merchants SET category = ?, image_url = ?, description = ? WHERE id = ?",
                    (category, image_url, description, merchant_id),
                )
            else:
                cursor.execute(
                    "INSERT INTO merchants (name, category, image_url, description) VALUES (?, ?, ?, ?)",
                    (name, category, image_url, description),
                )
                merchant_id = cursor.lastrowid
            merchant_ids[name] = merchant_id

        for merchant_name, title, value, description, photo_id in products_data:
            merchant_id = merchant_ids[merchant_name]
            image_url = unsplash_image(photo_id)
            product = cursor.execute(
                "SELECT id FROM products WHERE merchant_id = ? AND title = ?",
                (merchant_id, title),
            ).fetchone()
            if product:
                cursor.execute(
                    "UPDATE products SET monetary_value = ?, description = ?, image_url = ? WHERE id = ?",
                    (value, description, image_url, product["id"]),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO products (merchant_id, title, monetary_value, description, image_url)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (merchant_id, title, value, description, image_url),
                )

        conn.commit()
    finally:
        conn.close()

def generate_voucher_code():
    """Generates a unique redemption code like GIFT-ABC1234"""
    chars = string.ascii_uppercase + string.digits
    code = ''.join(random.choice(chars) for _ in range(6))
    return f"GIFT-{code}"

@app.route('/')
def index():
    """Renders the main store image grid homepage."""
    conn = get_db()
    merchants = conn.execute("SELECT * FROM merchants").fetchall()
    conn.close()
    return render_template('index.html', merchants=merchants)

@app.route('/store/<int:merchant_id>')
def store_catalog(merchant_id):
    """Displays item packages inside a clicked store."""
    conn = get_db()
    merchant = conn.execute("SELECT * FROM merchants WHERE id = ?", (merchant_id,)).fetchone()
    products = conn.execute("SELECT * FROM products WHERE merchant_id = ?", (merchant_id,)).fetchall()
    conn.close()
    
    if not merchant:
        flash("Store not found.", "danger")
        return redirect(url_for('index'))
        
    return render_template('store.html', merchant=merchant, products=products)

@app.route('/buy/<int:product_id>', methods=['GET', 'POST'])
def buy_gift(product_id):
    """Handles gift purchase details and creates the secure voucher."""
    conn = get_db()
    product = conn.execute(
        "SELECT products.*, merchants.name as merchant_name FROM products JOIN merchants ON products.merchant_id = merchants.id WHERE products.id = ?",
        (product_id,)
    ).fetchone()
    
    if request.method == 'POST':
        sender_name = request.form['sender_name']
        recipient_phone = request.form['recipient_phone']
        message = request.form['message']
        
        voucher_code = generate_voucher_code()
        
        conn.execute('''
            INSERT INTO vouchers (voucher_code, merchant_id, product_id, sender_name, recipient_phone, message, monetary_value)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (voucher_code, product['merchant_id'], product['id'], sender_name, recipient_phone, message, product['monetary_value']))
        conn.commit()
        conn.close()
        
        flash(f"Gift successfully purchased! Voucher Code: {voucher_code}", "success")
        return redirect(url_for('view_voucher', voucher_code=voucher_code))
        
    conn.close()
    return render_template('buy.html', product=product)

@app.route('/voucher/<voucher_code>')
def view_voucher(voucher_code):
    """Displays the recipient's digital gift card."""
    conn = get_db()
    voucher = conn.execute('''
        SELECT vouchers.*, merchants.name as merchant_name, products.title as product_title, products.description as product_desc
        FROM vouchers
        JOIN merchants ON vouchers.merchant_id = merchants.id
        JOIN products ON vouchers.product_id = products.id
        WHERE vouchers.voucher_code = ?
    ''', (voucher_code,)).fetchone()
    conn.close()
    
    if not voucher:
        flash("Invalid voucher code.", "danger")
        return redirect(url_for('index'))
        
    return render_template('voucher.html', voucher=voucher)

@app.route('/merchant/verify', methods=['GET', 'POST'])
def merchant_verify():
    """Cashier verification portal to prevent fraud and mark vouchers USED."""
    voucher = None
    if request.method == 'POST':
        code = request.form['voucher_code'].strip().upper()
        action = request.form.get('action')
        
        conn = get_db()
        voucher = conn.execute('''
            SELECT vouchers.*, merchants.name as merchant_name, products.title as product_title
            FROM vouchers
            JOIN merchants ON vouchers.merchant_id = merchants.id
            JOIN products ON vouchers.product_id = products.id
            WHERE vouchers.voucher_code = ?
        ''', (code,)).fetchone()
        
        if voucher:
            if action == 'redeem' and voucher['status'] == 'ACTIVE':
                conn.execute("UPDATE vouchers SET status = 'USED' WHERE voucher_code = ?", (code,))
                conn.commit()
                flash(f"Voucher {code} successfully marked as REDEEMED!", "success")
                voucher = conn.execute('''
                    SELECT vouchers.*, merchants.name as merchant_name, products.title as product_title
                    FROM vouchers
                    JOIN merchants ON vouchers.merchant_id = merchants.id
                    JOIN products ON vouchers.product_id = products.id
                    WHERE vouchers.voucher_code = ?
                ''', (code,)).fetchone()
        else:
            flash("Voucher code not found in the system.", "danger")
        conn.close()
        
    return render_template('verify.html', voucher=voucher)

if __name__ == '__main__':
    init_db()
    seed_db()
    app.run(debug=True, port=5000)