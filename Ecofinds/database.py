import mysql.connector
from mysql.connector import Error

def create_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='ecofinds_db',
            user='ecofinds_user',
            password='your_secure_password_123'  # Use the password you set
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def initialize_database():
    """Initialize the database with all required tables"""
    try:
        # First connect without specifying a database to check if it exists
        connection = mysql.connector.connect(
            host='localhost',
            user='ecofinds_user',
            password='your_secure_password_123'
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Create database if it doesn't exist
            cursor.execute("CREATE DATABASE IF NOT EXISTS ecofinds_db")
            print("Database checked/created successfully")
            
            # Switch to the database
            cursor.execute("USE ecofinds_db")
            
            # Create users table (added user_image)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    user_image VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("Users table checked/created successfully")
            
            # Create categories table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(50) NOT NULL
                )
            """)
            print("Categories table checked/created successfully")
            
            # Create products table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    price DECIMAL(10, 2) NOT NULL,
                    category_id INT,
                    seller_id INT,
                    image_path VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES categories(id),
                    FOREIGN KEY (seller_id) REFERENCES users(id)
                )
            """)
            print("Products table checked/created successfully")
            
            # Create carts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS carts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    product_id INT,
                    quantity INT DEFAULT 1,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (product_id) REFERENCES products(id)
                )
            """)
            print("Carts table checked/created successfully")
            
            # Create purchases table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS purchases (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    product_id INT,
                    purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    quantity INT DEFAULT 1,
                    total_price DECIMAL(10, 2),
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (product_id) REFERENCES products(id)
                )
            """)
            print("Purchases table checked/created successfully")
            
            # Insert default categories if table is empty
            cursor.execute("SELECT COUNT(*) FROM categories")
            if cursor.fetchone()[0] == 0:
                categories = [
                    ('Electronics',),
                    ('Clothing',),
                    ('Furniture',),
                    ('Books',),
                    ('Sports',),
                    ('Toys',),
                    ('Other',)
                ]
                cursor.executemany("INSERT INTO categories (name) VALUES (%s)", categories)
                print("Default categories added successfully")
            
            connection.commit()
            print("Database initialization completed successfully!")
            
    except Error as e:
        print(f"Error initializing database: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()