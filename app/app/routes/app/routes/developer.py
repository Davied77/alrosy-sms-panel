from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.models.developer import StaticAsset
from app import db
from functools import wraps

developer_bp = Blueprint('developer', __name__)

def dev_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_developer():
            return jsonify({'error': 'Developer access required'}), 403
        return f(*args, **kwargs)
    return decorated

@developer_bp.route('/')
@login_required
@dev_required
def index():
    assets = StaticAsset.query.all()
    return render_template('developer/index.html', assets=assets)

@developer_bp.route('/upload', methods=['POST'])
@login_required
@dev_required
def upload():
    file = request.files.get('file')
    if file:
        content = file.read().decode('utf-8')
        asset = StaticAsset(name=file.filename, slug=StaticAsset.slugify(file.filename), asset_type='page', content=content)
        db.session.add(asset)
        db.session.commit()
        return jsonify({'success': True, 'slug': asset.slug})
    return jsonify({'error': 'No file'}), 400

@developer_bp.route('/pages')
@login_required
@dev_required
def pages_list():
    assets = StaticAsset.query.filter_by(asset_type='page').all()
    return render_template('developer/pages.html', assets=assets)

@developer_bp.route('/page/<slug>')
def page_view(slug):
    asset = StaticAsset.query.filter_by(slug=slug, is_published=True).first_or_404()
    return asset.content
