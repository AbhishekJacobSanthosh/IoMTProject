class HealthSmartContract:
    def __init__(self):
        self.thresholds = {
            'heart_rate': {'low': 60, 'high': 100},
            'blood_pressure': {'low': 90, 'high': 140},
            'body_temp': {'low': 36.0, 'high': 38.0},
            'spo2': {'low': 94, 'high': 100},
            'glucose': {'low': 70, 'high': 140}
        }

    def check_vitals(self, data):
        """Check vital signs against thresholds and generate alerts"""
        alerts = []
        
        # Check heart rate
        if 'heart_rate' in data:
            hr = data['heart_rate']
            if hr > self.thresholds['heart_rate']['high']:
                alerts.append({
                    'type': 'heart_rate',
                    'severity': 'high',
                    'message': f"High heart rate: {hr} bpm"
                })
            elif hr < self.thresholds['heart_rate']['low']:
                alerts.append({
                    'type': 'heart_rate',
                    'severity': 'low',
                    'message': f"Low heart rate: {hr} bpm"
                })
        
        # Check blood pressure
        if 'blood_pressure' in data:
            systolic = data['blood_pressure'][0]
            diastolic = data['blood_pressure'][1]
            
            if systolic > self.thresholds['blood_pressure']['high']:
                alerts.append({
                    'type': 'blood_pressure',
                    'severity': 'high',
                    'message': f"High systolic BP: {systolic} mmHg"
                })
            elif systolic < self.thresholds['blood_pressure']['low']:
                alerts.append({
                    'type': 'blood_pressure',
                    'severity': 'low',
                    'message': f"Low systolic BP: {systolic} mmHg"
                })
        
        # Check body temperature
        if 'body_temp' in data:
            temp = data['body_temp']
            if temp > self.thresholds['body_temp']['high']:
                alerts.append({
                    'type': 'body_temp',
                    'severity': 'high',
                    'message': f"High body temperature: {temp} °C"
                })
            elif temp < self.thresholds['body_temp']['low']:
                alerts.append({
                    'type': 'body_temp',
                    'severity': 'low',
                    'message': f"Low body temperature: {temp} °C"
                })
        
        # Check SpO2
        if 'spo2' in data:
            spo2 = data['spo2']
            if spo2 < self.thresholds['spo2']['low']:
                alerts.append({
                    'type': 'spo2',
                    'severity': 'low',
                    'message': f"Low oxygen saturation: {spo2}%"
                })
        
        # Check glucose
        if 'glucose' in data:
            glucose = data['glucose']
            if glucose > self.thresholds['glucose']['high']:
                alerts.append({
                    'type': 'glucose',
                    'severity': 'high',
                    'message': f"High blood glucose: {glucose} mg/dL"
                })
            elif glucose < self.thresholds['glucose']['low']:
                alerts.append({
                    'type': 'glucose',
                    'severity': 'low',
                    'message': f"Low blood glucose: {glucose} mg/dL"
                })
        
        return alerts
