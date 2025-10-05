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


# DATABASE CONFIGURATION

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


# ML MODEL LOADING

try:
    with open('rf2_model.pkl', 'rb') as f:
        model = pickle.load(f)  # This should be your pipeline from the notebook
    print("✅ Model loaded successfully!")
    print(f"Model type: {type(model)}")
except FileNotFoundError:
    print("⚠️ Model file not found. Please ensure rf_model.pkl exists.")
    model = None

# Expected feature columns in the exact order from your training data
EXPECTED_COLUMNS = [
    'Age_band_of_driver', 'Sex_of_driver', 'Educational_level',
    'Vehicle_driver_relation', 'Driving_experience', 'Type_of_vehicle',
    'Area_accident_occured', 'Lanes_or_Medians', 'Types_of_Junction',
    'Road_surface_type', 'Light_conditions', 'Weather_conditions',
    'Type_of_collision', 'Number_of_vehicles_involved', 'Vehicle_movement',
    'Pedestrian_movement', 'Cause_of_accident'
]

# Value mappings to normalize input (frontend -> dataset format)
VALUE_MAPPINGS = {
    'Age_band_of_driver': {
        '18-30': '18-30',
        '31-50': '31-50', 
        'under 18': 'under 18',
        'over 51': 'over 51',
        'unknown': 'unknown'
    },
    'Sex_of_driver': {
        'male': 'male',
        'female': 'female',
        'unknown': 'unknown'
    },
    'Educational_level': {
        'above high school': 'above high school',
        'junior high school': 'junior high school',
        'elementary school': 'elementary school',
        'high school': 'high school',
        'unknown': 'unknown',
        'illiterate': 'illiterate',
        'writing & reading': 'writing & reading'
    },
    'Vehicle_driver_relation': {
        'employee': 'employee',
        'owner': 'owner',
        'other': 'other'
    },
    'Driving_experience': {
        '1-2yr': '1-2yr',
        '2-5yr': '2-5yr',
        '5-10yr': '5-10yr',
        'above 10yr': 'above 10yr',
        'below 1yr': 'below 1yr',
        'no licence': 'no licence',
        'unknown': 'unknown'
    },
    'Type_of_vehicle': {
        'car': 'car',
        'automobile': 'car',
        'bus': 'bus',
        'public': 'bus',
        'lorry': 'lorry',
        'truck': 'lorry',
        'motorcycle': 'motorcycle',
        'mootorbike': 'mootorbike',
        'three_wheeler': 'three_wheeler',
        'three wheeler': 'three_wheeler',
        'bajaj': 'three_wheeler',
        'bicycle': 'bicycle',
        'other': 'other'
    },
    'Area_accident_occured': {
        'residential areas': 'residential areas',
        'office areas': 'office areas',
        'recreational areas': 'recreational areas',
        'industrial areas': 'industrial areas',
        'school areas': 'school areas',
        'market areas': 'market areas',
        'church areas': 'church areas',
        'hospital areas': 'hospital areas',
        'rural village areas': 'rural village areas',
        'outside rural areas': 'outside rural areas',
        'other': 'other',
        'unknown': 'unknown'
    },
    'Lanes_or_Medians': {
        'undivided two way': 'undivided two way',
        'one way': 'one way',
        'two-way (divided with broken lines road marking)': 'two-way (divided with broken lines road marking)',
        'two-way (divided with solid lines road marking)': 'two-way (divided with solid lines road marking)',
        'double carriageway (median)': 'double carriageway (median)',
        'other': 'other',
        'unknown': 'unknown'
    },
    'Types_of_Junction': {
        'no junction': 'no junction',
        'y shape': 'y shape',
        't shape': 't shape',
        'x shape': 'x shape',
        'crossing': 'crossing',
        'o shape': 'o shape',
        'other': 'other',
        'unknown': 'unknown'
    },
    'Road_surface_type': {
        'asphalt roads': 'asphalt roads',
        'earth roads': 'earth roads',
        'gravel roads': 'gravel roads',
        'asphalt roads with some distress': 'asphalt roads with some distress',
        'other': 'other',
        'unknown': 'unknown'
    },
    'Light_conditions': {
        'daylight': 'daylight',
        'darkness - lights lit': 'darkness - lights lit',
        'darkness - lights unlit': 'darkness - lights unlit',
        'darkness - no lighting': 'darkness - no lighting',
        'unknown': 'unknown'
    },
    'Weather_conditions': {
        'normal': 'normal',
        'raining': 'raining',
        'raining and windy': 'raining and windy',
        'cloudy': 'cloudy',
        'windy': 'windy',
        'snow': 'snow',
        'fog or mist': 'fog or mist',
        'other': 'other',
        'unknown': 'unknown'
    },
    'Type_of_collision': {
        'vehicle with vehicle collision': 'vehicle with vehicle collision',
        'collision with roadside objects': 'collision with roadside objects',
        'collision with pedestrians': 'collision with pedestrians',
        'rollover': 'rollover',
        'collision with animals': 'collision with animals',
        'collision with roadside-parked vehicles': 'collision with roadside-parked vehicles',
        'fall from vehicles': 'fall from vehicles',
        'with train': 'with train',
        'other': 'other',
        'unknown': 'unknown'
    },
    'Number_of_vehicles_involved': {
        '1': 1,
        '2': 2,
        '3': 3,
        '4': 4,
        '6': 6,
        '7': 7,
        'unknown': 'unknown'
    },
    'Vehicle_movement': {
        'going straight': 'going straight',
        'turning left': 'turning left',
        'turning right': 'turning right',
        'overtaking': 'overtaking',
        'changing lane to the left': 'changing lane to the left',
        'changing lane to the right': 'changing lane to the right',
        'u-turn': 'u-turn',
        'moving backward': 'moving backward',
        'parked': 'parked',
        'stopped': 'stopped',
        'entering a junction': 'entering a junction',
        'getting off': 'getting off',
        'waiting to go': 'waiting to go',
        'overturning': 'overturning',
        'other': 'other',
        'reversing':'reversing',
        'turnover':'turnover',
        'unknown': 'unknown'
    },
    'Pedestrian_movement': {
        'not a pedestrian': 'not a pedestrian',
        'crossing from driver\'s nearside': 'crossing from driver\'s nearside',
        'crossing from driver\'s offside': 'crossing from driver\'s offside',
        'crossing from nearside - masked by parked or stationot a pedestrianry vehicle': 'crossing from nearside - masked by parked or stationot a pedestrianry vehicle',
        'crossing from offside - masked by  parked or stationot a pedestrianry vehicle': 'crossing from offside - masked by  parked or stationot a pedestrianry vehicle',
        'standing in carriageway': 'standing in carriageway',
        'in carriageway, stationot a pedestrianry - not crossing  (standing or playing)': 'in carriageway, stationot a pedestrianry - not crossing  (standing or playing)',
        'unknown': 'unknown'
    },
    'Cause_of_accident': {
        'no distancing': 'no distancing',
        'changing lane to the left': 'changing lane to the left',
        'changing lane to the right': 'changing lane to the right',
        'overtaking': 'overtaking',
        'no priority to vehicle': 'no priority to vehicle',
        'no priority to pedestrian': 'no priority to pedestrian',
        'moving backward': 'moving backward',
        'overspeed': 'overspeed',
        'driving carelessly': 'driving carelessly',
        'driving at high speed': 'driving at high speed',
        'driving under the influence of drugs': 'driving under the influence of drugs',
        'drunk driving': 'drunk driving',
        'overloading': 'overloading',
        'getting off the vehicle improperly': 'getting off the vehicle improperly',
        'driving to the left': 'driving to the left',
        'improper parking': 'improper parking',
        'turnover': 'turnover',
        'overturning': 'overturning',
        'other': 'other',
        'unknown': 'unknown'
    }
}

