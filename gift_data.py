import sqlite3

DATABASE = 'gifting.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # 1. Merchants Table (Stores like KFC, Cake Shop, Ice Cream, etc.)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS merchants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            logo_icon TEXT DEFAULT 'bi-shop',
            description TEXT
        )
    ''')

    # 2. Products Table (Items linked to a specific merchant with monetary weight)
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

    # 3. Vouchers Table (Closed-loop digital cards generated upon purchase)
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

    conn.commit()
    conn.close()

def seed_db():
    """Populates initial local merchants and their catalog packages matching the storefront."""
    conn = get_db()
    cursor = conn.cursor()

    # Check if data already exists
    cursor.execute("SELECT COUNT(*) FROM merchants")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    # Seed Merchants (matching your wireframe grid)
    merchants_data = [
        ("KFC Uganda", "Fast Food", "bi-bag-heart-fill", "Crispy chicken, burgers, and family meal combos."),
        ("The Cake Studio", "Cake & Bakery", "bi-cake2-fill", "Custom birthday, graduation, and celebration cakes."),
        ("Planet Ice Cream", "Desserts", "bi-cup-straw", "Scoops, frozen yoghurt, and sweet treat buckets."),
        ("Luigi's Pizza", "Pizza Outlet", "bi-pie-chart-fill", "Wood-fired pizzas and family sharing deals."),
        ("Urban Fashion Hub", "Fashion Boutique", "bi-handbag-fill", "Trending apparel, streetwear, and accessories.")
    ]

    cursor.executemany(
        "INSERT INTO merchants (name, category, logo_icon, description) VALUES (?, ?, ?, ?)",
        merchants_data
    )

    # Seed Products for each merchant
    products_data = [
        # KFC (Merchant ID 1)
        (1, "Streetwise 3 Meal Package", 28000, "3 pieces of chicken, large chips, and 500ml soda.", "kfc_streetwise.jpg"),
        (1, "Zinger Burger Feast", 35000, "Zinger burger, regular chips, wingman, and drink.", "kfc_zinger.jpg"),
        (1, "Mega Family Bucket Voucher", 85000, "9 pieces of crispy chicken, 2 large chips, and 1.25L soda.", "kfc_bucket.jpg"),
        
        # Cake Studio (Merchant ID 2)
        (2, "Bento Birthday Mini Cake (1/2 kg)", 45000, "Cute custom bento cake in chocolate or vanilla.", "cake_bento.jpg"),
        (2, "Deluxe Black Forest Cake (1 kg)", 90000, "Rich chocolate sponge with fresh cherries and cream.", "cake_blackforest.jpg"),
        (2, "Celebration Cupcake Box (6 pcs)", 35000, "Assorted flavored cupcakes with custom icing tags.", "cake_cupcakes.jpg"),

        # Planet Ice Cream (Merchant ID 3)
        (3, "Double Scoop Waffle Cone Voucher", 15000, "Choice of 2 premium flavors with topping in a waffle cone.", "icecream_scoop.jpg"),
        (3, "Family Sundae Dessert Bucket", 40000, "1-liter ice cream tub with hot fudge and sprinkles.", "icecream_bucket.jpg"),

        # Luigi's Pizza (Merchant ID 4)
        (4, "Medium Pizza + 2L Soda Combo", 45000, "Any medium pizza (Pepperoni, Chicken BBQ, or Hawaiian) plus soda.", "pizza_medium.jpg"),
        (4, "Large Stuffed Crust Feast", 65000, "Large stuffed crust pizza with garlic bread and dips.", "pizza_large.jpg"),

        # Urban Fashion (Merchant ID 5)
        (5, "Streetwear Hoodie / Sweatshirt Voucher", 75000, "Redeemable for any branded premium hoodie or sweatshirt.", "fashion_hoodie.jpg"),
        (5, "Custom Jersey / Arsenal Kit Voucher", 60000, "Redeemable for standard club sports jerseys.", "fashion_jersey.jpg")
    ]

    cursor.executemany(
        "INSERT INTO products (merchant_id, title, monetary_value, description, image_url) VALUES (?, ?, ?, ?, ?)",
        products_data
    )

    conn.commit()
    conn.close()
    print("Database tables updated and seeded successfully with marketplace stores!")

if __name__ == '__main__':
    init_db()
    seed_db()