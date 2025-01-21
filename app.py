import logging
from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from database import init_db  # Import the init_db from the database module
from flask import Flask, flash, render_template, redirect, url_for


# Logging Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# App Configuration
app = Flask(__name__)
app.config['DATABASE'] = 'ecommerce.db'
app.secret_key = os.getenv("SECRET_KEY", "777419777")  # Use an environment variable for production
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.permanent_session_lifetime = 3600  # Session expires after 1 hour

# Initialize the database using the command from database.py
@app.cli.command('initdb')
def initdb_command():
    """Initialize the database."""
    logging.info("Initializing the database...")
    init_db()
    logging.info("Database initialized successfully.")

# Ensure the uploads folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
    logging.info(f"Uploads folder created at {app.config['UPLOAD_FOLDER']}.")

# Helper function to check allowed file types
def allowed_file(filename):
    allowed = '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
    logging.debug(f"File '{filename}' allowed: {allowed}")
    return allowed

# Database connection helper
def get_db_connection():
    try:
        logging.info("Connecting to the database...")
        conn = sqlite3.connect(app.config['DATABASE'])
        conn.row_factory = sqlite3.Row
        logging.info("Database connection successful.")
        return conn
    except sqlite3.Error as e:
        logging.error(f"Database connection error: {e}")
        return None

