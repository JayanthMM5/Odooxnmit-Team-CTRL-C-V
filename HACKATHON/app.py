from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Change in production
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

DB_NAME = 'ecofinds.db'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Initialize DB
def init_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        username TEXT NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        discount REAL DEFAULT 0.0,
        image_url TEXT DEFAULT 'placeholder.jpg'
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS carts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER DEFAULT 1
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()

    # Add discount if not exists
    c.execute("PRAGMA table_info(products)")
    columns = [col['name'] for col in c.fetchall()]
    if 'discount' not in columns:
        c.execute("ALTER TABLE products ADD COLUMN discount REAL DEFAULT 0.0")
        conn.commit()

    # Seed dummy admin user if not exists
    c.execute('SELECT * FROM users WHERE email = "admin@ecofinds.com"')
    if not c.fetchone():
        admin_password = generate_password_hash('adminpass')
        c.execute('INSERT INTO users (email, password, username) VALUES (?, ?, ?)', 
                  ('admin@ecofinds.com', admin_password, 'Admin'))
        conn.commit()

    # Get admin user_id
    c.execute('SELECT id FROM users WHERE email = "admin@ecofinds.com"')
    admin_id = c.fetchone()['id']

    # Seed sample products if none exist
    c.execute('SELECT COUNT(*) FROM products')
    if c.fetchone()['COUNT(*)'] == 0:
        samples = [
            ('Vintage Laptop', 'Lightly used Dell laptop, perfect for students.', 'Electronics', 150.00, 10.0, 'https://images.unsplash.com/photo-1496181133206-80ce9b88a7ae?auto=format&fit=crop&q=80&w=300&h=200'),
            ('Smartphone', 'iPhone 8 in good condition, unlocked.', 'Electronics', 100.00, 0.0, 'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&q=80&w=300&h=200'),
            ('Denim Jeans', 'Pre-owned Levi\'s jeans, size 32.', 'Clothing', 20.00, 5.0, 'https://images.unsplash.com/photo-1584378449755-1f7aebb80c3a?auto=format&fit=crop&q=80&w=300&h=200'),
            ('Summer Dress', 'Lightly worn floral dress, size M.', 'Clothing', 15.00, 0.0, 'https://images.unsplash.com/photo-1567401893414-96b9bc4c6c2e?auto=format&fit=crop&q=80&w=300&h=200'),
            ('Wooden Chair', 'Antique wooden chair, sturdy and stylish.', 'Furniture', 50.00, 15.0, 'https://images.unsplash.com/photo-1586023492125-27b2c045be8b?auto=format&fit=crop&q=80&w=300&h=200'),
            ('Sofa Set', 'Comfortable 3-seater sofa, minor wear.', 'Furniture', 200.00, 20.0, 'https://images.unsplash.com/photo-1555041469-a586c61ea9ec?auto=format&fit=crop&q=80&w=300&h=200'),
            ('Classic Novels Bundle', 'Set of 5 vintage books, great condition.', 'Books', 10.00, 0.0, 'https://images.unsplash.com/photo-1491841573634-28140fc7b69b?auto=format&fit=crop&q=80&w=300&h=200'),
            ('Old Textbooks', 'Assorted educational books, used but intact.', 'Books', 5.00, 0.0, 'https://images.unsplash.com/photo-1476275466078-4007374eaa43?auto=format&fit=crop&q=80&w=300&h=200'),
            ('Bicycle', 'Second-hand mountain bike, ready to ride.', 'Other', 80.00, 10.0, 'https://images.unsplash.com/photo-1485965120184-e220f721d03e?auto=format&fit=crop&q=80&w=300&h=200'),
            ('Toy Collection', 'Mixed kids toys, gently used.', 'Other', 25.00, 0.0, 'https://images.unsplash.com/photo-1561336313-0bd5e0b27ec8?auto=format&fit=crop&q=80&w=300&h=200')
        ]
        for title, desc, cat, price, discount, img in samples:
            c.execute('INSERT INTO products (user_id, title, description, category, price, discount, image_url) VALUES (?, ?, ?, ?, ?, ?, ?)',
                      (admin_id, title, desc, cat, price, discount, img))
        conn.commit()
    conn.close()

init_db()

# Helper: Get DB connection
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# Landing
@app.route('/')
def landing():
    conn = get_db()
    c = conn.cursor()
    category = request.args.get('category')
    search = request.args.get('search')
    query = 'SELECT * FROM products'
    params = []
    if category:
        query += ' WHERE category = ?'
        params.append(category)
    elif search:
        query += ' WHERE title LIKE ?'
        params.append(f'%{search}%')
    else:
        query += ' ORDER BY RANDOM() LIMIT 8'  # Random best picks
    c.execute(query, params)
    products = c.fetchall()
    conn.close()
    categories = ['Electronics', 'Clothing', 'Furniture', 'Books', 'Other']
    return render_template('landing.html', products=products, categories=categories)

# Sign Up
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        username = request.form['username']
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute('INSERT INTO users (email, password, username) VALUES (?, ?, ?)', (email, password, username))
            conn.commit()
            flash('Account created! Please log in.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already exists.')
        conn.close()
    return render_template('signup.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('landing'))
        flash('Invalid credentials.')
    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('landing'))

# Dashboard
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
    user = c.fetchone()
    if request.method == 'POST':
        username = request.form['username']
        c.execute('UPDATE users SET username = ? WHERE id = ?', (username, session['user_id']))
        conn.commit()
        session['username'] = username
        flash('Profile updated.')
    c.execute('SELECT * FROM products WHERE user_id = ?', (session['user_id'],))
    listings = c.fetchall()
    conn.close()
    return render_template('dashboard.html', user=user, listings=listings)

