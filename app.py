from flask import Flask, request, render_template, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import mysql.connector
from mysql.connector import Error
import pandas as pd
import pickle
import numpy as np
import os

app = Flask(__name__, template_folder='.', static_folder='.')
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
CORS(app, origins=['http://localhost:8000', 'http://127.0.0.1:8000'], supports_credentials=True)

# ========================================
# DATABASE CONFIGURATION
# ========================================
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'database': 'accident_user',
    'user': 'root',
    'password': 'Abdullah@450'
}

def get_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        print("MySQL connection successful!")
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def init_db():
    try:
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    full_name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            connection.commit()
            cursor.close()
            connection.close()
            print("Database table 'user' created successfully!")
    except Error as e:
        print(f"Error creating table: {e}")

init_db()

# ========================================
# ML MODEL LOADING
# ========================================
try:
    with open('rf1_model.pkl', 'rb') as f:
        model = pickle.load(f)
    print("✅ Model loaded successfully!")
except FileNotFoundError:
    print("⚠️ Model file not found. Please ensure rf1_model.pkl exists.")
    model = None

# ALL LOWERCASE Feature mappings based on your dataset
FEATURE_MAPPINGS = {
    'age_band_of_driver': {
        '18-30': 0, '31-50': 1, 'under 18': 2, 'over 51': 3, 'unknown': 4
    },
    'sex_of_driver': {
        'female': 0, 'male': 1, 'unknown': 2
    },
    'educational_level': {
        'above high school': 0, 
        'junior high school': 1, 
        'elementary school': 2,
        'high school': 3,
        'unknown': 4,
        'illiterate': 5,
        'writing & reading': 6
    },
    'vehicle_driver_relation': {
        'employee': 0, 'owner': 1, 'other': 2
    },
    'driving_experience': {
        '1-2yr': 0, 
        '2-5yr': 1, 
        '5-10yr': 2, 
        'above 10yr': 3,
        'below 1yr': 4, 
        'no licence': 5,
        'unknown': 6
    },
    'type_of_vehicle': {
        # Map frontend inputs to dataset values (all lowercase)
        'car': 0, 'automobile': 0,
        'bus': 1, 'public': 1,
        'lorry': 2, 'truck': 2,
        'motorcycle': 3, 'motorbike': 3, 'mootorbike': 3,
        'three_wheeler': 4, 'bajaj': 4, 'turbo': 4,
        'bicycle': 5,
        'other': 6
    },
    'area_accident_occured': {
        'residential': 0, 'residential areas': 0,
        'office areas': 1, 'office area': 1,
        'recreational areas': 2,
        'industrial areas': 3, 'industrial': 3,
        'school areas': 4, 'school area': 4,
        'market areas': 5, 'market area': 5,
        'church areas': 6, 'church area': 6,
        'hospital areas': 7, 'hospital area': 7,
        'rural village areas': 8,
        'outside rural areas': 9,
        'other': 10,
        'unknown': 11
    },
    'lanes_or_medians': {
        'undivided two way': 0, 'undivided': 0,
        'one way': 1,
        'two-way': 2, 'two-way (divided with broken lines road marking)': 2,
        'two-way (divided with solid lines road marking)': 3,
        'double carriageway (median)': 4, 'double carriageway': 4,
        'other': 5,
        'unknown': 6
    },
    'types_of_junction': {
        'no junction': 0,
        'y shape': 1,
        't shape': 2,
        'x shape': 3,
        'crossing': 4,
        'o shape': 5,
        'other': 6,
        'unknown': 7
    },
    'road_surface_type': {
        'asphalt roads': 0,
        'earth roads': 1,
        'gravel roads': 2,
        'asphalt roads with some distress': 3,
        'other': 4,
        'unknown': 5
    },
    'light_conditions': {
        'daylight': 0,
        'darkness': 1, 'darkness - lights lit': 1,
        'darkness - lights unlit': 2,
        'darkness - no lighting': 3,
        'unknown': 4
    },
    'weather_conditions': {
        'normal': 0,
        'raining': 1,
        'raining and windy': 2,
        'cloudy': 3,
        'windy': 4,
        'snow': 5,
        'fog or mist': 6,
        'other': 7,
        'unknown': 8
    },
    'type_of_collision': {
        'vehicle with vehicle collision': 0,
        'collision with roadside objects': 1, 'collision with roadside object': 1,
        'collision with pedestrians': 2,
        'rollover': 3,
        'collision with animals': 4,
        'collision with roadside-parked vehicles': 5,
        'fall from vehicles': 6,
        'with train': 7,
        'other': 8,
        'unknown': 9
    },
    'number_of_vehicles_involved': {
        '1': 0, '2': 1, '3': 2, '4': 3, '6': 4, '7': 5, 'unknown': 6
    },
    'vehicle_movement': {
        'going straight': 0,
        'turning left': 1,
        'turning right': 2,
        'overtaking': 3,
        'changing lane to the left': 4, 'changing left': 4,
        'changing lane to the right': 5, 'changing right': 5,
        'u-turn': 6, 'turnover': 6,
        'moving backward': 7, 'moving backwards': 7, 'reversing': 7,
        'parked': 8,
        'stopped': 9, 'stopping': 9,
        'entering a junction': 10,
        'getting off': 11,
        'waiting to go': 12,
        'overturning': 13,
        'other': 14,
        'unknown': 15
    },
    'pedestrian_movement': {
        'not a pedestrian': 0,
        'crossing from driver\'s nearside': 1, 'crossing from driver\'s ne': 1,
        'crossing from driver\'s offside': 2,
        'unknown': 3
    },
    'cause_of_accident': {
        'no distancing': 0,
        'changing lane to the left': 1, 'changing left': 1,
        'changing lane to the right': 2, 'changing right': 2,
        'overtaking': 3,
        'no priority to vehicle': 4, 'no priority': 4,
        'no priority to pedestrian': 5,
        'moving backward': 6, 'moving backwards': 6, 'moving back': 6,
        'overspeed': 7,
        'driving carelessly': 8,
        'driving at high speed': 9,
        'driving under the influence of drugs': 10, 'driving under': 10,
        'drunk driving': 11,
        'overloading': 12,
        'getting off the vehicle improperly': 13,
        'driving to the left': 14,
        'improper parking': 15,
        'turnover': 16,
        'overturning': 17,
        'other': 18,
        'unknown': 19
    }
}

