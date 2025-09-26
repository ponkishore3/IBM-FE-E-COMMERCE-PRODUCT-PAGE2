from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(_name_)
app.secret_key = "super_secret_key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ----------------------
# Models
# ----------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)

# ----------------------
# Helpers
# ----------------------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in.")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = User.query.get(session.get("user_id"))
        if not user or not user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated

# ----------------------
# Routes
# ----------------------
@app.route("/")
def home():
    products = Product.query.all()
    user = None
    if "user_id" in session:
        user = User.query.get(session["user_id"])
    return render_template("home.html", products=products, user=user)

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = generate_password_hash(request.form["password"])
        if User.query.filter_by(username=username).first():
            flash("Username already taken.")
            return redirect(url_for("register"))
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        flash("Account created. Please log in.")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            flash("Logged in successfully.")
            return redirect(url_for("home"))
        flash("Invalid credentials.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Logged out.")
    return redirect(url_for("home"))

# Cart
@app.route("/add/<int:product_id>")
@login_required
def add_to_cart(product_id):
    if "cart" not in session:
        session["cart"] = []
    session["cart"].append(product_id)
    session.modified = True
    flash("Product added to cart.")
    return redirect(url_for("cart"))

@app.route("/cart")
@login_required
def cart():
    cart_items = []
    total = 0
    if "cart" in session:
        for pid in session["cart"]:
            prod = Product.query.get(pid)
            if prod:
                cart_items.append(prod)
                total += prod.price
    return render_template("cart.html", cart=cart_items, total=total)

@app.route("/checkout", methods=["GET","POST"])
@login_required
def checkout():
    if request.method == "POST":
        if "cart" not in session or not session["cart"]:
            flash("Cart empty.")
            return redirect(url_for("cart"))
        items = [Product.query.get(pid) for pid in session["cart"]]
        for item in items:
            if item.stock <= 0:
                flash(f"{item.name} out of stock")
                return redirect(url_for("cart"))
        for item in items:
            item.stock -= 1
        db.session.commit()
        session.pop("cart", None)
        flash("Order placed successfully!")
        return redirect(url_for("home"))
    return render_template("checkout.html")

# Admin
@app.route("/admin")
@admin_required
def admin_index():
    products = Product.query.all()
    return render_template("admin/index.html", products=products)

@app.route("/admin/add", methods=["GET","POST"])
@admin_required
def admin_add_product():
    if request.method == "POST":
        name = request.form["name"].strip()
        price = float(request.form["price"])
        stock = int(request.form["stock"])
        prod = Product(name=name, price=price, stock=stock)
        db.session.add(prod)
        db.session.commit()
        flash("Product added.")
        return redirect(url_for("admin_index"))
    return render_template("admin/add_product.html")

@app.route("/admin/edit/<int:product_id>", methods=["GET","POST"])
@admin_required
def admin_edit_product(product_id):
    prod = Product.query.get_or_404(product_id)
    if request.method == "POST":
        prod.name = request.form["name"].strip()
        prod.price = float(request.form["price"])
        prod.stock = int(request.form["stock"])
        db.session.commit()
        flash("Product updated.")
        return redirect(url_for("admin_index"))
    return render_template("admin/edit_product.html", product=prod)

@app.route("/admin/delete/<int:product_id>", methods=["POST"])
@admin_required
def admin_delete_product(product_id):
    prod = Product.query.get_or_404(product_id)
    db.session.delete(prod)
    db.session.commit()
    flash("Product deleted.")
    return redirect(url_for("admin_index"))

# ----------------------
# Initial setup
# ----------------------
def create_admin():
    if not User.query.filter_by(is_admin=True).first():
        admin = User(username="admin", password=generate_password_hash("adminpass"), is_admin=True)
        db.session.add(admin)
        db.session.commit()
        print("Admin created -> username: admin, password: adminpass")

# ----------------------
if _name_ == "_main_":
    with app.app_context():
        db.create_all()
        create_admin()
    app.run(debug=True)