from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import User, TestResult, LearnTestResult, Vocabulary
from app.utils import admin_required
from app import db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@admin_required
def admin_panel():
    test_results = TestResult.query.order_by(TestResult.timestamp.desc()).all()
    learn_test_results = LearnTestResult.query.order_by(LearnTestResult.completed_at.desc()).all()
    users = User.query.all()  # Fetch all users
    return render_template(
        'admin/admin_panel.html',
        test_results=test_results,
        learn_test_results=learn_test_results,
        users=users
    )

@admin_bp.route('/users/promote/<int:user_id>', methods=['POST'])
@admin_required
def promote_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash(f'User {user.username} is already an admin.', 'info')
    else:
        user.is_admin = True
        db.session.commit()
        flash(f'User {user.username} has been promoted to admin.', 'success')
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/users/demote/<int:user_id>', methods=['POST'])
@admin_required
def demote_user(user_id):
    user = User.query.get_or_404(user_id)
    if not user.is_admin:
        flash(f'User {user.username} is not an admin.', 'info')
    elif user.id == current_user.id:
        flash('You cannot demote yourself.', 'danger')
    else:
        user.is_admin = False
        db.session.commit()
        flash(f'User {user.username} has been demoted to regular user.', 'success')
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
    else:
        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.username} has been deleted.', 'success')
    return redirect(url_for('admin.admin_panel'))