# Routes
@app.route('/')
def index():
    logging.info("Rendering index page.")
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        role = request.form.get('role')
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        # Validate inputs
        if not role or not name or not email or not password:
            logging.warning("Signup failed: Missing required fields.")
            flash('All fields are required.', 'danger')
            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password)
        logging.info("Password hashed successfully.")

        # Insert into the database
        conn = get_db_connection()
        if conn:
            try:
                logging.info("Inserting new user into the database...")
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                               (name, email, hashed_password, role))
                conn.commit()
                logging.info("User signed up successfully.")
                flash('Signup successful! Please login.', 'success')
            except sqlite3.Error as e:
                logging.error(f"Database error during signup: {e}")
                flash(f"Database error: {e}", 'danger')
            finally:
                conn.close()
        return redirect(url_for('login'))
    logging.info("Rendering signup page.")
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        conn = get_db_connection()
        if conn:
            try:
                logging.info("Fetching user data from the database...")
                user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
                conn.close()
                if user and check_password_hash(user['password'], password):
                    logging.info(f"User {user['email']} authenticated successfully.")
                    session.permanent = True
                    session['user_id'] = user['id']
                    session['role'] = user['role']
                    session['name'] = user['name']
                    if user['role'] == 'farmer':
                        return redirect(url_for('dashboard'))
                    else:
                        return redirect(url_for('marketplace'))
                else:
                    logging.warning("Invalid email or password.")
                    flash('Invalid email or password!', 'danger')
            except sqlite3.Error as e:
                logging.error(f"Database error during login: {e}")
                flash(f"Database error: {e}", 'danger')
    logging.info("Rendering login page.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    logging.info(f"User {session.get('user_id')} logged out.")
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('role') != 'farmer':
        logging.warning("Unauthorized access to dashboard.")
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    if conn:
        try:
            logging.info("Fetching farmer's products and orders...")
            products = conn.execute("SELECT * FROM products WHERE farmer_id = ?", (session['user_id'],)).fetchall()
            orders = conn.execute("SELECT orders.*, products.name AS product_name FROM orders JOIN products ON orders.product_id = products.id WHERE products.farmer_id = ?", (session['user_id'],)).fetchall()
            conn.close()
            logging.info("Farmer's data fetched successfully.")
            return render_template('dashboard.html', products=products, orders=orders)
        except sqlite3.Error as e:
            logging.error(f"Database error while fetching dashboard data: {e}")
            flash("Database connection error!", "danger")
    return redirect(url_for('index'))

@app.route('/addproduct', methods=['GET', 'POST'])

def addproduct():
    if 'user_id' not in session or session.get('role') != 'farmer':
        logging.warning("Unauthorized access to add product.")
        return redirect(url_for('login'))

    farmer_id = session.get('user_id')
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        quantity = request.form['quantity']
        category = request.form['category']
        contact = request.form['contact']

        # Handle file upload
        image = request.files.get('image')
        image_filename = None
        if image and allowed_file(image.filename):
            image_filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
            logging.info(f"Image '{image_filename}' uploaded successfully.")

        if not name or not price or not category:
            logging.warning("Add product failed: Missing required fields.")
            flash('Name, price, and category are required!', 'danger')
            return redirect(request.url)

        conn = get_db_connection()
        try:
            logging.info("Inserting new product into the database...")
            conn.execute('''INSERT INTO products (name, price, quantity, description, contact, image, farmer_id, category)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                         (name, price, quantity, description, contact, image_filename, farmer_id, category))
            conn.commit()
            logging.info("Product added successfully.")
            flash('Product added successfully!', 'success')
        except sqlite3.Error as e:
            logging.error(f"Error adding product: {e}")
            flash(f"Error adding product: {e}", 'danger')
        finally:
            conn.close()
        return redirect(url_for('dashboard'))
    logging.info("Rendering add product page.")
    return render_template('addproduct.html')

@app.route('/delete_product/<int:product_id>')

def delete_product(product_id):
    if 'user_id' not in session or session.get('role') != 'farmer':
        logging.warning("Unauthorized access to delete product.")
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn:
        try:
            logging.info(f"Deleting product with ID {product_id}...")
            conn.execute("DELETE FROM products WHERE id = ? AND farmer_id = ?", (product_id, session['user_id']))
            conn.commit()
            logging.info("Product deleted successfully.")
            flash('Product deleted successfully!', 'info')
        except sqlite3.Error as e:
            logging.error(f"Error deleting product: {e}")
            flash(f"Database error: {e}", 'danger')
        finally:
            conn.close()
    return redirect(url_for('dashboard'))

@app.route('/marketplace')
def marketplace():
    """Display the marketplace for all users."""
    search_query = request.args.get('search', '').strip()
    category_filter = request.args.get('category', '').strip()

    conn = get_db_connection()
    products = []
    if conn:
        try:
            logging.info("Fetching products from the marketplace...")
            query = "SELECT * FROM products WHERE 1=1"
            params = []

            if search_query:
                query += " AND name LIKE ?"
                params.append(f"%{search_query}%")
            
            if category_filter:
                query += " AND category = ?"
                params.append(category_filter)
            
            products = conn.execute(query, params).fetchall()
            logging.info("Products fetched successfully.")
        except sqlite3.Error as e:
            logging.error(f"Database error while fetching products: {e}")
            flash(f"Database error: {e}", 'danger')
        finally:
            conn.close()

    # Check if the user is logged in (optional, for displaying user-specific features)
    is_logged_in = 'user_id' in session and session.get('role') == 'customer'

    return render_template('marketplace.html', products=products, is_logged_in=is_logged_in)

@app.route('/productpage/<int:product_id>', methods=['GET', 'POST'])
def product_page(product_id):
    if 'user_id' not in session or session.get('role') != 'customer':
        logging.warning("Unauthorized access to product page.")
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    if conn:
        if request.method == 'GET':
            # Fetch product details to display
            logging.info(f"Fetching product details for product ID {product_id}...")
            product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
            conn.close()
            if not product:
                logging.warning(f"Product with ID {product_id} not found.")
                flash("Product not found!", "warning")
                return redirect(url_for('marketplace'))
            logging.info(f"Product with ID {product_id} fetched successfully.")
            return render_template('productpage.html', product=product)

        elif request.method == 'POST':
            # Add to Cart functionality
            quantity = int(request.form.get('quantity', 1))
            cart = session.get('cart', {})
            
            # Update the cart
            if str(product_id) in cart:
                cart[str(product_id)] += quantity
            else:
                cart[str(product_id)] = quantity

            session['cart'] = cart
            session.modified = True
            logging.info(f"Product ID {product_id} added to cart with quantity {quantity}. Current cart: {cart}.")
            flash('Product added to cart successfully!', 'success')
            return redirect(url_for('product_page', product_id=product_id))

    return redirect(url_for('marketplace'))


@app.route('/orders')

def orders():
    if 'user_id' not in session or session.get('role') != 'customer':
        logging.warning(f"Unauthorized access attempt to orders page by user {session.get('user_id')}.")
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    if conn:
        try:
            logging.info(f"Fetching orders for customer {session['user_id']}...")
            orders = conn.execute("""
                SELECT orders.id, products.name AS product_name, orders.quantity, orders.payment_option, orders.status
                FROM orders
                JOIN products ON orders.product_id = products.id
                WHERE orders.customer_id = ?
            """, (session['user_id'],)).fetchall()
            conn.close()
            logging.info(f"Fetched {len(orders)} orders for customer {session['user_id']}.")
            return render_template('orders.html', orders=orders)
        except sqlite3.Error as e:
            logging.error(f"Database error while fetching orders: {e}")
            flash(f"Database error: {e}", "danger")
            conn.close()
            return redirect(url_for('index'))
    else:
        logging.error("Database connection error in orders route.")
        flash("Database connection error!", "danger")
        return redirect(url_for('index'))

@app.route('/delete_order/<int:order_id>')

def delete_order(order_id):
    if 'user_id' not in session or session.get('role') != 'customer':
        logging.warning(f"Unauthorized access attempt to delete order with ID {order_id} by user {session.get('user_id')}.")
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn:
        try:
            logging.info(f"Attempting to delete order with ID {order_id} for customer {session['user_id']}...")
            conn.execute("DELETE FROM orders WHERE id = ? AND customer_id = ?", (order_id, session['user_id']))
            conn.commit()
            logging.info(f"Order with ID {order_id} deleted successfully for customer {session['user_id']}.")
            flash('Order deleted successfully!', 'info')
        except sqlite3.Error as e:
            logging.error(f"Database error while deleting order with ID {order_id}: {e}")
            flash(f"Database error: {e}", 'danger')
        finally:
            conn.close()
    return redirect(url_for('orders'))

@app.route('/confirm_delivery/<int:order_id>', methods=['GET'])

def confirm_delivery(order_id):
    # Check if user is logged in and is a customer
    if 'user_id' not in session or session.get('role') != 'customer':
        logging.warning(f"Unauthorized access attempt to confirm delivery for order ID {order_id} by user {session.get('user_id')}.")
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn:
        try:
            logging.info(f"Attempting to confirm delivery for order with ID {order_id} for customer {session['user_id']}...")

            # Update the status of the order to 'Completed' for the given order_id and customer_id
            # Only change status if the current status is 'Pending'
            result = conn.execute("""
                UPDATE orders
                SET status = 'Completed'
                WHERE id = ? AND customer_id = ? AND status = 'Pending'
            """, (order_id, session['user_id']))
            conn.commit()

            # Check if the update was successful (i.e., any rows were affected)
            if conn.total_changes > 0:
                logging.info(f"Order with ID {order_id} confirmed as delivered for customer {session['user_id']}.")
                flash('Order confirmed as delivered!', 'info')
            else:
                logging.warning(f"Order with ID {order_id} was not in Pending status or was not found for customer {session['user_id']}.")
                flash('No pending order found to confirm delivery or the order has already been completed.', 'warning')

        except sqlite3.Error as e:
            logging.error(f"Database error while confirming delivery for order with ID {order_id}: {e}")
            flash(f"Database error: {e}", 'danger')
        finally:
            conn.close()

    return redirect(url_for('orders'))

@app.route('/cart')

def cart():
    """Display items in the user's cart."""
    if 'user_id' not in session or session.get('role') != 'customer':
        logging.warning("Unauthorized access to cart.")
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cart_items = []
    total_price = 0
    if conn:
        try:
            logging.info("Fetching items from the cart...")

            # Run the query to get cart items along with total price for each item
            query = """
                SELECT cart.id AS cart_id, products.name AS product_name, cart.quantity, products.price, 
                       (cart.quantity * products.price) AS total_price 
                FROM cart 
                JOIN products ON cart.product_id = products.id 
                WHERE cart.customer_id = ?
            """
            cart_items = conn.execute(query, (session['user_id'],)).fetchall()

            # Log the fetched cart items
            logging.info(f"Fetched cart items: {cart_items}")

            # Calculate the total price for all items in the cart
            total_price = sum(item['total_price'] for item in cart_items)
            logging.info(f"Total price for the cart: {total_price}")

            conn.close()
            logging.info("Cart items fetched successfully.")
        except sqlite3.Error as e:
            logging.error(f"Database error while fetching cart items: {e}")
            flash("Database connection error!", "danger")
            return redirect(url_for('marketplace'))
    
    # Log the total price
    logging.info(f"Final total price: {total_price}")

    return render_template('cart.html', cart_items=cart_items, total_price=total_price)

@app.route('/add_to_cart', methods=['POST'])

def add_to_cart():
    """Add product to the cart."""
    try:
        if 'user_id' not in session:
            logging.warning("Unauthorized access attempt to add_to_cart.")
            flash("You need to log in first!", "danger")
            return redirect(url_for('login'))

        product_id = request.form.get('product_id')
        quantity = request.form.get('quantity', type=int)

        # Validate input
        if not product_id or quantity is None or quantity <= 0:
            logging.error(f"Invalid product or quantity: product_id={product_id}, quantity={quantity}.")
            flash("Invalid product or quantity!", "danger")
            return redirect(url_for('marketplace'))

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if the product exists in the database
        product = cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
        if not product:
            logging.error(f"Product with ID {product_id} not found in the database.")
            flash("Product not found!", "danger")
            return redirect(url_for('marketplace'))

        # Check if the product already exists in the cart
        cart_item = cursor.execute('''
            SELECT * FROM cart WHERE customer_id = ? AND product_id = ?
        ''', (session['user_id'], product_id)).fetchone()

        if cart_item:
            # If the product is already in the cart, update the quantity
            new_quantity = cart_item['quantity'] + quantity
            cursor.execute('''
                UPDATE cart SET quantity = ? WHERE customer_id = ? AND product_id = ?
            ''', (new_quantity, session['user_id'], product_id))
            logging.info(f"Updated quantity of product ID {product_id} in cart. New quantity: {new_quantity}")
            flash(f"Updated quantity of {product['name']} in your cart.", "success")
        else:
            # If the product is not in the cart, add a new entry
            cursor.execute('''
                INSERT INTO cart (customer_id, product_id, quantity) 
                VALUES (?, ?, ?)
            ''', (session['user_id'], product_id, quantity))
            logging.info(f"Added product ID {product_id} to cart with quantity {quantity}.")
            flash("Product added to your cart!", "success")

        # Commit changes and close connection
        conn.commit()

    except sqlite3.Error as e:
        logging.error(f"Database error while adding product to cart: {e}")
        flash("An error occurred while adding the product to your cart.", "danger")
    except Exception as e:
        logging.error(f"Unexpected error in add_to_cart route: {e}")
        flash("An unexpected error occurred. Please try again.", "danger")
    finally:
        if conn:
            conn.close()

    return redirect(url_for('marketplace'))  # Redirect to the marketplace after adding to the cart


@app.route('/remove_from_cart/<int:cart_id>', methods=['POST'])

def remove_from_cart(cart_id):
    """Remove an item from the cart."""
    if 'user_id' not in session or session.get('role') != 'customer':
        logging.warning("Unauthorized access to remove from cart.")
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    if conn:
        try:
            logging.info(f"Removing item with cart ID {cart_id} from cart...")
            conn.execute("DELETE FROM cart WHERE id = ? AND customer_id = ?", (cart_id, session['user_id']))
            conn.commit()
            logging.info(f"Item with cart ID {cart_id} removed from cart successfully.")
            flash('Item removed from cart!', 'info')
        except sqlite3.Error as e:
            logging.error(f"Database error while removing from cart: {e}")
            flash("Database connection error!", "danger")
        finally:
            conn.close()
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET', 'POST'])

def checkout():
    """Checkout the cart items."""
    if 'user_id' not in session or session.get('role') != 'customer':
        logging.warning("Unauthorized access to checkout.")
        flash("You need to log in as a customer to proceed with checkout.", "danger")
        return redirect(url_for('login'))

    # Handle GET request
    if request.method == 'GET':
        logging.info("GET request to /checkout - redirecting to cart.")
        flash("Please use the checkout button to proceed.", "warning")
        return redirect(url_for('cart'))

    # Handle POST request
    logging.info("POST request received at /checkout.")
    conn = get_db_connection()
    if conn:
        try:
            # Retrieve payment option from the form
            payment_option = request.form.get('payment_option')
            logging.info(f"Received payment option: {payment_option}")
            if payment_option not in ['credit', 'debit', 'cash']:
                logging.warning("Invalid payment option selected.")
                flash("Invalid payment option selected!", "danger")
                return redirect(url_for('cart'))

            # Fetch cart items
            cart_items = conn.execute(
                "SELECT * FROM cart WHERE customer_id = ?", 
                (session['user_id'],)
            ).fetchall()

            if not cart_items:
                logging.warning("No items in the cart during checkout.")
                flash("Your cart is empty. Add items before checking out.", "danger")
                return redirect(url_for('cart'))

            # Process each cart item
            for item in cart_items:
                product = conn.execute(
                    "SELECT * FROM products WHERE id = ?", 
                    (item['product_id'],)
                ).fetchone()

                if product['quantity'] < item['quantity']:
                    flash(f"Not enough stock for {product['name']}!", "danger")
                    return redirect(url_for('cart'))

                # Insert order
                conn.execute(
                    """
                    INSERT INTO orders (product_id, customer_id, quantity, total_price, payment_option)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (item['product_id'], session['user_id'], item['quantity'], 
                     item['quantity'] * product['price'], payment_option)
                )

                # Update product stock
                conn.execute(
                    "UPDATE products SET quantity = quantity - ? WHERE id = ?",
                    (item['quantity'], item['product_id'])
                )

            # Clear cart
            conn.execute("DELETE FROM cart WHERE customer_id = ?", (session['user_id'],))
            conn.commit()
            logging.info("Checkout completed successfully.")
            flash("Checkout successful! Your order has been placed.", "success")
        except sqlite3.Error as e:
            logging.error(f"Database error during checkout: {e}")
            flash("An error occurred during checkout. Please try again.", "danger")
        finally:
            conn.close()

    return redirect(url_for('orders'))

if __name__ == '__main__':
    app.run(debug=True)