# Add Product
@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        category = request.form['category']
        price = float(request.form['price'])
        discount_str = request.form.get('discount', '0.0')
        discount = float(discount_str) if discount_str else 0.0
        image_url = 'placeholder.jpg'
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_url = f'uploads/{filename}'
        conn = get_db()
        c = conn.cursor()
        c.execute('INSERT INTO products (user_id, title, description, category, price, discount, image_url) VALUES (?, ?, ?, ?, ?, ?, ?)',
                  (session['user_id'], title, description, category, price, discount, image_url))
        conn.commit()
        conn.close()
        flash('Product added successfully!')
        return redirect(url_for('dashboard'))
    categories = ['Electronics', 'Clothing', 'Furniture', 'Books', 'Other']
    return render_template('add_product.html', categories=categories)

# Edit Product
@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM products WHERE id = ? AND user_id = ?', (product_id, session['user_id']))
    product = c.fetchone()
    if not product:
        flash('Product not found or not yours.')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        category = request.form['category']
        price = float(request.form['price'])
        discount_str = request.form.get('discount', '0.0')
        discount = float(discount_str) if discount_str else 0.0
        image_url = product['image_url']
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_url = f'uploads/{filename}'
        c.execute('UPDATE products SET title = ?, description = ?, category = ?, price = ?, discount = ?, image_url = ? WHERE id = ?',
                  (title, description, category, price, discount, image_url, product_id))
        conn.commit()
        flash('Product updated successfully!')
        return redirect(url_for('dashboard'))
    categories = ['Electronics', 'Clothing', 'Furniture', 'Books', 'Other']
    conn.close()
    return render_template('edit_product.html', product=product, categories=categories)

# Delete Product
@app.route('/delete_product/<int:product_id>')
def delete_product(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM products WHERE id = ? AND user_id = ?', (product_id, session['user_id']))
    conn.commit()
    conn.close()
    flash('Product deleted successfully!')
    return redirect(url_for('dashboard'))

# Product Detail
@app.route('/product/<int:product_id>')
def product_detail(product_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    product = c.fetchone()
    conn.close()
    if not product:
        flash('Product not found.')
        return redirect(url_for('landing'))
    score = min(len(product['description']) // 10 + {'Electronics': 5, 'Clothing': 10}.get(product['category'], 0), 100)
    return render_template('product_detail.html', product=product, score=score)

# Add to Cart
@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM carts WHERE user_id = ? AND product_id = ?', (session['user_id'], product_id))
    existing = c.fetchone()
    if existing:
        c.execute('UPDATE carts SET quantity = quantity + 1 WHERE id = ?', (existing['id'],))
    else:
        c.execute('INSERT INTO carts (user_id, product_id) VALUES (?, ?)', (session['user_id'], product_id))
    conn.commit()
    conn.close()
    flash('Added to cart!')
    return redirect(url_for('product_detail', product_id=product_id))

# Cart
@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT p.*, c.quantity FROM products p 
                 JOIN carts c ON p.id = c.product_id WHERE c.user_id = ?''', (session['user_id'],))
    items = c.fetchall()
    total = sum((item['price'] - (item['discount'] or 0.0)) * item['quantity'] for item in items)
    conn.close()
    return render_template('cart.html', items=items, total=total)

# Remove from Cart
@app.route('/remove_from_cart/<int:product_id>')
def remove_from_cart(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM carts WHERE user_id = ? AND product_id = ?', (session['user_id'], product_id))
    conn.commit()
    conn.close()
    flash('Removed from cart!')
    return redirect(url_for('cart'))

# Checkout
@app.route('/checkout')
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM carts WHERE user_id = ?', (session['user_id'],))
    cart_items = c.fetchall()
    items = []
    total = 0
    for item in cart_items:
        c.execute('SELECT * FROM products WHERE id = ?', (item['product_id'],))
        product = c.fetchone()
        discounted_price = product['price'] - (product['discount'] or 0.0)
        subtotal = discounted_price * item['quantity']
        total += subtotal
        items.append({'title': product['title'], 'quantity': item['quantity'], 'subtotal': subtotal})
        c.execute('INSERT INTO purchases (user_id, product_id) VALUES (?, ?)', (session['user_id'], item['product_id']))
    c.execute('DELETE FROM carts WHERE user_id = ?', (session['user_id'],))
    conn.commit()
    conn.close()

    # Generate PDF bill
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.drawString(100, 750, "EcoFinds Bill")
    p.drawString(100, 730, f"User: {session['username']}")
    p.drawString(100, 710, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y = 680
    for item in items:
        p.drawString(100, y, f"{item['title']} x {item['quantity']} = ₹{item['subtotal']}")
        y -= 20
    p.drawString(100, y - 20, f"Total: ₹{total}")
    p.save()
    buffer.seek(0)
    flash('Checkout complete! Congratulations on your purchase!')
    return send_file(buffer, as_attachment=True, download_name='bill.pdf', mimetype='application/pdf')

# Previous Purchases
@app.route('/previous_purchases')
def previous_purchases():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT p.*, pu.purchase_date FROM products p 
                 JOIN purchases pu ON p.id = pu.product_id WHERE pu.user_id = ?''', (session['user_id'],))
    purchases = c.fetchall()
    conn.close()
    return render_template('previous_purchases.html', purchases=purchases)

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
