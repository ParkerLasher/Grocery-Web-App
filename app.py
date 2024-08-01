from flask import Flask, request, jsonify, session
from flask_pymongo import PyMongo
from flask_cors import CORS
from bson.objectid import ObjectId
import pandas as pd
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.config["MONGO_URI"] = os.getenv("MONGO_URI")
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# Ensure proper CORS handling
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "http://grocery.parkerlasher.com"}})

mongo = PyMongo(app)

@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = 'http://grocery.parkerlasher.com'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

@app.route('/register', methods=['POST'])
def register():
    email = request.json.get('email')
    password = request.json.get('password')
    if not email or not password:
        return jsonify({'message': 'Email and password are required'}), 400
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
    mongo.db.users.insert_one({'email': email, 'password': hashed_password})
    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/login', methods=['POST'])
def login():
    email = request.json.get('email')
    password = request.json.get('password')
    user = mongo.db.users.find_one({'email': email})
    if user and check_password_hash(user['password'], password):
        session['user_id'] = str(user['_id'])
        print(f"User ID set in session: {session['user_id']}")  # Logging user ID set in session
        return jsonify({'message': 'Logged in successfully'}), 200
    return jsonify({'message': 'Invalid email or password'}), 401

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/items', methods=['GET'])
def get_items():
    if 'user_id' not in session:
        return jsonify({'message': 'Unauthorized access'}), 401

    user_id = session['user_id']
    print(f"Fetching items for user_id: {user_id}")  # Logging fetching items for user ID
    items = list(mongo.db.items.find({'user_id': user_id}))
    for item in items:
        item['_id'] = str(item['_id'])
    return jsonify(items)

@app.route('/items', methods=['POST'])
def add_item():
    if 'user_id' not in session:
        return jsonify({'message': 'Unauthorized access'}), 401

    data = request.json
    data['user_id'] = session['user_id']
    print(f"Adding item for user_id: {data['user_id']}")  # Logging adding item for user ID
    data['purchase_history'] = []
    result = mongo.db.items.insert_one(data)
    data['_id'] = str(result.inserted_id)
    return jsonify(data)

@app.route('/items/<id>', methods=['PUT'])
def update_item(id):
    if 'user_id' not in session:
        return jsonify({'message': 'Unauthorized access'}), 401

    data = request.json
    # Remove the '_id' field if present to avoid trying to modify it
    data.pop('_id', None)
    print(f"Updating item with ID: {id} for user_id: {session['user_id']}")  # Logging updating item
    mongo.db.items.update_one({'_id': ObjectId(id)}, {'$set': data})
    data['_id'] = id
    return jsonify(data)

@app.route('/items/weekly', methods=['POST'])
def submit_weekly_list():
    if 'user_id' not in session:
        return jsonify({'message': 'Unauthorized access'}), 401

    data = request.json
    date = data.get('date')
    user_id = session['user_id']
    if date:
        now = datetime.fromisoformat(date).replace(tzinfo=None)
    else:
        now = datetime.now().replace(tzinfo=None)
    submitted_item_names = {item['name'] for item in data['items']}

    print(f"Submitting weekly list for user_id: {user_id} with items: {submitted_item_names} and date: {now}")  # Logging weekly list submission

    for item_name in submitted_item_names:
        existing_item = mongo.db.items.find_one({'user_id': user_id, 'name': item_name})
        if existing_item:
            print(f"Updating existing item: {item_name} for user_id: {user_id}")
            purchase_history_entry = {'date': now, 'purchased': True}
            mongo.db.items.update_one(
                {'_id': existing_item['_id']},
                {'$push': {'purchase_history': purchase_history_entry}}
            )
        else:
            print(f"Adding new item: {item_name} for user_id: {user_id}")
            new_item = {
                'user_id': user_id,
                'name': item_name,
                'date': date,
                'purchase_history': [{'date': now, 'purchased': True}]
            }
            mongo.db.items.insert_one(new_item)
    return jsonify({'message': 'Weekly list submitted'})

@app.route('/autogenerate', methods=['GET'])
def autogenerate_list():
    if 'user_id' not in session:
        return jsonify({'message': 'Unauthorized access'}), 401

    user_id = session['user_id']
    items = list(mongo.db.items.find({'user_id': user_id}))
    now = request.args.get('date', default=datetime.now().isoformat())
    now = pd.to_datetime(now).tz_localize(None)  # Ensure timezone-naive
    print(f"Simulated date for auto-generation: {now} for user_id: {user_id}")  # Logging simulated date
    generated_list = []

    for item in items:
        purchase_history = item.get('purchase_history', [])
        if purchase_history:
            df = pd.DataFrame(purchase_history)
            try:
                df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.tz_localize(None)  # Ensure timezone-naive
            except Exception as e:
                print(f"Error parsing dates: {e}")
                continue
            df = df[df['purchased'] == True]  # Only consider purchased items
            df = df.sort_values('date')
            if not df.empty:
                df['days_between'] = df['date'].diff().dt.days.fillna(0).astype(int)
                avg_days_between = df['days_between'][1:].mean()  # Ignore the first NaN value
                if pd.isna(avg_days_between) or avg_days_between == 0:
                    avg_days_between = 1  # Default to 1 day if no valid average is found
                last_purchase_date = df['date'].max()
                days_since_last = (now - last_purchase_date).days

                # Debugging logs
                print(f"Item: {item['name']}")
                print(f"Avg days between: {avg_days_between}")
                print(f"Last purchase date: {last_purchase_date}")
                print(f"Days since last purchase: {days_since_last}")

                if days_since_last >= avg_days_between:
                    generated_list.append(item['name'])

    print(f"Auto-generated list for user_id: {user_id}: {generated_list}")  # Logging auto-generated list
    return jsonify({'generated_list': generated_list})

@app.route('/items/confirm', methods=['POST'])
def confirm_purchases():
    if 'user_id' not in session:
        return jsonify({'message': 'Unauthorized access'}), 401

    data = request.json
    date = data.get('date')
    user_id = session['user_id']
    if date:
        now = datetime.fromisoformat(date).replace(tzinfo=None)
    else:
        now = datetime.now().replace(tzinfo=None)
    confirmed_item_names = set(data['items'])

    print(f"Confirming purchases for user_id: {user_id} with items: {confirmed_item_names} on date: {now}")  # Logging confirming purchases

    for item in mongo.db.items.find({'user_id': user_id}):
        if item['name'] in confirmed_item_names:
            mongo.db.items.update_one(
                {'_id': item['_id']},
                {'$push': {'purchase_history': {'date': now, 'purchased': True}}}
            )

    return jsonify({'message': 'Purchases confirmed'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)