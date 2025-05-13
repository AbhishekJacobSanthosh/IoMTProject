from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from web3 import Web3
from eth_account.messages import encode_defunct
from functools import wraps
import datetime
import time
import json
import os
import secrets
import atexit

# Import system components
from system import HealthMonitoringSystem

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config["TEMPLATES_AUTO_RELOAD"] = True  # Ensure templates are not cached
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0  # Disable caching for static files

# MongoDB Configuration
# MongoDB Configuration
app.config["MONGO_URI"] = "mongodb://localhost:27017/iomt_blockchain_db"
mongo = PyMongo(app)

# Explicitly create collections if they don't exist
db = mongo.db
collection_names = db.list_collection_names()
if "patients" not in collection_names:
    db.create_collection("patients")
if "health_records" not in collection_names:
    db.create_collection("health_records")
if "blockchain" not in collection_names:
    db.create_collection("blockchain")

# MongoDB collections
patients_collection = mongo.db.patients
health_records_collection = mongo.db.health_records
blockchain_collection = mongo.db.blockchain

# Create indexes for faster lookups
# Create indexes for faster lookups
try:
    # Use partial index for username to allow null values
    patients_collection.create_index("username", 
                                   unique=True, 
                                   partialFilterExpression={"username": {"$type": "string"}})
    
    # Use partial index for patient_id
    patients_collection.create_index("patient_id", 
                                   unique=True,
                                   partialFilterExpression={"patient_id": {"$type": "string"}})
    
    # Use partial index for user_id
    patients_collection.create_index("user_id", 
                                   unique=True,
                                   partialFilterExpression={"user_id": {"$exists": True}})
    
    # Keep sparse index for eth_address
    patients_collection.create_index("eth_address", sparse=True)
    
    print("MongoDB indexes created successfully")
except Exception as e:
    print(f"Error creating MongoDB indexes: {e}")



# Print confirmation
print(f"MongoDB connected successfully. Database: {mongo.db.name}")
print(f"Collections: {mongo.db.list_collection_names()}")


# Web3 configuration for Ethereum interaction
web3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))  # For local Ganache
# For production with Infura: web3 = Web3(Web3.HTTPProvider('https://mainnet.infura.io/v3/YOUR_INFURA_KEY'))

# Store nonces for MetaMask authentication
metamask_nonces = {}

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize the health monitoring system
system = HealthMonitoringSystem(mongo)

# Admin users (stored in memory for simplicity)
admin_users = {
    'admin': {
        'username': 'admin',
        'password': 'admin123',
        'role': 'admin',
        'id': 1
    }
}

# User model for Flask-Login
class User(UserMixin):
    def __init__(self, user_data):
        self.id = user_data['id']
        self.username = user_data['username']
        self.password = user_data['password']
        self.role = user_data['role']
        if 'patient_id' in user_data:
            self.patient_id = user_data['patient_id']

@login_manager.user_loader
def load_user(user_id):
    # Check admin users
    for user in admin_users.values():
        if user['id'] == int(user_id):
            return User(user)
    
    # Check patient users from MongoDB
    patient = patients_collection.find_one({'user_id': int(user_id)})
    if patient:
        user_data = {
            'id': patient['user_id'],
            'username': patient['username'],
            'password': patient['password'],
            'role': 'patient',
            'patient_id': patient['patient_id']
        }
        return User(user_data)
    
    return None


# Role-based access control decorator
def role_required(*roles):
    def wrapper(func):
        @wraps(func)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                flash("You don't have permission to access this resource.", "danger")
                return redirect(url_for("login"))
            return func(*args, **kwargs)
        return decorated_view
    return wrapper

# Custom filter for timestamp conversion
@app.template_filter('timestamp_to_date')
def timestamp_to_date(timestamp):
    return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

