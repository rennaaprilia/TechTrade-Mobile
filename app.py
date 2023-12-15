from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash
from pymongo import MongoClient
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Change this to a secure random key
app.config['MONGO_URI'] = 'mongodb+srv://test:sparta@cluster0.zm8eqgi.mongodb.net/techtrade'
app.config['MONGO_DBNAME'] = 'techtrade'
app.config['UPLOAD_FOLDER'] = 'static/uploaded_img'

mongo = PyMongo(app)

@app.route('/')
def hello():
    products = mongo.db.products.find()
    return render_template('index.html',products=products)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = 'customer'  # Default role is 'user'

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        user_data = {
            'username': username,
            'password': hashed_password,
            'role': role
        }

        mongo.db.users.insert_one(user_data)
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = mongo.db.users.find_one({'username': username})

        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['username'] = user['username']
            session['role'] = user['role']
            if session['role'] == 'admin':
                return redirect(url_for('adminDashboard'))
            return redirect(url_for('hello'))

        return 'Invalid username or password'

    return render_template('login.html')

# Route to add a product to the cart
@app.route('/add_to_cart/<product_id>', methods=['GET'])
def add_to_cart(product_id):
    # Ensure the user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Find the product by its ObjectId
    product = mongo.db.products.find_one({'_id': ObjectId(product_id)})
    if not product:
        # Handle the case where the product is not found
        return redirect(url_for('hello'))

    # Create a cart item
    cart_item = {
        'user_id': session['user_id'],
        'product_id': product['_id'],
        'product_name': product['product_name'],
        'price': product['price'],
        'quantity': 1  # You can set the initial quantity as needed
    }

    # Add the cart item to the carts collection
    mongo.db.carts.insert_one(cart_item)

    # Redirect to the product listing page or wherever you want
    return redirect(url_for('hello'))

@app.route('/cart', methods=['GET', 'POST'])
def cart():
    # Ensure the user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Retrieve user's cart items from the carts collection
    user_id = session['user_id']
    cart_items_cursor = mongo.db.carts.find({'user_id': user_id})
    cart_items = list(cart_items_cursor)

    # Calculate the total price
    total_price = sum(int(item['price']) for item in cart_items)

    if request.method == 'POST':
        # Process the order and clear the cart
        user_name = session['username']
        order_time = datetime.now()
        total_products = len(cart_items)
        payment_method = request.form.get('payment_method', 'Not specified')

        # Create a report in the orders collection
        order_data = {
            'user_name': user_name,
            'order_time': order_time,
            'total_products': total_products,
            'total_price': total_price,
            'payment_method': payment_method
        }

        mongo.db.orders.insert_one(order_data)

        # Clear the user's cart
        mongo.db.carts.delete_many({'user_id': user_id})

        flash('Order placed successfully!', 'success')
        return redirect(url_for('cart'))

    # Render the cart template with the list of cart items and total price
    return render_template('cart.html', cart_items=cart_items, total_price=total_price)

# Route to add a product to favorites
@app.route('/add_to_favorites/<product_id>', methods=['GET'])
def add_to_favorites(product_id):
    # Ensure the user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Find the product by its ObjectId
    product = mongo.db.products.find_one({'_id': ObjectId(product_id)})
    if not product:
        # Handle the case where the product is not found
        return redirect(url_for('products'))

    # Create a favorites item
    favorites_item = {
        'user_id': session['user_id'],
        'product_id': product['_id'],
        'product_name': product['product_name'],
        'price': product['price'],
    }

    # Add the favorites item to the favorites collection
    mongo.db.favorites.insert_one(favorites_item)

    # Redirect to the product listing page or wherever you want
    return redirect(url_for('hello'))

# Route to show favorite products
@app.route('/favorites')
def favorites():
    # Ensure the user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Retrieve user's favorite products from the favorites collection
    user_id = session['user_id']
    favorites = mongo.db.favorites.find({'user_id': user_id})

    # Render the favorites template with the list of favorite products
    return render_template('favorites.html', favorites=favorites)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin/dashboard')
