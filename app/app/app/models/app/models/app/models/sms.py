from app import db
from datetime import datetime

class SMSRange(db.Model):
    __tablename__ = 'sms_ranges'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(50))
    prefix = db.Column(db.String(20))
    total_numbers = db.Column(db.Integer, default=0)
    price = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    numbers = db.relationship('SMSNumber', backref='range', lazy='dynamic')
    
    def get_available_count(self):
        return self.numbers.filter_by(is_reserved=False, is_active=True).count()
        
    def get_reserved_count(self):
        return self.numbers.filter_by(is_reserved=True).count()

class SMSNumber(db.Model):
    __tablename__ = 'sms_numbers'
    
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(20), nullable=False)
    range_id = db.Column(db.Integer, db.ForeignKey('sms_ranges.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_reserved = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    reserved_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'number': self.number,
            'range_id': self.range_id,
            'user_id': self.user_id,
            'is_reserved': self.is_reserved,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class SMSCDR(db.Model):
    __tablename__ = 'sms_cdr'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    sender = db.Column(db.String(20))
    recipient = db.Column(db.String(20))
    message = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    provider = db.Column(db.String(50))
    cost = db.Column(db.Float, default=0.0)
    error_message = db.Column(db.Text)
    sms_type = db.Column(db.String(20), default='outgoing')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='sms_records')
    
    def to_dict(self):
        return {
            'id': self.id,
            'sender': self.sender,
            'recipient': self.recipient,
            'message': self.message,
            'status': self.status,
            'cost': self.cost,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
