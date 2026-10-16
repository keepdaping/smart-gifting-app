# Smart Gifting App

A Flask-based digital gifting application that recommends products, lets a sender create a timed gift, and allows a recipient to unlock and claim it.

## Features

- AI-style product recommendation using TF-IDF similarity on the product catalogue.
- Gift personalization with sender, recipient, message, wrapping style, and scheduled unlock time.
- SQLite-backed gift lifecycle tracking for pending, active, claimed, expired, and refunded gifts.
- USSD-style menu flow for lightweight gift interaction.

## Project structure

- `app.py` — Flask routes and application entry point.
- `gift_data.py` — product catalogue loading and recommendation logic.
- `gift_store.py` — SQLite helpers for the gift lifecycle.
- `recommend.py` — example recommendation script.
- `inspect_data.py` — dataset inspection utility.
- `templates/` — HTML templates for the UI.
- `gifting.db` — local SQLite database file created at runtime.
- `amazon-products2.xlsx` — product data source.

## Setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the app:
   ```bash
   python app.py
   ```

## Run the app

Use the Flask development server locally:

```bash
python app.py
```

The app listens on `http://127.0.0.1:5000` by default.

## Environment variables

- `GIFT_DATASET_PATH` — override the Excel file used for recommendations.
- `GIFT_DB_PATH` — override the SQLite database path used by the app.

## Deployment

The project includes a `Procfile` configured for Gunicorn:

```bash
web: gunicorn app:app
```