# Load patient data from MongoDB
def load_patient_data():
    patients = {}
    for patient in patients_collection.find():
        patient_id = patient.get('patient_id')
        if patient_id:
            patients[patient_id] = {
                'username': patient.get('username', ''),
                'password': patient.get('password', ''),
                'user_id': patient.get('user_id', 0),
                'eth_address': patient.get('eth_address', ''),
                'records': patient.get('records', [])
            }
    return patients

# Save patient data to MongoDB
def save_patient_data(data):
    try:
        for patient_id, patient_info in data.items():
            # Check if patient exists
            existing_patient = patients_collection.find_one({'patient_id': patient_id})
            if existing_patient:
                # Update existing patient
                patients_collection.update_one(
                    {'patient_id': patient_id},
                    {'$set': patient_info}
                )
            else:
                # Insert new patient
                patient_info['patient_id'] = patient_id
                patients_collection.insert_one(patient_info)
        return True
    except Exception as e:
        print(f"Error saving patient data: {e}")
        return False

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('about'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('about'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Check admin users (kept in memory for security)
        if username in admin_users:
            user_data = admin_users[username]
            if user_data['password'] == password:
                user = User(user_data)
                login_user(user)
                flash(f'Welcome, {username}!', 'success')
                return redirect(url_for('about'))
        
        # Check patient users from MongoDB
        patient = patients_collection.find_one({'username': username})
        if patient and patient.get('password') == password:
            # Convert MongoDB document to User object
            user_data = {
                'id': patient.get('user_id'),
                'username': username,
                'password': password,
                'role': 'patient',
                'patient_id': patient.get('patient_id')
            }
            user = User(user_data)
            login_user(user)
            
            # Update last login timestamp
            patients_collection.update_one(
                {'username': username},
                {'$set': {'last_login': datetime.datetime.now()}}
            )
            
            flash(f'Welcome, Patient {username}!', 'success')
            return redirect(url_for('about'))
        
        flash('Invalid username or password', 'danger')
    
    return render_template('login.html')


@app.route('/login/admin', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('about'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Check admin users only
        if username in admin_users:
            user_data = admin_users[username]
            if user_data['password'] == password:
                user = User(user_data)
                login_user(user)
                flash(f'Welcome, Administrator {username}!', 'success')
                return redirect(url_for('about'))
        
        flash('Invalid admin credentials', 'danger')
    
    return render_template('admin_login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # Get blockchain data
    if current_user.role == 'patient':
        # For patients, only show their own data
        blockchain_data = system.get_patient_blockchain_data(current_user.patient_id)
    else:
        # For admins, show all data
        blockchain_data = system.get_blockchain_data()
    
    # Get latest data (if available)
    latest_data = None
    alerts = []
    if blockchain_data:
        latest_data = blockchain_data[-1]['data']
        alerts = latest_data.get('alerts', [])
    
    return render_template(
        'dashboard.html', 
        blocks=blockchain_data, 
        latest_data=latest_data, 
        alerts=alerts
    )

@app.route('/add_data')
@login_required
@role_required('admin')
def add_data():
    # Generate new health data and add to blockchain
    new_block, alerts, raw_data = system.process_health_data()
    
    flash('New health data generated and added to blockchain', 'success')
    return redirect(url_for('dashboard'))

@app.route('/patient/<patient_id>')
@login_required
def patient_history(patient_id):
    # Check if patient user is trying to access another patient's data
    if current_user.role == 'patient':
        if not hasattr(current_user, 'patient_id') or current_user.patient_id != patient_id:
            flash("You can only view your own medical history.", "danger")
            return redirect(url_for('dashboard'))
    
    # Check if patient exists in MongoDB
    patient = patients_collection.find_one({'patient_id': patient_id})
    if not patient:
        flash('Patient not found!', 'danger')
        return redirect(url_for('patients'))
    
    # Get patient's medical history
    history = system.view_medical_history(patient_id)
    
    return render_template('patient_history.html', patient_id=patient_id, history=history)

@app.route('/patients')
@login_required
def patients():
    # If patient, only show their own record
    if current_user.role == 'patient':
        if hasattr(current_user, 'patient_id'):
            patients = [current_user.patient_id]
        else:
            patients = []
    else:
        # Get all patients (for admin)
        patients = [p['patient_id'] for p in patients_collection.find()]
        
    return render_template('patients.html', patients=patients)

@app.route('/blockchain')
@login_required
@role_required('admin')
def blockchain_view():
    # Get blockchain data
    blockchain_data = system.get_blockchain_data()
    patients = system.get_all_patients()
    is_valid = system.blockchain.is_chain_valid()
    
    return render_template(
        'blockchain_view.html', 
        blockchain_data=blockchain_data, 
        patients=patients, 
        is_valid=is_valid
    )

@app.route('/register_patient', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def register_patient():
    if request.method == 'POST':
        # Get form data
        patient_id = request.form['patient_id']
        username = request.form['username']
        password = request.form['password']
        eth_address = request.form.get('eth_address', '')  # Optional field
        heart_rate = int(request.form['heart_rate'])
        systolic = int(request.form['systolic'])
        diastolic = int(request.form['diastolic'])
        body_temp = float(request.form['body_temp'])
        spo2 = int(request.form['spo2'])
        glucose = int(request.form['glucose'])
        
        # Check if patient ID or username already exists
        existing_patient = patients_collection.find_one({
            '$or': [
                {'patient_id': patient_id},
                {'username': username}
            ]
        })
        
        if existing_patient:
            if existing_patient.get('patient_id') == patient_id:
                flash('Patient ID already exists!', 'danger')
            else:
                flash('Username already taken!', 'danger')
            return redirect(url_for('register_patient'))
        
        # Generate a unique user ID for the patient
        user_id = max([admin_users[user]['id'] for user in admin_users]) + 1
        existing_patients = list(patients_collection.find())
        if existing_patients:
            for patient in existing_patients:
                if 'user_id' in patient and patient['user_id'] >= user_id:
                    user_id = patient['user_id'] + 1
        
        # Add patient to MongoDB
        # Add patient to MongoDB
        new_patient = {
            'patient_id': patient_id,
            'username': username,
            'password': password,
            'user_id': user_id,
            'eth_address': eth_address.lower() if eth_address else '',  # Store in lowercase
            'records': [],
            'created_at': datetime.datetime.now()
        }

        
        # Insert with explicit error handling
        try:
            result = patients_collection.insert_one(new_patient)
            print(f"Patient inserted with ID: {result.inserted_id}")
            
            # Verify insertion
            inserted_patient = patients_collection.find_one({'_id': result.inserted_id})
            if not inserted_patient:
                raise Exception("Patient was not inserted properly")
                
            print(f"Patient verified in database: {inserted_patient['patient_id']}")
        except Exception as e:
            print(f"Error inserting patient: {e}")
            flash(f'Error registering patient: {e}', 'danger')
            return redirect(url_for('register_patient'))
        
        # Create initial health data
        custom_data = {
            'patient_id': patient_id,
            'heart_rate': heart_rate,
            'blood_pressure': (systolic, diastolic),
            'body_temp': body_temp,
            'spo2': spo2,
            'glucose': glucose,
            'timestamp': time.time(),
            'readable_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Process the data and add to blockchain
        try:
            new_block, alerts, raw_data = system.process_health_data(custom_data)
            
            # Save health record to MongoDB with explicit error handling
            health_record = custom_data.copy()
            health_record['block_hash'] = new_block.hash
            health_record['created_at'] = datetime.datetime.now()
            
            record_result = health_records_collection.insert_one(health_record)
            print(f"Health record inserted with ID: {record_result.inserted_id}")
            
            # Update patient record with reference to health record
            patients_collection.update_one(
                {'patient_id': patient_id},
                {'$push': {'records': str(record_result.inserted_id)}}
            )
            
            flash('Patient registered successfully!', 'success')
        except Exception as e:
            print(f"Error processing health data: {e}")
            flash(f'Patient registered but error adding health data: {e}', 'warning')
            
        return redirect(url_for('dashboard'))
        
    return render_template('register_patient.html')

@app.route('/api/check_eth_address')
def check_eth_address():
    """Check if a patient exists with a given Ethereum address"""
    address = request.args.get('address')
    if not address:
        return jsonify({'error': 'Address is required'}), 400
    
    # Find patient with this Ethereum address (case-insensitive)
    patient = patients_collection.find_one({'eth_address': {'$regex': f'^{address}$', '$options': 'i'}})
    
    if patient:
        return jsonify({
            'exists': True,
            'patient_id': patient.get('patient_id'),
            'username': patient.get('username')
        })
    else:
        # Check all patients in database to debug
        all_patients = list(patients_collection.find({}, {'patient_id': 1, 'eth_address': 1}))
        
        return jsonify({
            'exists': False,
            'all_patients': [{
                'patient_id': p.get('patient_id'),
                'eth_address': p.get('eth_address')
            } for p in all_patients]
        })


@app.route('/edit_patient/<patient_id>', methods=['GET', 'POST'])
@login_required
def edit_patient(patient_id):
    # Check if patient user is trying to edit another patient's data
    if current_user.role == 'patient':
        if not hasattr(current_user, 'patient_id') or current_user.patient_id != patient_id:
            flash("You can only edit your own data.", "danger")
            return redirect(url_for('dashboard'))
    
    # Check if patient exists in MongoDB
    patient = patients_collection.find_one({'patient_id': patient_id})
    if not patient:
        flash('Patient not found!', 'danger')
        return redirect(url_for('patients'))
    
    # Get patient history
    patient_history = system.view_medical_history(patient_id)
    
    # Get the most recent data for this patient
    latest_data = patient_history[0] if patient_history else None
    
    if request.method == 'POST':
        # Get form data
        heart_rate = int(request.form['heart_rate'])
        systolic = int(request.form['systolic'])
        diastolic = int(request.form['diastolic'])
        body_temp = float(request.form['body_temp'])
        spo2 = int(request.form['spo2'])
        glucose = int(request.form['glucose'])
        
        # Create updated patient data
        custom_data = {
            'patient_id': patient_id,
            'heart_rate': heart_rate,
            'blood_pressure': (systolic, diastolic),
            'body_temp': body_temp,
            'spo2': spo2,
            'glucose': glucose,
            'timestamp': time.time(),
            'readable_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Process the data and add to blockchain
        new_block, alerts, raw_data = system.process_health_data(custom_data)
        
        flash('Patient data updated successfully!', 'success')
        return redirect(url_for('patient_history', patient_id=patient_id))
    
    # Handle case where latest_data is None
    if latest_data is None:
        # Create default data
        latest_data = {
            'heart_rate': 75,
            'blood_pressure': (120, 80),
            'body_temp': 36.6,
            'spo2': 98,
            'glucose': 100
        }
        
    return render_template('edit_patient.html', patient_id=patient_id, patient_data=latest_data)

@app.route('/remove_patient/<patient_id>', methods=['POST'])
@login_required
@role_required('admin')
def remove_patient(patient_id):
    # Remove patient from MongoDB
    result = patients_collection.delete_one({'patient_id': patient_id})
    
    if result.deleted_count > 0:
        # Also remove from system's patients dictionary
        if system.remove_patient(patient_id):
            flash(f'Patient {patient_id} removed successfully!', 'success')
        else:
            flash(f'Patient removed from database but not from blockchain!', 'warning')
    else:
        flash(f'Failed to remove patient {patient_id}!', 'danger')
    
    return redirect(url_for('patients'))

@app.route('/api/get_nonce')
def get_nonce():
    """Generate a nonce for MetaMask authentication"""
    address = request.args.get('address')
    print(f"Nonce requested for address: {address}")
    
    if not address:
        return jsonify({'error': 'Address is required'}), 400
    
    # Generate a random nonce
    nonce = secrets.token_hex(16)
    metamask_nonces[address] = nonce
    print(f"Generated nonce for {address}: {nonce}")
    
    return jsonify({'nonce': nonce})


@app.route('/api/verify_signature', methods=['POST'])
def verify_signature():
    """Verify a MetaMask signature"""
    data = request.json
    address = data.get('address')
    signature = data.get('signature')
    nonce = data.get('nonce')  # Get nonce from request
    
    print(f"Verifying signature for address: {address}")
    print(f"Signature: {signature}")
    
    if not address or not signature:
        print("Missing address or signature")
        return jsonify({'authenticated': False, 'error': 'Address and signature are required'}), 400
    
    # Get the nonce for this address if not provided in request
    if not nonce:
        nonce = metamask_nonces.get(address)
    
    if not nonce:
        print("No nonce found for this address")
        return jsonify({'authenticated': False, 'error': 'No nonce found for this address'}), 400
    
    # Verify the signature
    try:
        message = f"I am signing my one-time nonce: {nonce}"
        print(f"Message that was signed: {message}")
        
        message_hash = encode_defunct(text=message)
        recovered_address = web3.eth.account.recover_message(message_hash, signature=signature)
        
        print(f"Recovered address: {recovered_address}")
        print(f"Original address: {address}")
        
        # Check if the recovered address matches the claimed address (case-insensitive)
        if recovered_address.lower() == address.lower():
            print("Signature verified successfully!")
            
            # Find patient with this Ethereum address (case-insensitive)
            patient = patients_collection.find_one({'eth_address': {'$regex': f'^{address}$', '$options': 'i'}})
            print(f"Patient lookup result: {patient}")
            
            if patient:
                # Create a session for this user
                user_data = {
                    'id': patient.get('user_id'),
                    'username': patient.get('username'),
                    'password': patient.get('password'),
                    'role': 'patient',
                    'patient_id': patient.get('patient_id')
                }
                
                print(f"Creating user session for: {user_data['username']}")
                user = User(user_data)
                login_user(user)
                print(f"User logged in: {current_user.is_authenticated}")
                
                # Clear the nonce
                if address in metamask_nonces:
                    del metamask_nonces[address]
                
                return jsonify({'authenticated': True})
            else:
                print(f"No patient found with Ethereum address: {address}")
                # Check all patients in database to debug
                all_patients = list(patients_collection.find({}, {'patient_id': 1, 'eth_address': 1}))
                print(f"All patients in database: {all_patients}")
                
                return jsonify({'authenticated': False, 'error': 'No patient linked to this Ethereum address'})
        else:
            print("Signature verification failed - addresses don't match")
            return jsonify({'authenticated': False, 'error': 'Invalid signature'})
    except Exception as e:
        print(f"Error during signature verification: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'authenticated': False, 'error': str(e)})



@app.route('/api/health_data', methods=['GET'])
@login_required
@role_required('admin')
def api_health_data():
    # API endpoint to get health data
    blockchain_data = system.get_blockchain_data()
    return jsonify(blockchain_data)

@app.route('/api/generate_data', methods=['POST'])
@login_required
@role_required('admin')
def api_generate_data():
    # API endpoint to generate new data
    new_block, alerts, raw_data = system.process_health_data()
    return jsonify({
        'success': True,
        'block_index': new_block.index,
        'data': raw_data,
        'alerts': alerts
    })

# Register function to save data when application shuts down
@atexit.register
def save_data_on_shutdown():
    print("Saving all data before shutdown...")
    system.save_state()
    print("Data saved successfully")

if __name__ == '__main__':
    # Only generate sample data if no blockchain data exists
    if not system.get_blockchain_data():
        print("No existing data found, generating sample data...")
        for _ in range(5):
            system.process_health_data()
    else:
        print("Existing data found, skipping sample data generation")
    
    # Run the Flask app
    app.run(debug=True)
