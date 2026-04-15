# Splitsy — Web App (Demo v1.0)
**Split the haul. Share the savings.**

A Flask web app for demoing the Splitsy concept to investors.
Built for Atlanta, GA · 2026

---

## Setup & Run (takes about 2 minutes)

### Step 1 — Install Flask
Open your Terminal and run:
```
pip install flask
```

### Step 2 — Navigate to this folder
In your Terminal, cd into the splitsy folder:
```
cd path/to/splitsy
```
(Replace `path/to/splitsy` with the actual path where you saved the folder.)

### Step 3 — Run the app
```
python app.py
```
You should see:
```
🟢  Splitsy is running!
   Open your browser and go to: http://localhost:5000
```

### Step 4 — Open in your browser
Go to: **http://localhost:5000**

---

## What's included in the demo

| Page | URL | What it shows |
|------|-----|---------------|
| Browse listings | `/` | 8 pre-loaded seed listings with filters |
| Listing detail | `/listing/<id>` | Full listing info + claim flow |
| Claim a portion | (form on detail page) | Simulated payment + confirmation |
| Confirmation | `/confirmation/<id>` | Post-claim details + simulated rating |
| List a split | `/sell` | Full seller listing form |
| How it works | `/how-it-works` | Explainer page for investors |

## Notes for investors / demo
- Payments are **simulated** — no real money moves. A note on screen explains this.
- Stripe integration is architected and ready to plug in.
- New listings created during the demo session are stored in memory (reset on server restart).
- The product catalog has 386 items mapped and categorized — see `Splitsy_Product_Catalog_v2.xlsx`.

## Tech stack
- **Backend:** Python / Flask
- **Frontend:** Jinja2 templates, vanilla CSS, minimal JS
- **Payments (production):** Stripe (not yet wired in)
- **Maps (production):** Google Maps API (placeholder in demo)
- **Database (production):** PostgreSQL or SQLite (in-memory for demo)

## Next steps after demo
1. Add a real database (SQLite for local dev, PostgreSQL for production)
2. Wire in Stripe for real payments
3. Add user authentication (login/signup)
4. Build receipt photo upload + OCR for markup cap enforcement
5. Add push/SMS notifications
6. Deploy to a server (Render, Railway, or Heroku are easiest for Flask)
