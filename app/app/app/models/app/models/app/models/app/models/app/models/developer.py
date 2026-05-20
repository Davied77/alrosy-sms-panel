from app import db
from datetime import datetime
import re

class StaticAsset(db.Model):
    __tablename__ = 'static_assets'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True)
    asset_type = db.Column(db.String(20))
    content = db.Column(db.Text)
    file_path = db.Column(db.String(500))
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def slugify(name):
        return re.sub(r'[^\w\-]', '', name.lower().replace(' ', '-'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'asset_type': self.asset_type,
            'is_published': self.is_published
        }
