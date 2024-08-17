# app.py
from flask import Flask, request, jsonify, send_from_directory, g
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import jwt
import datetime
import json
import os
import uuid
import time
app = Flask(__name__, static_folder='react_build')
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///zillow_clone.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

class House(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    photo = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
class Bid(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    house_id = db.Column(db.Integer, db.ForeignKey('house.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    user = db.relationship('User', backref='bids')
@app.route('/api/houses/<int:house_id>/bids', methods=['POST'])
def place_bid(house_id):
    data = request.json
    token = request.headers.get('Authorization').split()[1]
    try:
        user_id = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])['user_id']
        new_bid = Bid(amount=data['amount'], user_id=user_id, house_id=house_id)
        db.session.add(new_bid)
        db.session.commit()
        return jsonify({'message': 'Bid placed successfully'}), 201
    except:
        return jsonify({'message': 'Invalid token'}), 401

@app.route('/api/houses/<int:house_id>/bids', methods=['GET'])
def get_bids(house_id):
    bids = Bid.query.filter_by(house_id=house_id).order_by(Bid.amount.desc()).all()
    return jsonify([{
        'id': bid.id,
        'amount': bid.amount,
        'user': bid.user.username,
        'timestamp': bid.timestamp
    } for bid in bids])

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')
    new_user = User(username=data['username'], password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'Registered successfully'}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    if user and check_password_hash(user.password, data['password']):
        token = jwt.encode({'user_id': user.id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)},
                           app.config['SECRET_KEY'])
        return jsonify({'token': token})
    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/api/houses', methods=['GET'])
def get_houses():
    houses = House.query.all()
    return jsonify([{
        'id': house.id,
        'address': house.address,
        'price': house.price,
        'photo': f"/uploads/{house.photo}",
        'user_id': house.user_id
    } for house in houses])
@app.route('/api/houses', methods=['POST'])
def add_house():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'message': 'No token provided'}), 401
    try:
        data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = data['user_id']
        
        address = request.form['address']
        price = request.form['price']
        photo = request.files['photo']
        
        if photo:
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        new_house = House(address=address, price=price, photo=filename, user_id=user_id)
        db.session.add(new_house)
        db.session.commit()
        return jsonify({'message': 'House added successfully'}), 201
    except Exception as e:
        print(f"Error in add_house: {str(e)}")  # Add this line for debugging
        return jsonify({'message': 'Invalid token or error occurred'}), 401
@app.route('/api/config', methods=['GET'])
def get_config():
    with open('config.json', 'r') as config_file:
        config = json.load(config_file)
    return jsonify(config)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Serve React App
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')
@app.route('/api/houses/<int:house_id>', methods=['GET'])
def get_house(house_id):
    house = House.query.get_or_404(house_id)
    user = User.query.get(house.user_id)
    return jsonify({
        'id': house.id,
        'address': house.address,
        'price': house.price,
        'photo': f"/uploads/{house.photo}",
        'user_id': house.user_id,
        'user_name': user.username if user else 'Unknown User'
    })

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify({
        'id': user.id,
        'username': user.username
    })

@app.route('/api/users/current', methods=['GET'])
def get_current_user():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'message': 'No token provided'}), 401
    try:
        data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=['HS256'])
        user = User.query.get(data['user_id'])
        return jsonify({
            'id': user.id,
            'username': user.username
        })
    except:
        return jsonify({'message': 'Invalid token'}), 401
    
@app.route('/api/users/current/houses', methods=['GET'])
def get_current_user_houses():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'message': 'No token provided'}), 401
    try:
        data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=['HS256'])
        houses = House.query.filter_by(user_id=data['user_id']).all()
        return jsonify([{
            'id': house.id,
            'address': house.address,
            'price': house.price,
            'photo': f"/uploads/{house.photo}"
        } for house in houses])
    except:
        return jsonify({'message': 'Invalid token'}), 401
@app.route('/api/users/current/update', methods=['POST'])
def update_current_user():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'message': 'No token provided'}), 401
    try:
        data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=['HS256'])
        user = User.query.get(data['user_id'])
        new_username = request.json.get('username')
        if new_username:
            user.username = new_username
            db.session.commit()
        return jsonify({'message': 'Username updated successfully'})
    except:
        return jsonify({'message': 'Invalid token'}), 401

@app.route('/api/users/<int:user_id>/houses', methods=['GET'])
def get_user_houses(user_id):
    houses = House.query.filter_by(user_id=user_id).all()
    return jsonify([{
        'id': house.id,
        'address': house.address,
        'price': house.price,
        'photo': f"/uploads/{house.photo}"
    } for house in houses])
@app.before_request
def before_request_func():
    execution_id = uuid.uuid4()
    g.start_time = time.time()
    g.execution_id = execution_id

    print(g.execution_id, "ROUTE CALLED ", request.url)

def create_app():
    with app.app_context():
        db.create_all()
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    return app

if __name__ == '__main__':
    create_app()
    app.run(debug=True, host='0.0.0.0', port=5005)