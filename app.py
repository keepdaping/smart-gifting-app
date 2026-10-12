from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import uuid
import sqlite3
import json
from datetime import datetime, timedelta
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)

# Load dataset and prepare TF-IDF on startup
df = pd.read_excel("amazon-products2.xlsx")
df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
df['gift_text'] = df['gift_text'].fillna('')

vectorizer = TfidfVectorizer(stop_words='english')
tfidf_matrix = vectorizer.fit_transform(df['gift_text'])

# Initialize SQLite Database
def init_db():
    conn = sqlite3.connect("gifting.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pending_gifts (
            session_id TEXT PRIMARY KEY,
            product_json TEXT,
            sender_name TEXT,
            recipient_name TEXT,
            personal_message TEXT,
            wrapping_style TEXT,
            scheduled_time TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS active_gifts (
            gift_token TEXT PRIMARY KEY,
            product_title TEXT,
            product_price TEXT,
            product_currency TEXT,
            product_image TEXT,
            product_brand TEXT,
            sender_name TEXT,
            recipient_name TEXT,
            personal_message TEXT,
            wrapping_style TEXT,
            scheduled_time TEXT,
            expires_at TEXT,
            claimed INTEGER,
            expired INTEGER,
            refunded INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Helper to convert pandas row/dict safely
import json

@app.route("/", methods=["GET", "POST"])
def index():
    recommendations = []
    user_query = ""
    
    if request.method == "POST":
        user_query = request.form.get("query", "")
        if user_query.strip():
            query_vector = vectorizer.transform([user_query])
            similarity_scores = cosine_similarity(query_vector, tfidf_matrix).flatten()
            top_indices = similarity_scores.argsort()[::-1][:6]
            
            results = df.iloc[top_indices].copy()
            results['similarity_score'] = similarity_scores[top_indices]
            results['product_id'] = top_indices
            
            recommendations = results.to_dict(orient="records")

    return render_template("index.html", recommendations=recommendations, user_query=user_query)


@app.route("/select/<int:product_id>", methods=["GET", "POST"])
def select_gift(product_id):
    product = df.iloc[product_id]
    
    if request.method == "POST":
        session_id = str(uuid.uuid4())[:8]
        product_dict = product.to_dict()
        
        conn = sqlite3.connect("gifting.db")
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO pending_gifts (session_id, product_json, sender_name, recipient_name, personal_message, wrapping_style, scheduled_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id,
            json.dumps(product_dict),
            request.form.get("sender_name"),
            request.form.get("recipient_name"),
            request.form.get("personal_message"),
            request.form.get("wrapping_style"),
            request.form.get("scheduled_time")
        ))
        conn.commit()
        conn.close()
        
        return redirect(url_for('checkout', session_id=session_id))

    return render_template("personalize.html", product=product, product_id=product_id)


@app.route("/checkout/<session_id>", methods=["GET", "POST"])
def checkout(session_id):
    conn = sqlite3.connect("gifting.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM pending_gifts WHERE session_id = ?", (session_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return redirect(url_for('index'))
        
    gift_data = {
        "product": json.loads(row["product_json"]),
        "sender_name": row["sender_name"],
        "recipient_name": row["recipient_name"],
        "personal_message": row["personal_message"],
        "wrapping_style": row["wrapping_style"],
        "scheduled_time": row["scheduled_time"]
    }
        
    if request.method == "POST":
        gift_token = str(uuid.uuid4())[:8]
        # Set expiration time (change timedelta here if you want fast testing)
        expires_at = datetime.now() + timedelta(hours=24)
        
        prod = gift_data["product"]
        cursor.execute('''
            INSERT INTO active_gifts (gift_token, product_title, product_price, product_currency, product_image, product_brand, sender_name, recipient_name, personal_message, wrapping_style, scheduled_time, expires_at, claimed, expired, refunded)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0)
        ''', (
            gift_token,
            prod.get("title"),
            str(prod.get("final_price")),
            prod.get("currency", "$"),
            str(prod.get("image_url")),
            prod.get("brand"),
            gift_data["sender_name"],
            gift_data["recipient_name"],
            gift_data["personal_message"],
            gift_data["wrapping_style"],
            gift_data["scheduled_time"],
            expires_at.strftime("%Y-%m-%d %H:%M:%S")
        ))
        
        # Clean up pending
        cursor.execute("DELETE FROM pending_gifts WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()
        
        return redirect(url_for('success_page', gift_token=gift_token))

    conn.close()
    return render_template("checkout.html", gift=gift_data, session_id=session_id)


@app.route("/success/<gift_token>")
def success_page(gift_token):
    conn = sqlite3.connect("gifting.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM active_gifts WHERE gift_token = ?", (gift_token,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return "Gift not found!", 404
        
    gift = {
        "sender_name": row["sender_name"],
        "recipient_name": row["recipient_name"],
        "product": {
            "title": row["product_title"],
            "final_price": row["product_price"],
            "currency": row["product_currency"],
            "image_url": row["product_image"],
            "brand": row["product_brand"]
        }
    }
    return render_template("success.html", gift=gift, gift_token=gift_token)


@app.route("/gift/<gift_token>")
def open_gift(gift_token):
    conn = sqlite3.connect("gifting.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM active_gifts WHERE gift_token = ?", (gift_token,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return render_template("error.html", message="This gift link is invalid or has expired."), 404
        
    if row["claimed"]:
        conn.close()
        return render_template("error.html", message="This gift has already been claimed!")

    # Check if expired
    expires_str = row["expires_at"]
    if expires_str:
        try:
            expires_dt = datetime.strptime(expires_str, "%Y-%m-%d %H:%M:%S")
            if datetime.now() > expires_dt:
                cursor.execute("UPDATE active_gifts SET expired = 1, refunded = 1 WHERE gift_token = ?", (gift_token,))
                conn.commit()
                conn.close()
                return render_template("error.html", message="This gift link has expired. A mock refund has been automatically initiated to the sender.")
        except ValueError:
            pass

    # Check scheduled unlock
    is_locked = False
    scheduled_str = row["scheduled_time"]
    if scheduled_str:
        try:
            scheduled_dt = datetime.strptime(scheduled_str, "%Y-%m-%dT%H:%M")
            if datetime.now() < scheduled_dt:
                is_locked = True
        except ValueError:
            pass
            
    gift = {
        "sender_name": row["sender_name"],
        "recipient_name": row["recipient_name"],
        "personal_message": row["personal_message"],
        "wrapping_style": row["wrapping_style"],
        "product": {
            "title": row["product_title"],
            "final_price": row["product_price"],
            "currency": row["product_currency"],
            "image_url": row["product_image"],
            "brand": row["product_brand"]
        }
    }
    conn.close()
    return render_template("open_gift.html", gift=gift, gift_token=gift_token, is_locked=is_locked, scheduled_time=scheduled_str)


@app.route("/claim/<gift_token>", methods=["POST"])
def claim_gift(gift_token):
    conn = sqlite3.connect("gifting.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM active_gifts WHERE gift_token = ?", (gift_token,))
    row = cursor.fetchone()
    
    if row:
        cursor.execute("UPDATE active_gifts SET claimed = 1 WHERE gift_token = ?", (gift_token,))
        conn.commit()
        
    gift = {
        "recipient_name": row["recipient_name"] if row else "Recipient",
        "sender_name": row["sender_name"] if row else "Sender"
    }
    conn.close()
    return render_template("claimed.html", gift=gift)

@app.route("/ussd", methods=["GET", "POST"])
def ussd_simulation():
    response_text = ""
    step = request.form.get("step", "home")
    user_input = request.form.get("user_input", "").strip()
    
    if step == "home":
        if user_input == "*123#":
            response_text = "Welcome to Smart Gifting (USSD)\n1. Check My Gifts\n2. Help"
            next_step = "menu"
        else:
            response_text = "Please dial *123# to start."
            next_step = "home"
    elif step == "menu":
        if user_input == "1":
            # Fetch active gifts from SQLite
            conn = sqlite3.connect("gifting.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM active_gifts WHERE claimed = 0 LIMIT 3")
            gifts = cursor.fetchall()
            conn.close()
            
            if not gifts:
                response_text = "You have no pending gifts.\n0. Back"
                next_step = "home"
            else:
                response_text = "Select a gift to claim:\n"
                for idx, g in enumerate(gifts, 1):
                    response_text += f"{idx}. {g['product_title'][:20]}... from {g['sender_name']}\n"
                response_text += "0. Back"
                next_step = "claim_menu"
        else:
            response_text = "Invalid choice.\n1. Check My Gifts\n0. Exit"
            next_step = "home"
    else:
        response_text = "Session ended. Dial *123# to restart."
        next_step = "home"
        
    return render_template("ussd.html", response_text=response_text, step=next_step)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)