"""Flask application for the smart gifting workflow."""

from __future__ import annotations

import json
from datetime import datetime

from flask import Flask, redirect, render_template, request, url_for

from gift_data import build_recommendation_model, load_product_catalog
from gift_store import (
    delete_pending_gift,
    fetch_active_gift,
    fetch_active_gifts_for_ussd,
    fetch_pending_gift,
    init_database,
    mark_gift_claimed,
    mark_gift_expired,
    save_active_gift,
    save_pending_gift,
)
from recommend import recommend_gifts

app = Flask(__name__)

PRODUCT_DATA = load_product_catalog()
VECTORIZER, TFIDF_MATRIX = build_recommendation_model(PRODUCT_DATA)

init_database()


def build_gift_payload(product_row):
    """Convert a product row to the JSON payload stored in the pending gift table."""
    return product_row.to_dict()


def is_gift_locked(scheduled_time: str | None) -> bool:
    """Return whether the gift is still blocked by its scheduled unlock time."""
    if not scheduled_time:
        return False

    try:
        scheduled_dt = datetime.strptime(scheduled_time, "%Y-%m-%dT%H:%M")
        return datetime.now() < scheduled_dt
    except ValueError:
        return False


@app.route("/", methods=["GET", "POST"])
def index():
    """Render the homepage and recommendation search panel."""
    recommendations = []
    user_query = ""

    if request.method == "POST":
        user_query = request.form.get("query", "")
        recommendations = recommend_gifts(
            user_query,
            PRODUCT_DATA,
            VECTORIZER,
            TFIDF_MATRIX,
            top_n=6,
        )

    return render_template("index.html", recommendations=recommendations, user_query=user_query)


@app.route("/select/<int:product_id>", methods=["GET", "POST"])
def select_gift(product_id):
    """Capture the sender's gift details for a selected recommendation."""
    product = PRODUCT_DATA.iloc[product_id]

    if request.method == "POST":
        session_id = save_pending_gift(
            build_gift_payload(product),
            {
                "sender_name": request.form.get("sender_name"),
                "recipient_name": request.form.get("recipient_name"),
                "personal_message": request.form.get("personal_message"),
                "wrapping_style": request.form.get("wrapping_style"),
                "scheduled_time": request.form.get("scheduled_time"),
            },
        )
        return redirect(url_for("checkout", session_id=session_id))

    return render_template("personalize.html", product=product, product_id=product_id)


@app.route("/checkout/<session_id>", methods=["GET", "POST"])
def checkout(session_id):
    """Show the final checkout summary and finalize the gift creation."""
    row = fetch_pending_gift(session_id)
    if not row:
        return redirect(url_for("index"))

    gift_data = {
        "product": json.loads(row["product_json"]),
        "sender_name": row["sender_name"],
        "recipient_name": row["recipient_name"],
        "personal_message": row["personal_message"],
        "wrapping_style": row["wrapping_style"],
        "scheduled_time": row["scheduled_time"],
    }

    if request.method == "POST":
        gift_token = save_active_gift(gift_data)
        delete_pending_gift(session_id)
        return redirect(url_for("success_page", gift_token=gift_token))

    return render_template("checkout.html", gift=gift_data, session_id=session_id)


@app.route("/success/<gift_token>")
def success_page(gift_token):
    """Render the post-checkout success screen for the sender."""
    row = fetch_active_gift(gift_token)
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
            "brand": row["product_brand"],
        },
    }
    return render_template("success.html", gift=gift, gift_token=gift_token)


@app.route("/gift/<gift_token>")
def open_gift(gift_token):
    """Display the actual gift presentation and claim screen."""
    row = fetch_active_gift(gift_token)
    if not row:
        return render_template("error.html", message="This gift link is invalid or has expired."), 404

    if row["claimed"]:
        return render_template("error.html", message="This gift has already been claimed!")

    expires_str = row["expires_at"]
    if expires_str:
        try:
            expires_dt = datetime.strptime(expires_str, "%Y-%m-%d %H:%M:%S")
            if datetime.now() > expires_dt:
                mark_gift_expired(gift_token)
                return render_template(
                    "error.html",
                    message="This gift link has expired. A mock refund has been automatically initiated to the sender.",
                )
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
            "brand": row["product_brand"],
        },
    }
    return render_template(
        "open_gift.html",
        gift=gift,
        gift_token=gift_token,
        is_locked=is_gift_locked(row["scheduled_time"]),
        scheduled_time=row["scheduled_time"],
    )


@app.route("/claim/<gift_token>", methods=["POST"])
def claim_gift(gift_token):
    """Finalize the recipient's claim for a gift."""
    row = fetch_active_gift(gift_token)
    if row:
        mark_gift_claimed(gift_token)

    gift = {
        "recipient_name": row["recipient_name"] if row else "Recipient",
        "sender_name": row["sender_name"] if row else "Sender",
    }
    return render_template("claimed.html", gift=gift)


@app.route("/ussd", methods=["GET", "POST"])
def ussd_simulation():
    """Provide a minimal USSD-style gift lookup experience."""
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
            gifts = fetch_active_gifts_for_ussd()
            if not gifts:
                response_text = "You have no pending gifts.\n0. Back"
                next_step = "home"
            else:
                response_text = "Select a gift to claim:\n"
                for idx, gift in enumerate(gifts, 1):
                    response_text += f"{idx}. {gift['product_title'][:20]}... from {gift['sender_name']}\n"
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
    app.run(host="0.0.0.0", port=5000, debug=True)
