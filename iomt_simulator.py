import random
import time
import datetime

class IoMTDeviceSimulator:
    @staticmethod
    def generate_health_data():
        """Generate simulated health data from IoMT devices"""
        return {
            'patient_id': f"PAT{random.randint(1000,9999)}",
            'heart_rate': random.randint(50, 120),
            'blood_pressure': (random.randint(80, 160), random.randint(50, 100)),
            'body_temp': round(random.uniform(35.5, 39.5), 1),
            'spo2': random.randint(88, 100),
            'glucose': random.randint(70, 180),
            'timestamp': time.time(),
            'readable_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
