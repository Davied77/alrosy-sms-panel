from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from app.models.sms import SMSCDR
from functools import wraps
from datetime import datetime

monitor_bp = Blueprint('monitor', __name__)

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated

@monitor_bp.route('/')
@login_required
@admin_required
def index():
    return render_template('monitor/index.html')

@monitor_bp.route('/status')
@login_required
@admin_required
def get_status():
    recent = SMSCDR.query.order_by(SMSCDR.created_at.desc()).limit(10).all()
    return jsonify({
        'status': 'active',
        'last_check': datetime.utcnow().isoformat(),
        'recent_messages': [r.to_dict() for r in recent]
    })
