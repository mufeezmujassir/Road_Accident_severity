from flask import Flask, request, render_template, jsonify
import pandas as pd
import pickle
import numpy as np

app = Flask(__name__)

# Load the trained model
try:
    with open('rf_model.pkl', 'rb') as f:
        model = pickle.load(f)
    print("Model loaded successfully!")
except FileNotFoundError:
    print("Model file not found. Please ensure rf_model.pkl exists in the same directory.")
    model = None

# Define the feature mappings for encoding
FEATURE_MAPPINGS = {
    'Age_band_of_driver': {
        '18-30': 0, '31-50': 1, 'Over 51': 2, 'Unknown': 3, 'Under 18': 4
    },
    'Sex_of_driver': {
        'Female': 0, 'Male': 1, 'Unknown': 2
    },
    'Educational_level': {
        'Elementary school': 0, 'High school': 1, 'Illiterate': 2, 'Junior high school': 3,
        'Second degree': 4, 'Unknown': 5, 'Writing & reading': 6
    },
    'Vehicle_driver_relation': {
        'Employee': 0, 'Other': 1, 'Owner': 2, 'Unknown': 3
    },
    'Driving_experience': {
        '1-2yr': 0, '2-5yr': 1, '5-10yr': 2, 'Above 10yr': 3, 'Below 1yr': 4,
        'No Licence': 5, 'Unknown': 6
    },
    'Type_of_vehicle': {
        'Automobile': 0, 'Bajaj': 1, 'Bicycle': 2, 'Lorry (11-40Q)': 3,
        'Lorry (41-100Q)': 4, 'Motorcycle': 5, 'Other': 6, 'Pick up upto 10Q': 7,
        'Public (12 seats)': 8, 'Public (13-45 seats)': 9, 'Public (> 45 seats)': 10,
        'Ridden horse': 11, 'Special vehicle': 12, 'Stationwagen': 13, 'Taxi': 14,
        'Turbo': 15
    },
    'Area_accident_occured': {
        'Church areas': 0, 'Hospital areas': 1, 'Industrial areas': 2,
        'Market areas': 3, 'Office areas': 4, 'Other': 5, 'Outside rural areas': 6,
        'Recreational areas': 7, 'Residential areas': 8, 'Rural village areas': 9,
        'Rural village areasOffice areas': 10, 'School areas': 11, 'Unknown': 12
    },
    'Lanes_or_Medians': {
        'Double carriageway (median)': 0, 'One way': 1, 'other': 2,
        'Two-way (divided with broken lines road marking)': 3,
        'Two-way (divided with solid lines road marking)': 4,
        'Undivided Two way': 5, 'Unknown': 6
    },
    'Types_of_Junction': {
        'Crossing': 0, 'No junction': 1, 'O Shape': 2, 'Other': 3,
        'T Shape': 4, 'Unknown': 5, 'X Shape': 6, 'Y Shape': 7
    },
    'Road_surface_type': {
        'Asphalt roads': 0, 'Earth roads': 1, 'Gravel roads': 2, 'Other': 3, 'Unknown': 4
    },
    'Light_conditions': {
        'Darkness - lights lit': 0, 'Darkness - lights unlit': 1,
        'Darkness - no lighting': 2, 'Daylight': 3, 'Unknown': 4
    },
    'Weather_conditions': {
        'Cloudy': 0, 'Fog or mist': 1, 'Normal': 2, 'Other': 3, 'Raining': 4,
        'Raining and Windy': 5, 'Snow': 6, 'Unknown': 7, 'Windy': 8
    },
    'Type_of_collision': {
        'Collision with animals': 0, 'Collision with pedestrians': 1,
        'Collision with roadside objects': 2, 'Collision with roadside-parked vehicles': 3,
        'Fall from vehicles': 4, 'Other': 5, 'Rollover': 6, 'Unknown': 7,
        'Vehicle with vehicle collision': 8, 'With Train': 9
    },
    'Number_of_vehicles_involved': {
        '1': 0, '2': 1, '3': 2, '4': 3, '6': 4, '7': 5
    },
    'Vehicle_movement': {
        'Entering a junction': 0, 'Getting off': 1, 'Going straight': 2,
        'Moving Backward': 3, 'Other': 4, 'Overtaking': 5, 'Parked': 6,
        'Reversing': 7, 'Stopping': 8, 'Turning left': 9, 'Turning right': 10,
        'U-Turn': 11, 'Unknown': 12, 'Waiting to go': 13
    },
    'Pedestrian_movement': {
        'Crossing from driver\'s nearside': 0, 'Crossing from driver\'s offside': 1,
        'Crossing from nearside - masked by parked or stationary vehicle': 2,
        'Crossing from offside - masked by parked or stationary vehicle': 3,
        'In carriageway, stationary - not crossing (standing or playing)': 4,
        'Not a Pedestrian': 5, 'Unknown or other': 6, 'Walking along in carriageway, back to traffic': 7,
        'Walking along in carriageway, facing traffic': 8
    },
    'Cause_of_accident': {
        'Changing lane to the left': 0, 'Changing lane to the right': 1,
        'Driving at high speed': 2, 'Driving carelessly': 3, 'Driving to the left': 4,
        'Driving under the influence of drugs': 5, 'Drunk driving': 6,
        'Getting off the vehicle improperly': 7, 'Improper parking': 8,
        'Moving Backward': 9, 'No distancing': 10, 'No priority to pedestrian': 11,
        'No priority to vehicle': 12, 'Other': 13, 'Overloading': 14,
        'Overtaking': 15, 'Overturning': 16, 'Turnover': 17, 'Unknown': 18
    }
}