SEVERITY_LABELS = {0: 'Fatal injury', 1: 'Serious Injury', 2: 'Slight Injury'}

def normalize_input_value(field_name, input_value):
    """Normalize input value to match training data format"""
    if input_value is None or input_value == '':
        return 'unknown'
    
    # Convert to lowercase for matching
    input_lower = str(input_value).lower().strip()
    
    # Get mapping for this field
    field_mapping = VALUE_MAPPINGS.get(field_name, {})
    
    # Try exact match first
    for key, value in field_mapping.items():
        if key.lower() == input_lower:
            return value
    
    # Try partial match
    for key, value in field_mapping.items():
        if input_lower in key.lower() or key.lower() in input_lower:
            return value
    
    print(f"⚠️ No match found for '{input_value}' in {field_name}, using 'unknown'")
    return 'unknown'

def prepare_input_dataframe(form_data):
    """Prepare input DataFrame in the exact format expected by the model"""
    
    # Convert form field names to expected column names
    field_name_mapping = {
        'age_band_of_driver': 'Age_band_of_driver',
        'sex_of_driver': 'Sex_of_driver',
        'educational_level': 'Educational_level',
        'vehicle_driver_relation': 'Vehicle_driver_relation',
        'driving_experience': 'Driving_experience',
        'type_of_vehicle': 'Type_of_vehicle',
        'area_accident_occured': 'Area_accident_occured',
        'lanes_or_medians': 'Lanes_or_Medians',
        'types_of_junction': 'Types_of_Junction',
        'road_surface_type': 'Road_surface_type',
        'light_conditions': 'Light_conditions',
        'weather_conditions': 'Weather_conditions',
        'type_of_collision': 'Type_of_collision',
        'number_of_vehicles_involved': 'Number_of_vehicles_involved',
        'vehicle_movement': 'Vehicle_movement',
        'pedestrian_movement': 'Pedestrian_movement',
        'cause_of_accident': 'Cause_of_accident'
    }
    
    # Prepare the data dictionary
    prepared_data = {}
    
    for form_field, expected_column in field_name_mapping.items():
        input_value = form_data.get(form_field)
        normalized_value = normalize_input_value(expected_column, input_value)
        prepared_data[expected_column] = normalized_value
        
        print(f"{form_field} -> {expected_column}: '{input_value}' -> '{normalized_value}'")
    
    # Create DataFrame with single row
    input_df = pd.DataFrame([prepared_data])
    
    # Ensure all expected columns are present in correct order
    for col in EXPECTED_COLUMNS:
        if col not in input_df.columns:
            input_df[col] = 'unknown'
            print(f"⚠️ Missing column {col}, filled with 'unknown'")
    
    # Reorder columns to match training data
    input_df = input_df[EXPECTED_COLUMNS]
    
    print(f"📊 Input DataFrame shape: {input_df.shape}")
    print(f"📊 Input DataFrame columns: {list(input_df.columns)}")
    print(f"📊 Input DataFrame values: {input_df.iloc[0].to_dict()}")
    
    return input_df


