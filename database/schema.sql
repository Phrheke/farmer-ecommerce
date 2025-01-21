-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role TEXT CHECK(role IN ('farmer', 'customer')) NOT NULL
);

-- Create products table
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price REAL NOT NULL,
    quantity INTEGER NOT NULL,
    description TEXT NOT NULL, -- Added description column
    contact TEXT,
    image TEXT,
    farmer_id INTEGER,
    category TEXT,
    FOREIGN KEY(farmer_id) REFERENCES users(id)
);

-- Create orders table
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    customer_id INTEGER,
    quantity INTEGER NOT NULL,
    payment_option TEXT CHECK(payment_option IN ('credit', 'debit', 'cash')) NOT NULL,
    status TEXT DEFAULT 'Pending', -- Added status column for tracking orders
    FOREIGN KEY(product_id) REFERENCES products(id),
    FOREIGN KEY(customer_id) REFERENCES users(id)
);

-- Create cart table
CREATE TABLE IF NOT EXISTS cart (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL, -- Reference to the customer who owns the cart
    product_id INTEGER NOT NULL, -- Reference to the product in the cart
    quantity INTEGER NOT NULL, -- Quantity of the product
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Timestamp when the product was added to the cart
    FOREIGN KEY(customer_id) REFERENCES users(id),
    FOREIGN KEY(product_id) REFERENCES products(id)
);