# Reverse mappings for severity prediction results
SEVERITY_LABELS = {0: 'Fatal injury', 1: 'Serious Injury', 2: 'Slight Injury'}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    if model is None:
        return jsonify({'error': 'Model not loaded'}), 500
    
    try:
        # Get form data
        form_data = request.form.to_dict()
        
        # Create input array based on the feature order from your training data
        input_features = []
        
        feature_names = [
            'Age_band_of_driver', 'Sex_of_driver', 'Educational_level',
            'Vehicle_driver_relation', 'Driving_experience', 'Type_of_vehicle',
            'Area_accident_occured', 'Lanes_or_Medians', 'Types_of_Junction',
            'Road_surface_type', 'Light_conditions', 'Weather_conditions',
            'Type_of_collision', 'Number_of_vehicles_involved', 'Vehicle_movement',
            'Pedestrian_movement', 'Cause_of_accident'
        ]
        
        # Encode each feature
        for feature_name in feature_names:
            feature_value = form_data.get(feature_name)
            if feature_value in FEATURE_MAPPINGS[feature_name]:
                encoded_value = FEATURE_MAPPINGS[feature_name][feature_value]
                input_features.append(encoded_value)
            else:
                # Handle unknown values - use the 'Unknown' encoding if available
                if 'Unknown' in FEATURE_MAPPINGS[feature_name]:
                    input_features.append(FEATURE_MAPPINGS[feature_name]['Unknown'])
                else:
                    input_features.append(0)  # Default fallback
        
        # Make prediction
        input_array = np.array(input_features).reshape(1, -1)
        prediction = model.predict(input_array)[0]
        prediction_proba = model.predict_proba(input_array)[0]
        
        # Get severity label
        severity_label = SEVERITY_LABELS.get(prediction, 'Unknown')
        
        # Get confidence scores
        confidence_scores = {
            SEVERITY_LABELS[i]: round(prob * 100, 2) 
            for i, prob in enumerate(prediction_proba)
        }
        
        return jsonify({
            'prediction': int(prediction),
            'severity_label': severity_label,
            'confidence_scores': confidence_scores
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)