from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash
from pymongo import MongoClient
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Change this to a secure random key
app.config['MONGO_URI'] = 'mongodb://test:sparta@ac-pgpmvvq-shard-00-00.zm8eqgi.mongodb.net:27017,ac-pgpmvvq-shard-00-01.zm8eqgi.mongodb.net:27017,ac-pgpmvvq-shard-00-02.zm8eqgi.mongodb.net:27017/?ssl=true&replicaSet=atlas-11mrub-shard-0&authSource=admin&retryWrites=true&w=majority'
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
        role = 'customer'

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

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)