def adminDashboard():
    if session['role'] == 'admin':
        return render_template('admindashboard.html')
    return 'Access Denied'

@app.route('/admin/products', methods=['GET', 'POST'])
def products():
    if session['role'] != 'admin':
       return 'Access Denied'
    if request.method == 'POST':
        # Get product data from the form
        product_id = request.form.get('product_id')
        product_name = request.form.get('product_name')
        price = request.form.get('price')
        category = request.form.get('category')

        # Check if the 'product_image' file is present in the form
        if 'product_image' in request.files:
            product_image = request.files['product_image']

            # Save the file to the 'uploads' folder
            upload_folder = app.config['UPLOAD_FOLDER']
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            product_image_path = os.path.join(upload_folder, product_image.filename)
            product_image.save(product_image_path)
            product_image_path = product_image_path.replace("static/", "")
        else:
            # Handle the case where no image is provided
            product_image_path = None

        # Create a dictionary representing the product
        product_data = {
            'product_name': product_name,
            'product_image_path': product_image_path,
            'price': price,
            'category': category
        }

        # Insert or update the product data into the 'products' collection
        if product_id:
            # If product_id is present, update the existing product
            mongo.db.products.update_one({'_id': ObjectId(product_id)}, {'$set': product_data})
        else:
            # If product_id is not present, insert a new product
            mongo.db.products.insert_one(product_data)

        # Redirect to the product listing page or wherever you want
        return redirect(url_for('products'))

    # Display the product listing page
    products = mongo.db.products.find()
    return render_template('products.html', products=products)

# Render edit.html for editing a product
@app.route('/admin/edit_product/<product_id>', methods=['GET'])
def edit_product(product_id):
    if session['role'] != 'admin':
       return 'Access Denied'
    # Find the product by its ObjectId
    product = mongo.db.products.find_one({'_id': ObjectId(product_id)})
    if not product:
        # Handle the case where the product is not found
        return redirect(url_for('products'))

    # Render the edit.html template with the product data
    return render_template('edit.html', product=product)

# Handle form submission for updating a product
@app.route('/admin/edit_product/<product_id>', methods=['POST'])
def update_product(product_id):
    if session['role'] != 'admin':
       return 'Access Denied'
    # Find the product by its ObjectId
    product = mongo.db.products.find_one({'_id': ObjectId(product_id)})
    if not product:
        # Handle the case where the product is not found
        return redirect(url_for('products'))

    # Get updated product data from the form
    product_name = request.form.get('product_name')
    price = request.form.get('price')
    category = request.form.get('category')

    # Check if the 'product_image' file is present in the form
    if 'product_image' in request.files:
        product_image = request.files['product_image']

        # Save the file to the 'uploads' folder
        upload_folder = app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        product_image_path = os.path.join(upload_folder, product_image.filename)
        product_image.save(product_image_path)
        product_image_path = product_image_path.replace("static/", "")

        # Update the product image path
        mongo.db.products.update_one({'_id': ObjectId(product_id)}, {'$set': {'product_image_path': product_image_path}})

    # Update other product fields
    mongo.db.products.update_one({'_id': ObjectId(product_id)}, {'$set': {'product_name': product_name, 'price': price, 'category': category}})

    # Redirect to the product listing page or wherever you want
    return redirect(url_for('products'))

# Route to delete a product
@app.route('/admin/delete_product/<product_id>', methods=['GET'])

def delete_product(product_id):
    if session['role'] != 'admin':
       return 'Access Denied'
    # Find the product by its ObjectId
    product = mongo.db.products.find_one({'_id': ObjectId(product_id)})
    if not product:
        # Handle the case where the product is not found
        return redirect(url_for('products'))

    # Delete the product from the database
    mongo.db.products.delete_one({'_id': ObjectId(product_id)})

    # Optionally, delete the associated image file from the server
    if 'product_image_path' in product:
        image_path = product['product_image_path']
        if os.path.exists(image_path):
            os.remove(image_path)

    # Redirect to the product listing page or wherever you want
    return redirect(url_for('products'))

if __name__ == '__main__':
    app.run(debug=True)