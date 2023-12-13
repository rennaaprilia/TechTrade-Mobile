from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def hello():
    return render_template('index.html')

@app.route('/product')
def index():
    return render_template('product.html')

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)