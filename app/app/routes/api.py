from flask import Blueprint, jsonify, request
from app.models.user import User
from app.models.sms import SMSRange, SMSNumber, SMSCDR
from app import db
from functools import wraps

api_bp = Blueprint('api', __name__)

def api_auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        user = User.query.filter_by(api_token=token).first()
        if not user or not user.is_active:
            return jsonify({'error': 'Invalid token'}), 401
        return f(user, *args, **kwargs)
    return decorated

@api_bp.route('/clients')
@api_auth_required
def get_clients(user):
    if not user.is_admin() and not user.is_agent():
        return jsonify({'error': 'Unauthorized'}), 403
    clients = User.query.filter_by(role='client').all()
    return jsonify([c.to_dict() for c in clients])

@api_bp.route('/sms-numbers')
@api_auth_required
def get_sms_numbers(user):
    numbers = SMSNumber.query.all() if user.is_admin() else SMSNumber.query.filter_by(user_id=user.id).all()
    return jsonify([n.to_dict() for n in numbers])

@api_bp.route('/sms-ranges')
@api_auth_required
def get_sms_ranges(user):
    ranges = SMSRange.query.filter_by(is_active=True).all()
    return jsonify([{'id': r.id, 'name': r.name, 'country': r.country, 'available': r.get_available_count(), 'total': r.total_numbers} for r in ranges])

@api_bp.route('/send-sms', methods=['POST'])
@api_auth_required
def send_sms(user):
    data = request.get_json()
    cdr = SMSCDR(user_id=user.id, sender=data.get('sender', 'API'), recipient=data.get('recipient'), message=data.get('message'), status='sent', cost=0.05)
    db.session.add(cdr)
    user.sms_used += 1
    db.session.commit()
    return jsonify(cdr.to_dict()), 201

@api_bp.route('/sms-cdr')
@api_auth_required
def get_sms_cdr(user):
    records = SMSCDR.query.filter_by(user_id=user.id).order_by(SMSCDR.created_at.desc()).limit(100).all()
    return jsonify([r.to_dict() for r in records])

@api_bp.route('/sms-stats')
@api_auth_required
def get_sms_stats(user):
    return jsonify(user.get_sms_stats())
