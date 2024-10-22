from flask import Blueprint, render_template
from flask_login import login_required
from ..models import TestResult, LearnTestResult
from ..utils import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@admin_required
def admin_panel():
    test_results = TestResult.query.order_by(TestResult.timestamp.desc()).all()
    learn_test_results = LearnTestResult.query.order_by(LearnTestResult.completed_at.desc()).all()
    return render_template(
        'admin/admin_panel.html',
        test_results=test_results,
        learn_test_results=learn_test_results
    )
