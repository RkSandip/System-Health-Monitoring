from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import psutil
import threading
import time
from datetime import datetime
import os

app = Flask(__name__)

    # Configure Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///monitor.db")
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

    #  Metadata model
class Metadata(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    environment = db.Column(db.String(80))
    location = db.Column(db.String(120))


    # Define the Alert model
class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    metric_type = db.Column(db.String(50))
    threshold = db.Column(db.Float)
    current_value = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20))  # e.g., "active" or "resolved"

    # Create the database tables
with app.app_context():
    db.create_all()


# Endpoint to get current system metrics
@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    return jsonify({'cpu': cpu, 'memory': memory, 'disk': disk})


# Endpoint to manage metadata: GET to list, POST to add metadata
@app.route('/api/metadata', methods=['GET', 'POST'])
def manage_metadata():
    if request.method == 'POST':
        data = request.get_json()
        if not data or 'name' not in data or 'environment' not in data or 'location' not in data:
            return jsonify({'error': 'Missing required fields'}), 400
        meta = Metadata(name=data['name'], environment=data['environment'], location=data['location'])
        db.session.add(meta)
        db.session.commit()
        return jsonify({'message': 'Metadata added', 'id': meta.id}), 201
    else:
        all_meta = Metadata.query.all()
        return jsonify([
            {'id': m.id, 'name': m.name, 'environment': m.environment, 'location': m.location}
            for m in all_meta
        ])


# Endpoint to get alerts
@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    alerts = Alert.query.all()
    return jsonify([
        {
            'id': a.id,
            'metric_type': a.metric_type,
            'threshold': a.threshold,
            'current_value': a.current_value,
            'timestamp': a.timestamp.isoformat(),
            'status': a.status
        }
        for a in alerts
    ])


# Background thread to monitor system metrics and trigger alerts
def monitor_system():
    with app.app_context():
        while True:
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent

            # Check CPU threshold 
            if cpu > 80:
                alert = Alert(metric_type="CPU", threshold=80, current_value=cpu, status="active")
                db.session.add(alert)
                db.session.commit()

            # Check Memory threshold
            if memory > 85:
                alert = Alert(metric_type="Memory", threshold=90, current_value=memory, status="active")
                db.session.add(alert)
                db.session.commit()

            # Check Disk threshold
            if disk < 10:
                alert = Alert(metric_type="Disk", threshold=10, current_value=disk, status="active")
                db.session.add(alert)
                db.session.commit()

            time.sleep(10)  # Wait 10 seconds before next check


# Start the background monitoring thread
monitor_thread = threading.Thread(target=monitor_system)
monitor_thread.daemon = True
monitor_thread.start()

    # Ensure app runs properly on Render
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