SEVERITY_LABELS = {0: 'Fatal injury', 1: 'Serious Injury', 2: 'Slight Injury'}

# Function to normalize and find matching key
def find_match(value, mapping_dict, feature_name):
    """Find matching key in mapping dict, all converted to lowercase"""
    if value is None or value == '':
        return mapping_dict.get('unknown', 0)
    
    # Convert to lowercase and strip whitespace
    value_clean = str(value).lower().strip()
    
    # Direct match
    if value_clean in mapping_dict:
        return mapping_dict[value_clean]
    
    # Partial match for truncated values
    for key in mapping_dict:
        if value_clean in key or key in value_clean:
            return mapping_dict[key]
    
    # Log unmatched values for debugging
    print(f"⚠️ No match found for '{value}' in {feature_name}")
    print(f"   Available options: {list(mapping_dict.keys())}")
    
    # Default to unknown or 0
    return mapping_dict.get('unknown', 0)

# ========================================
# JWT AUTHENTICATION
# ========================================
def generate_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

def verify_token(token):
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload['user_id']
    except:
        return None

def require_auth(f):
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'No token provided'}), 401
        
        if token.startswith('Bearer '):
            token = token[7:]
        
        user_id = verify_token(token)
        if not user_id:
            return jsonify({'message': 'Invalid token'}), 401
        
        return f(user_id, *args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# ========================================
# AUTHENTICATION ROUTES
# ========================================
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        
        if not all([name, email, password]):
            return jsonify({'message': 'All fields are required'}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'message': 'Database connection failed'}), 500
            
        cursor = connection.cursor()
        cursor.execute('SELECT id FROM user WHERE email = %s', (email,))
        if cursor.fetchone():
            cursor.close()
            connection.close()
            return jsonify({'message': 'User already exists'}), 400
        
        hashed_password = generate_password_hash(password)
        cursor.execute(
            'INSERT INTO user (full_name, email, password) VALUES (%s, %s, %s)',
            (name, email, hashed_password)
        )
        user_id = cursor.lastrowid
        connection.commit()
        cursor.close()
        connection.close()
        
        token = generate_token(user_id)
        
        return jsonify({
            'message': 'User created successfully',
            'token': token,
            'user': {'id': user_id, 'name': name, 'email': email}
        }), 201
        
    except Exception as e:
        print(f"Registration error: {e}")
        return jsonify({'message': 'Registration failed'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not all([email, password]):
            return jsonify({'message': 'Email and password are required'}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'message': 'Database connection failed'}), 500
            
        cursor = connection.cursor()
        cursor.execute('SELECT id, full_name, email, password FROM user WHERE email = %s', (email,))
        user = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if not user or not check_password_hash(user[3], password):
            return jsonify({'message': 'Invalid credentials'}), 401
        
        token = generate_token(user[0])
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': {'id': user[0], 'name': user[1], 'email': user[2]}
        }), 200
        
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'message': 'Login failed'}), 500