# JWT AUTHENTICATION

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


# AUTHENTICATION ROUTES

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


# ML PREDICTION ROUTES

@app.route('/')
def home():
    return render_template('/index.html')

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
        print(f"📥 Received raw data: {form_data}")
        
        # Prepare input DataFrame in the correct format
        input_df = prepare_input_dataframe(form_data)
        
        # Make prediction using the pipeline
        print("🔮 Making prediction...")
        prediction = model.predict(input_df)[0]
        prediction_proba = model.predict_proba(input_df)[0]
        
        print(f"🎯 Raw prediction: {prediction}")
        print(f"🎯 Prediction probabilities: {prediction_proba}")
        
        # Map prediction to severity label
        severity_label = SEVERITY_LABELS.get(prediction, f'Unknown ({prediction})')
        
        # Create confidence scores
        confidence_scores = {}
        for i, prob in enumerate(prediction_proba):
            severity_name = SEVERITY_LABELS.get(i, f'Class_{i}')
            confidence_scores[severity_name] = round(float(prob), 4)
        
        print(f"✅ Final prediction for user {user_id}: {severity_label}")
        print(f"📊 Confidence scores: {confidence_scores}")
        
        return jsonify({
            'prediction': severity_label,
            'severity_label': severity_label,
            'confidence': confidence_scores,
            'user_id': user_id
        })
        
    except Exception as e:
        print(f"❌ Prediction error: {str(e)}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return jsonify({
            'error': str(e), 
            'traceback': traceback.format_exc(),
            'message': 'Prediction failed. Please check server logs for details.'
        }), 500


# HEALTH CHECK

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'message': 'Combined API is running',
        'model_loaded': model is not None,
        'model_type': str(type(model)) if model else None,
        'database_connected': get_db_connection() is not None
    }), 200


# ERROR HANDLERS

@app.errorhandler(404)
def not_found(error):
    return jsonify({'message': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'message': 'Internal server error'}), 500


# RUN APPLICATION

if __name__ == '__main__':
    print("🚀 Combined Authentication & Prediction API starting...")
    print("📊 Model status:", "✅ Loaded" if model else "❌ Not loaded")
    if model:
        print(f"📊 Model type: {type(model)}")
    app.run(debug=True, host='0.0.0.0', port=5000)