from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
from database import create_connection, initialize_database
import mysql.connector
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialize database when the app starts
with app.app_context():
    initialize_database()

# Home page
@app.route('/')
def index():
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            
            # Get all products
            cursor.execute("""
                SELECT p.*, u.username as seller, c.name as category_name 
                FROM products p 
                JOIN users u ON p.seller_id = u.id 
                JOIN categories c ON p.category_id = c.id 
                ORDER BY p.created_at DESC
            """)
            products = cursor.fetchall()
            
            # Get categories for filter
            cursor.execute("SELECT * FROM categories")
            categories = cursor.fetchall()
            
            cursor.close()
            connection.close()
            
            return render_template('index.html', products=products, categories=categories)
        return "Database connection error", 500
    except Exception as e:
        return f"Error: {str(e)}", 500

# User registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('register'))
        
        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            
            # Check if username or email already exists
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                flash('Username already taken.', 'error')
                return redirect(url_for('register'))
            
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                flash('Email already registered. Please login.', 'error')
                return redirect(url_for('register'))
            
            # Insert new user with hashed password
            hashed_password = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                (username, email, hashed_password)
            )
            connection.commit()
            
            cursor.close()
            connection.close()
            
            flash('Registration successful. Please login.', 'success')
            return redirect(url_for('login'))
        
        return "Database connection error", 500
    
    return render_template('register.html')

# User login

# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        connection = create_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            
            # Select only essential columns to avoid schema dependency
            cursor.execute("SELECT id, username, email, password FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            
            cursor.close()
            connection.close()
            
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['email'] = user['email']
                # Fetch user_image separately if it exists (optional)
                connection = create_connection()
                if connection:
                    cursor = connection.cursor(dictionary=True)
                    cursor.execute("SELECT user_image FROM users WHERE id = %s", (user['id'],))
                    user_image = cursor.fetchone()
                    session['user_image'] = user_image['user_image'] if user_image and 'user_image' in user_image else None
                    cursor.close()
                    connection.close()
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid email or password.', 'error')
        
        return "Database connection error", 500
    
    return render_template('login.html')
# User dashboard
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    connection = create_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        
        if request.method == 'POST':
            # Handle profile update
            username = request.form['username']
            email = request.form['email']
            password = request.form.get('password', None)
            
            # Check for duplicates
            cursor.execute("SELECT id FROM users WHERE username = %s AND id != %s", (username, session['user_id']))
            if cursor.fetchone():
                flash('Username already taken.', 'error')
                return redirect(url_for('dashboard'))
            
            cursor.execute("SELECT id FROM users WHERE email = %s AND id != %s", (email, session['user_id']))
            if cursor.fetchone():
                flash('Email already in use.', 'error')
                return redirect(url_for('dashboard'))
            
            update_query = "UPDATE users SET username = %s, email = %s"
            params = [username, email]
            
            if password:
                hashed_password = generate_password_hash(password)
                update_query += ", password = %s"
                params.append(hashed_password)
            
            # Handle user image upload
            if 'user_image' in request.files:
                file = request.files['user_image']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{timestamp}_{filename}"
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    update_query += ", user_image = %s"
                    params.append(filename)
            
            update_query += " WHERE id = %s"
            params.append(session['user_id'])
            
            cursor.execute(update_query, params)
            connection.commit()
            
            # Update session
            session['username'] = username
            session['email'] = email
            cursor.execute("SELECT user_image FROM users WHERE id = %s", (session['user_id'],))
            user = cursor.fetchone()
            session['user_image'] = user['user_image']
            
            flash('Profile updated successfully!', 'success')
        
        # Get user products
        cursor.execute("""
            SELECT p.*, c.name as category_name 
            FROM products p 
            JOIN categories c ON p.category_id = c.id 
            WHERE p.seller_id = %s 
            ORDER BY p.created_at DESC
        """, (session['user_id'],))
        products = cursor.fetchall()
        
        # Get current user details for display
        cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
        user = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        return render_template('dashboard.html', products=products, user=user)
    
    return "Database connection error", 500

# Add product
@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    connection = create_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM categories")
        categories = cursor.fetchall()
        
        if request.method == 'POST':
            title = request.form['title']
            description = request.form['description']
            price = float(request.form['price'])
            category_id = int(request.form['category_id'])
            image_path = None
            
            if 'image' in request.files:
                file = request.files['image']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{timestamp}_{filename}"
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    image_path = filename
            
            cursor.execute(
                "INSERT INTO products (title, description, price, category_id, seller_id, image_path) VALUES (%s, %s, %s, %s, %s, %s)",
                (title, description, price, category_id, session['user_id'], image_path)
            )
            connection.commit()
            
            flash('Product added successfully!', 'success')
            return redirect(url_for('dashboard'))
        
        cursor.close()
        connection.close()
        
        return render_template('add_product.html', categories=categories)
    
    return "Database connection error", 500

# Edit product
@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    connection = create_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM products WHERE id = %s AND seller_id = %s", (product_id, session['user_id']))
        product = cursor.fetchone()
        
        if not product:
            flash('Product not found or you are not the owner.', 'error')
            return redirect(url_for('dashboard'))
        
        cursor.execute("SELECT * FROM categories")
        categories = cursor.fetchall()
        
        if request.method == 'POST':
            title = request.form['title']
            description = request.form['description']
            price = float(request.form['price'])
            category_id = int(request.form['category_id'])
            
            update_query = "UPDATE products SET title = %s, description = %s, price = %s, category_id = %s"
            params = [title, description, price, category_id]
            
            if 'image' in request.files:
                file = request.files['image']
                if file and allowed_file(file.filename):
                    # Delete old image if exists
                    if product['image_path']:
                        old_path = os.path.join(app.config['UPLOAD_FOLDER'], product['image_path'])
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{timestamp}_{filename}"
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    update_query += ", image_path = %s"
                    params.append(filename)
            
            update_query += " WHERE id = %s"
            params.append(product_id)
            
            cursor.execute(update_query, params)
            connection.commit()
            
            flash('Product updated successfully!', 'success')
            return redirect(url_for('dashboard'))
        
        cursor.close()
        connection.close()
        
        return render_template('edit_product.html', product=product, categories=categories)
    
    return "Database connection error", 500

# Delete product
@app.route('/delete_product/<int:product_id>')
def delete_product(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    connection = create_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM products WHERE id = %s AND seller_id = %s", (product_id, session['user_id']))
        product = cursor.fetchone()
        
        if product:
            # Delete image if exists
            if product['image_path']:
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], product['image_path'])
                if os.path.exists(image_path):
                    os.remove(image_path)
            
            cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
            connection.commit()
            
            flash('Product deleted successfully!', 'success')
        else:
            flash('Product not found or you are not the owner.', 'error')
        
        cursor.close()
        connection.close()
    
    return redirect(url_for('dashboard'))

