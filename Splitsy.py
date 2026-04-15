from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, g
import sqlite3, uuid, hashlib, os
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = "splitsy-v2-secret-key-2026"

DATABASE = os.path.join(os.path.dirname(__file__), "splitsy.db")

# ---------------------------------------------------------------------------
# DATABASE SETUP
# ---------------------------------------------------------------------------

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        db.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                neighborhood TEXT,
                address TEXT,
                is_founding_member INTEGER DEFAULT 1,
                rating REAL DEFAULT 5.0,
                review_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS communities (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                lat REAL NOT NULL,
                lng REAL NOT NULL,
                address TEXT,
                created_by TEXT,
                member_count INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS community_members (
                user_id TEXT,
                community_id TEXT,
                joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, community_id)
            );

            CREATE TABLE IF NOT EXISTS listings (
                id TEXT PRIMARY KEY,
                seller_id TEXT NOT NULL,
                item TEXT NOT NULL,
                category TEXT,
                bulk_store TEXT,
                total_qty TEXT,
                portion_size TEXT,
                portions_total INTEGER,
                portions_claimed INTEGER DEFAULT 0,
                price_per_portion REAL,
                retail_price REAL,
                pickup_window TEXT,
                meetup_spot TEXT,
                community_id TEXT,
                verified INTEGER DEFAULT 0,
                model TEXT DEFAULT 'pioneer',
                emoji TEXT DEFAULT '📦',
                image_url TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS claims (
                id TEXT PRIMARY KEY,
                listing_id TEXT NOT NULL,
                buyer_id TEXT NOT NULL,
                amount REAL,
                status TEXT DEFAULT 'pending',
                rated_seller INTEGER DEFAULT 0,
                seller_rating INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        db.commit()
        _seed_data(db)

def _seed_data(db):
    # Only seed if no communities exist yet
    existing = db.execute("SELECT COUNT(*) as c FROM communities").fetchone()
    if existing['c'] > 0:
        return

    # Seed communities — hyper-local Atlanta spots
    communities = [
        ("com001", "The Beltline Collective", "For folks along the Eastside Trail corridor", 33.7678, -84.3733, "Eastside Trail, Atlanta, GA"),
        ("com002", "Ponce City Market Neighbors", "Midtown residents near PCM", 33.7721, -84.3659, "675 Ponce de Leon Ave NE, Atlanta, GA"),
        ("com003", "Old Fourth Ward Community", "O4W neighborhood residents", 33.7587, -84.3648, "Old Fourth Ward, Atlanta, GA"),
        ("com004", "EAV Collective", "East Atlanta Village locals", 33.7268, -84.3413, "East Atlanta Village, Atlanta, GA"),
        ("com005", "Inman Park Neighbors", "Inman Park & Candler Park area", 33.7579, -84.3527, "Inman Park, Atlanta, GA"),
        ("com006", "Grant Park Group", "Grant Park & Zoo Atlanta area", 33.7335, -84.3701, "Grant Park, Atlanta, GA"),
        ("com007", "Virginia-Highland Hub", "Va-Hi residents", 33.7808, -84.3557, "Virginia-Highland, Atlanta, GA"),
        ("com008", "West Midtown Collective", "West Midtown & Westside residents", 33.7820, -84.4108, "West Midtown, Atlanta, GA"),
        ("com009", "Kirkwood Neighbors", "Kirkwood & Edgewood community", 33.7456, -84.3390, "Kirkwood, Atlanta, GA"),
        ("com010", "Reynoldstown Block", "Reynoldstown residents near the Beltline", 33.7511, -84.3572, "Reynoldstown, Atlanta, GA"),
    ]
    for c in communities:
        db.execute("INSERT OR IGNORE INTO communities (id,name,description,lat,lng,address) VALUES (?,?,?,?,?,?)", c)

    # Seed demo user
    pw_hash = hashlib.sha256("demo123".encode()).hexdigest()
    db.execute("INSERT OR IGNORE INTO users (id,name,email,password_hash,neighborhood) VALUES (?,?,?,?,?)",
               ("user_demo","Marcus T.","demo@splitsy.com", pw_hash, "Old Fourth Ward"))

    # Seed listings with Unsplash image URLs (real product-style photos)
    listings = [
        ("l001","user_demo","Extra Virgin Olive Oil","Pantry & Food","Costco","2-pack of 2L bottles","1 bottle (2L)",2,1,7.50,10.99,"Sat Jan 18, 10am–2pm","Ponce City Market Lobby","com002",1,"pioneer","🫒","https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=600&q=80"),
        ("l002","user_demo","Sparkling Water (LaCroix)","Pantry & Food","Costco","32-can variety pack","8 cans",4,2,3.25,5.99,"Sun Jan 19, 11am–3pm","East Atlanta Village MARTA Station","com004",1,"pioneer","💧","https://images.unsplash.com/photo-1559839734-2b71ea197ec3?w=600&q=80"),
        ("l003","user_demo","Protein Bars (RXBar)","Pantry & Food","Costco","30-bar box","5 bars",6,1,4.16,6.99,"Sat Jan 18, 2pm–5pm","Piedmont Park — 10th St Gate","com002",1,"pioneer","💪","https://images.unsplash.com/photo-1622484212850-eb596d769edc?w=600&q=80"),
        ("l004","user_demo","Paper Towels (Bounty)","Household Essentials","Costco","12-roll pack","3 rolls",4,0,4.99,7.99,"Mon Jan 20, 6pm–8pm","Inman Park MARTA Station","com005",1,"pioneer","🧻","https://images.unsplash.com/photo-1584305574647-0cc949a2bb9f?w=600&q=80"),
        ("l005","user_demo","Dish Soap (Dawn)","Household Essentials","Sam's Club","3-pack","1 bottle",3,0,4.66,5.99,"Fri Jan 24, 5pm–7pm","Old Fourth Ward — Irwin St Park","com003",1,"pioneer","🧴","https://images.unsplash.com/photo-1563453392212-326f5e854473?w=600&q=80"),
        ("l006","user_demo","Energy Drinks (Red Bull)","Pantry & Food","Costco","24-pack","6 cans",4,3,7.49,11.94,"Already completed","Krog Street Market Entrance","com001",1,"pioneer","⚡","https://images.unsplash.com/photo-1622543925917-763c34d1a86e?w=600&q=80"),
        ("l007","user_demo","Shampoo (OGX)","Health & Personal Care","Costco","3-pack","1 bottle",3,1,5.66,7.99,"Sun Jan 19, 3pm–6pm","Grant Park — Entrance on Cherokee Ave","com006",0,"pioneer","🧴","https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=600&q=80"),
        ("l008","user_demo","Disinfecting Wipes (Lysol)","Household Essentials","Sam's Club","5-tub pack","1 tub",5,0,3.79,5.49,"Wed Jan 22, 5pm–7pm","Virginia-Highland — N Highland & Virginia Ave","com007",1,"pool","🧽","https://images.unsplash.com/photo-1585771724684-38269d6639fd?w=600&q=80"),
        ("l009","user_demo","Toothpaste (Colgate 4-pack)","Health & Personal Care","Sam's Club","4-pack","1 tube",4,1,3.74,4.99,"Thu Jan 23, 4pm–6pm","Beltline — Irwin St Access","com001",1,"pioneer","🦷","https://images.unsplash.com/photo-1559590196-f9b8a0a9d2c5?w=600&q=80"),
        ("l010","user_demo","AA Batteries (Duracell)","Household Essentials","Costco","48-pack","8-pack",6,2,3.33,5.49,"Sat Jan 18, 1pm–4pm","Reynoldstown — Flat Shoals Ave","com010",1,"pioneer","🔋","https://images.unsplash.com/photo-1619642751034-765dfdf7c58e?w=600&q=80"),
    ]
    for l in listings:
        db.execute("""INSERT OR IGNORE INTO listings
            (id,seller_id,item,category,bulk_store,total_qty,portion_size,portions_total,
             portions_claimed,price_per_portion,retail_price,pickup_window,meetup_spot,
             community_id,verified,model,emoji,image_url)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", l)
    db.commit()

# ---------------------------------------------------------------------------
# AUTH HELPERS
# ---------------------------------------------------------------------------

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated

def get_current_user():
    if 'user_id' not in session:
        return None
    db = get_db()
    return db.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()

# ---------------------------------------------------------------------------
# ROUTES — AUTH
# ---------------------------------------------------------------------------

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and user['password_hash'] == hash_password(password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            flash(f"Welcome back, {user['name']}! 👋", "success")
            return redirect(request.args.get('next') or url_for('index'))
        flash("Invalid email or password.", "error")
    return render_template("login.html")

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        neighborhood = request.form.get("neighborhood","").strip()
        if not all([name, email, password]):
            flash("Please fill in all required fields.", "error")
            return render_template("signup.html")
        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if existing:
            flash("An account with that email already exists.", "error")
            return render_template("signup.html")
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        db.execute("INSERT INTO users (id,name,email,password_hash,neighborhood) VALUES (?,?,?,?,?)",
                   (user_id, name, email, hash_password(password), neighborhood))
        db.commit()
        session['user_id'] = user_id
        session['user_name'] = name
        flash(f"Welcome to Splitsy, {name}! You're a Founding Member. 🎉", "success")
        return redirect(url_for('index'))
    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You've been logged out.", "success")
    return redirect(url_for('index'))

# ---------------------------------------------------------------------------
# ROUTES — MAIN
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    db = get_db()
    community_id = request.args.get("community", "all")
    category = request.args.get("category", "all")

    query = "SELECT l.*, u.name as seller_name, u.rating as seller_rating, u.review_count, c.name as community_name FROM listings l JOIN users u ON l.seller_id=u.id LEFT JOIN communities c ON l.community_id=c.id WHERE l.status='active'"
    params = []
    if community_id != "all":
        query += " AND l.community_id=?"
        params.append(community_id)
    if category != "all":
        query += " AND l.category=?"
        params.append(category)
    query += " ORDER BY l.created_at DESC"

    listings = db.execute(query, params).fetchall()
    communities = db.execute("SELECT * FROM communities ORDER BY name").fetchall()
    categories = ["Pantry & Food", "Household Essentials", "Health & Personal Care", "Pet Supplies", "Baby & Kids"]

    return render_template("index.html",
        listings=listings,
        communities=communities,
        categories=categories,
        selected_community=community_id,
        selected_category=category,
        current_user=get_current_user()
    )

@app.route("/listing/<listing_id>")
def listing_detail(listing_id):
    db = get_db()
    listing = db.execute("""
        SELECT l.*, u.name as seller_name, u.rating as seller_rating, u.review_count, u.is_founding_member,
               c.name as community_name
        FROM listings l JOIN users u ON l.seller_id=u.id
        LEFT JOIN communities c ON l.community_id=c.id
        WHERE l.id=?
    """, (listing_id,)).fetchone()
    if not listing:
        flash("Listing not found.", "error")
        return redirect(url_for('index'))
    portions_left = listing['portions_total'] - listing['portions_claimed']
    savings = (listing['retail_price'] or 0) - listing['price_per_portion']
    savings_pct = round((savings / listing['retail_price']) * 100) if listing['retail_price'] else 0
    return render_template("listing_detail.html", listing=listing, portions_left=portions_left,
                           savings=savings, savings_pct=savings_pct, current_user=get_current_user())

@app.route("/claim/<listing_id>", methods=["POST"])
@login_required
def claim(listing_id):
    db = get_db()
    listing = db.execute("SELECT * FROM listings WHERE id=?", (listing_id,)).fetchone()
    if not listing:
        flash("Listing not found.", "error")
        return redirect(url_for('index'))
    if listing['portions_claimed'] >= listing['portions_total']:
        flash("Sorry, this listing is fully claimed!", "error")
        return redirect(url_for('listing_detail', listing_id=listing_id))
    user_id = session['user_id']
    already = db.execute("SELECT id FROM claims WHERE listing_id=? AND buyer_id=?", (listing_id, user_id)).fetchone()
    if already:
        flash("You've already claimed a portion of this listing.", "error")
        return redirect(url_for('listing_detail', listing_id=listing_id))
    claim_id = f"claim_{uuid.uuid4().hex[:8]}"
    db.execute("INSERT INTO claims (id, listing_id, buyer_id, amount) VALUES (?,?,?,?)",
               (claim_id, listing_id, user_id, listing['price_per_portion']))
    db.execute("UPDATE listings SET portions_claimed=portions_claimed+1 WHERE id=?", (listing_id,))
    db.commit()
    flash(f"🎉 Portion claimed! Check your dashboard for meetup details.", "success")
    return redirect(url_for('confirmation', claim_id=claim_id))

@app.route("/confirmation/<claim_id>")
@login_required
def confirmation(claim_id):
    db = get_db()
    claim = db.execute("""
        SELECT cl.*, l.item, l.meetup_spot, l.pickup_window, l.emoji, l.price_per_portion,
               u.name as seller_name, l.id as listing_id
        FROM claims cl
        JOIN listings l ON cl.listing_id=l.id
        JOIN users u ON l.seller_id=u.id
        WHERE cl.id=?
    """, (claim_id,)).fetchone()
    return render_template("confirmation.html", claim=claim, current_user=get_current_user())

@app.route("/rate/<claim_id>", methods=["POST"])
@login_required
def rate_seller(claim_id):
    rating = int(request.form.get("rating", 5))
    db = get_db()
    claim = db.execute("SELECT * FROM claims WHERE id=? AND buyer_id=?", (claim_id, session['user_id'])).fetchone()
    if claim and not claim['rated_seller']:
        db.execute("UPDATE claims SET rated_seller=1, seller_rating=? WHERE id=?", (rating, claim_id))
        listing = db.execute("SELECT seller_id FROM listings WHERE id=?", (claim['listing_id'],)).fetchone()
        seller = db.execute("SELECT rating, review_count FROM users WHERE id=?", (listing['seller_id'],)).fetchone()
        new_count = seller['review_count'] + 1
        new_rating = ((seller['rating'] * seller['review_count']) + rating) / new_count
        db.execute("UPDATE users SET rating=?, review_count=? WHERE id=?", (round(new_rating,1), new_count, listing['seller_id']))
        db.commit()
    return jsonify({"ok": True})

@app.route("/sell", methods=["GET","POST"])
@login_required
def sell():
    db = get_db()
    communities = db.execute("SELECT * FROM communities ORDER BY name").fetchall()
    if request.method == "POST":
        item = request.form.get("item","").strip()
        category = request.form.get("category","").strip()
        bulk_store = request.form.get("bulk_store","").strip()
        total_qty = request.form.get("total_qty","").strip()
        portion_size = request.form.get("portion_size","").strip()
        portions_total = int(request.form.get("portions_total", 2))
        price = float(request.form.get("price_per_portion", 0))
        retail = float(request.form.get("retail_price", 0) or 0)
        pickup_window = request.form.get("pickup_window","").strip()
        meetup_spot = request.form.get("meetup_spot","").strip()
        community_id = request.form.get("community_id","").strip()
        model = request.form.get("model","pioneer")
        emoji_map = {"Pantry & Food":"🛒","Household Essentials":"🏠","Health & Personal Care":"💊","Pet Supplies":"🐾","Baby & Kids":"👶"}
        emoji = emoji_map.get(category, "📦")
        image_map = {
            "Pantry & Food": "https://images.unsplash.com/photo-1542838132-92c53300491e?w=600&q=80",
            "Household Essentials": "https://images.unsplash.com/photo-1584305574647-0cc949a2bb9f?w=600&q=80",
            "Health & Personal Care": "https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=600&q=80",
            "Pet Supplies": "https://images.unsplash.com/photo-1601758125946-6ec2ef64daf8?w=600&q=80",
            "Baby & Kids": "https://images.unsplash.com/photo-1515488042361-ee00e0ddd4e4?w=600&q=80",
        }
        image_url = image_map.get(category, "https://images.unsplash.com/photo-1542838132-92c53300491e?w=600&q=80")
        if retail > 0 and price > retail:
            flash("⚠️ Price exceeds the platform markup cap.", "error")
            return render_template("sell.html", communities=communities, current_user=get_current_user())
        listing_id = f"l_{uuid.uuid4().hex[:8]}"
        db.execute("""INSERT INTO listings
            (id,seller_id,item,category,bulk_store,total_qty,portion_size,portions_total,
             price_per_portion,retail_price,pickup_window,meetup_spot,community_id,model,emoji,image_url)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (listing_id, session['user_id'], item, category, bulk_store, total_qty, portion_size,
             portions_total, price, retail, pickup_window, meetup_spot, community_id, model, emoji, image_url))
        db.commit()
        flash(f"✅ Your listing for {item} is live!", "success")
        return redirect(url_for('listing_detail', listing_id=listing_id))
    return render_template("sell.html", communities=communities, current_user=get_current_user())

@app.route("/communities")
def communities():
    db = get_db()
    all_communities = db.execute("""
        SELECT c.*, COUNT(cm.user_id) as member_count
        FROM communities c
        LEFT JOIN community_members cm ON c.id=cm.community_id
        GROUP BY c.id ORDER BY c.name
    """).fetchall()
    user_communities = []
    if 'user_id' in session:
        user_communities = [r['community_id'] for r in
            db.execute("SELECT community_id FROM community_members WHERE user_id=?", (session['user_id'],)).fetchall()]
    return render_template("communities.html", communities=all_communities,
                           user_communities=user_communities, current_user=get_current_user())

@app.route("/communities/join/<community_id>", methods=["POST"])
@login_required
def join_community(community_id):
    db = get_db()
    db.execute("INSERT OR IGNORE INTO community_members (user_id, community_id) VALUES (?,?)",
               (session['user_id'], community_id))
    db.execute("UPDATE communities SET member_count=member_count+1 WHERE id=?", (community_id,))
    db.commit()
    return jsonify({"ok": True})

@app.route("/communities/create", methods=["POST"])
@login_required
def create_community():
    db = get_db()
    name = request.form.get("name","").strip()
    description = request.form.get("description","").strip()
    address = request.form.get("address","").strip()
    lat = float(request.form.get("lat", 33.749))
    lng = float(request.form.get("lng", -84.388))
    if not name:
        flash("Please enter a community name.", "error")
        return redirect(url_for('communities'))
    comm_id = f"com_{uuid.uuid4().hex[:6]}"
    db.execute("INSERT INTO communities (id,name,description,lat,lng,address,created_by) VALUES (?,?,?,?,?,?,?)",
               (comm_id, name, description, lat, lng, address, session['user_id']))
    db.execute("INSERT OR IGNORE INTO community_members (user_id, community_id) VALUES (?,?)",
               (session['user_id'], comm_id))
    db.commit()
    flash(f"🌱 Community '{name}' created!", "success")
    return redirect(url_for('communities'))

@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    user = get_current_user()
    my_listings = db.execute("""
        SELECT l.*, c.name as community_name FROM listings l
        LEFT JOIN communities c ON l.community_id=c.id
        WHERE l.seller_id=? ORDER BY l.created_at DESC
    """, (user['id'],)).fetchall()
    my_claims = db.execute("""
        SELECT cl.*, l.item, l.meetup_spot, l.pickup_window, l.emoji,
               u.name as seller_name, l.id as listing_id
        FROM claims cl JOIN listings l ON cl.listing_id=l.id
        JOIN users u ON l.seller_id=u.id
        WHERE cl.buyer_id=? ORDER BY cl.created_at DESC
    """, (user['id'],)).fetchall()
    my_communities = db.execute("""
        SELECT c.* FROM communities c
        JOIN community_members cm ON c.id=cm.community_id
        WHERE cm.user_id=?
    """, (user['id'],)).fetchall()
    return render_template("dashboard.html", user=user, my_listings=my_listings,
                           my_claims=my_claims, my_communities=my_communities, current_user=user)

@app.route("/how-it-works")
def how_it_works():
    return render_template("how_it_works.html", current_user=get_current_user())

@app.route("/api/communities")
def api_communities():
    db = get_db()
    rows = db.execute("SELECT * FROM communities").fetchall()
    return jsonify([dict(r) for r in rows])

# ---------------------------------------------------------------------------
# RUN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_db()
    print("\n🟢  Splitsy v2 is running!")
    print("   Open your browser: http://127.0.0.1:8080\n")
    print("   Demo login: demo@splitsy.com / demo123\n")
    app.run(debug=True, port=8080, host='127.0.0.1')