@app.route('/api/logout', methods=['POST'])
@require_auth
def logout(user_id):
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/api/profile', methods=['GET'])
@require_auth
def get_profile(user_id):
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'message': 'Database connection failed'}), 500
            
        cursor = connection.cursor()
        cursor.execute('SELECT id, full_name, email, created_at FROM user WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        return jsonify({
            'id': user[0],
            'name': user[1],
            'email': user[2],
            'created_at': user[3]
        }), 200
        
    except Exception as e:
        print(f"Profile error: {e}")
        return jsonify({'message': 'Failed to get profile'}), 500

# ========================================
# ML PREDICTION ROUTES
# ========================================
@app.route('/')
def home():
    return render_template('templates/index.html')

@app.route('/predict_form')
def predict_form():
    return render_template('templates/predict_form.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

@app.route('/api/predict', methods=['POST'])
@require_auth
def predict(user_id):
    if model is None:
        return jsonify({'error': 'Model not loaded'}), 500
    
    try:
        if request.is_json:
            form_data = request.get_json()
        else:
            form_data = request.form.to_dict()
        
        print(f"📥 Prediction request from user {user_id}")
        print(f"📥 Received data: {form_data}")
        
        # Convert all field names to lowercase for consistent processing
        lowercase_form_data = {}
        for key, value in form_data.items():
            lowercase_key = key.lower()
            lowercase_form_data[lowercase_key] = value
        
        # Define feature order (all lowercase now)
        feature_names = [
            'age_band_of_driver', 'sex_of_driver', 'educational_level',
            'vehicle_driver_relation', 'driving_experience', 'type_of_vehicle',
            'area_accident_occured', 'lanes_or_medians', 'types_of_junction',
            'road_surface_type', 'light_conditions', 'weather_conditions',
            'type_of_collision', 'number_of_vehicles_involved', 'vehicle_movement',
            'pedestrian_movement', 'cause_of_accident'
        ]
        
        input_features = []
        feature_debug = {}
        missing_features = []
        
        for feature_name in feature_names:
            feature_value = lowercase_form_data.get(feature_name)
            
            if feature_value is None or feature_value == '':
                missing_features.append(feature_name)
                encoded_value = find_match(None, FEATURE_MAPPINGS[feature_name], feature_name)
            else:
                encoded_value = find_match(feature_value, FEATURE_MAPPINGS[feature_name], feature_name)
            
            input_features.append(encoded_value)
            feature_debug[feature_name] = {
                'original': feature_value, 
                'encoded': encoded_value,
                'available_options': list(FEATURE_MAPPINGS[feature_name].keys())
            }
        
        if missing_features:
            print(f"⚠️ Missing features: {missing_features}")
        
        # Ensure we have the right number of features
        if len(input_features) != len(feature_names):
            return jsonify({
                'error': f'Feature count mismatch. Expected {len(feature_names)}, got {len(input_features)}'
            }), 400
        
        input_array = np.array(input_features).reshape(1, -1)
        print(f"🔢 Input array shape: {input_array.shape}")
        print(f"🔢 Input array: {input_array}")
        
        # Make prediction
        prediction = model.predict(input_array)[0]
        prediction_proba = model.predict_proba(input_array)[0]
        
        severity_label = SEVERITY_LABELS.get(prediction, 'Unknown')
        
        confidence_scores = {
            SEVERITY_LABELS[i]: round(prob, 4)
            for i, prob in enumerate(prediction_proba)
        }
        
        print(f"✅ Prediction for user {user_id}: {severity_label}")
        
        return jsonify({
            'prediction': severity_label,
            'severity_label': severity_label,
            'confidence': confidence_scores,
            'user_id': user_id,
            'debug': {
                'input_features': input_features,
                'raw_prediction': int(prediction),
                'missing_features': missing_features,
                'feature_debug': feature_debug
            }
        })
        
    except Exception as e:
        print(f"❌ Prediction error: {str(e)}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

# ========================================
# HEALTH CHECK
# ========================================
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'message': 'Combined API is running',
        'model_loaded': model is not None,
        'database_connected': get_db_connection() is not None
    }), 200

# ========================================
# ERROR HANDLERS
# ========================================
@app.errorhandler(404)
def not_found(error):
    return jsonify({'message': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'message': 'Internal server error'}), 500

# ========================================
# RUN APPLICATION
# ========================================
if __name__ == '__main__':
    print("🚀 Combined Authentication & Prediction API starting...")
    print("📊 Model status:", "✅ Loaded" if model else "❌ Not loaded")
    app.run(debug=True, host='0.0.0.0', port=5000)