# Product detail
@app.route('/product/<int:product_id>')
def product_detail(product_id):
    connection = create_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT p.*, u.username as seller, c.name as category_name 
            FROM products p 
            JOIN users u ON p.seller_id = u.id 
            JOIN categories c ON p.category_id = c.id 
            WHERE p.id = %s
        """, (product_id,))
        product = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        if product:
            return render_template('product_detail.html', product=product)
        else:
            flash('Product not found.', 'error')
            return redirect(url_for('index'))
    
    return "Database connection error", 500

# Add to cart
@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    connection = create_connection()
    if connection:
        cursor = connection.cursor()
        
        # Check if already in cart
        cursor.execute("SELECT id, quantity FROM carts WHERE user_id = %s AND product_id = %s", (session['user_id'], product_id))
        existing = cursor.fetchone()
        
        if existing:
            # Increment quantity
            cursor.execute("UPDATE carts SET quantity = quantity + 1 WHERE id = %s", (existing[0],))
        else:
            # Add new
            cursor.execute(
                "INSERT INTO carts (user_id, product_id, quantity) VALUES (%s, %s, 1)",
                (session['user_id'], product_id)
            )
        
        connection.commit()
        cursor.close()
        connection.close()
        
        flash('Item added to cart.', 'success')
    
    return redirect(url_for('index'))

# Cart view
@app.route('/cart', methods=['GET', 'POST'])
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    connection = create_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        
        if request.method == 'POST':
            action = request.form['action']
            cart_id = int(request.form['cart_id'])
            
            if action == 'update':
                quantity = int(request.form['quantity'])
                if quantity > 0:
                    cursor.execute("UPDATE carts SET quantity = %s WHERE id = %s", (quantity, cart_id))
                else:
                    cursor.execute("DELETE FROM carts WHERE id = %s", (cart_id,))
            elif action == 'remove':
                cursor.execute("DELETE FROM carts WHERE id = %s", (cart_id,))
            
            connection.commit()
        
        # Get cart items with seller
        cursor.execute("""
            SELECT c.*, p.title, p.price, p.image_path, u.username as seller 
            FROM carts c 
            JOIN products p ON c.product_id = p.id 
            JOIN users u ON p.seller_id = u.id 
            WHERE c.user_id = %s
        """, (session['user_id'],))
        cart_items = cursor.fetchall()
        
        total = sum(item['price'] * item['quantity'] for item in cart_items)
        
        cursor.close()
        connection.close()
        
        return render_template('cart.html', cart_items=cart_items, total=total)
    
    return "Database connection error", 500

# Checkout
@app.route('/checkout')
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    connection = create_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        
        # Get cart items
        cursor.execute("""
            SELECT c.*, p.price 
            FROM carts c 
            JOIN products p ON c.product_id = p.id 
            WHERE c.user_id = %s
        """, (session['user_id'],))
        cart_items = cursor.fetchall()
        
        if not cart_items:
            flash('Your cart is empty.', 'error')
            return redirect(url_for('cart'))
        
        # Move to purchases
        for item in cart_items:
            total_price = item['price'] * item['quantity']
            cursor.execute(
                "INSERT INTO purchases (user_id, product_id, quantity, total_price) VALUES (%s, %s, %s, %s)",
                (session['user_id'], item['product_id'], item['quantity'], total_price)
            )
        
        # Clear cart
        cursor.execute("DELETE FROM carts WHERE user_id = %s", (session['user_id'],))
        connection.commit()
        
        cursor.close()
        connection.close()
        
        flash('Purchase completed successfully!', 'success')
    
    return redirect(url_for('purchases'))

# View purchases
@app.route('/purchases')
def purchases():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    connection = create_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT pur.*, p.title, p.image_path, u.username as seller 
            FROM purchases pur 
            JOIN products p ON pur.product_id = p.id 
            JOIN users u ON p.seller_id = u.id 
            WHERE pur.user_id = %s 
            ORDER BY pur.purchase_date DESC
        """, (session['user_id'],))
        purchases = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return render_template('purchases.html', purchases=purchases)
    
    return "Database connection error", 500

# Search products
@app.route('/search')
def search():
    query = request.args.get('q', '')
    category_id = request.args.get('category_id', '')
    
    connection = create_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        
        sql = """
            SELECT p.*, u.username as seller, c.name as category_name 
            FROM products p 
            JOIN users u ON p.seller_id = u.id 
            JOIN categories c ON p.category_id = c.id 
            WHERE 1=1
        """
        params = []
        
        if query:
            sql += " AND p.title LIKE %s"
            params.append(f"%{query}%")
        
        if category_id:
            sql += " AND p.category_id = %s"
            params.append(category_id)
        
        sql += " ORDER BY p.created_at DESC"
        
        cursor.execute(sql, params)
        products = cursor.fetchall()
        
        cursor.execute("SELECT * FROM categories")
        categories = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return render_template('index.html', products=products, categories=categories, search_query=query, selected_category=category_id)
    
    return "Database connection error", 500

# User logout
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Create uploads directory if it doesn't exist
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    
    app.run(debug=True)