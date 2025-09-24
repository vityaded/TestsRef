# Updated app/routes/reading.py with flag_modified

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from app.models import ReadingActivity, ReadingPage, UserReadingProgress
from app import db
# --- ADD THIS IMPORT ---
from sqlalchemy.orm.attributes import flag_modified
# -----------------------

# Optional: For logging instead of print
# import logging
# logger = logging.getLogger(__name__)

reading_bp = Blueprint('reading', __name__, url_prefix='/reading')

@reading_bp.route('/activities')
@login_required
def reading_tasks():
    """Displays the list of available reading activities."""
    try:
        activities = ReadingActivity.query.order_by(ReadingActivity.title.asc()).all()
        progress_records = UserReadingProgress.query.filter_by(user_id=current_user.id).all()
        progress_map = {record.activity_id: record for record in progress_records}

        activity_cards = []
        for activity in activities:
            total_pages = len(activity.pages or [])
            progress = progress_map.get(activity.id)
            unlocked_pages = []

            if progress and isinstance(progress.unlocked_pages, list):
                for page_value in progress.unlocked_pages:
                    try:
                        page_number = int(page_value)
                    except (TypeError, ValueError):
                        continue
                    unlocked_pages.append(page_number)

            if total_pages > 0:
                if 1 not in unlocked_pages:
                    unlocked_pages.append(1)
                unlocked_pages = sorted({page for page in unlocked_pages if page >= 1})
                unlocked_pages = [page for page in unlocked_pages if page <= total_pages]
            else:
                unlocked_pages = []

            unlocked_count = len(unlocked_pages)
            effective_unlocked = min(unlocked_count, total_pages) if total_pages else 0
            completion_ratio = 100 if total_pages == 0 else int(round((effective_unlocked / total_pages) * 100))
            completed = total_pages > 0 and completion_ratio >= 100

            if completed and total_pages:
                next_page = total_pages
            else:
                next_page = unlocked_pages[-1] if unlocked_pages else 1
            next_page = max(1, min(next_page, total_pages or 1))

            activity_cards.append({
                'activity': activity,
                'total_pages': total_pages,
                'pages_unlocked': effective_unlocked,
                'pages_remaining': max(total_pages - effective_unlocked, 0),
                'completion_ratio': completion_ratio,
                'completed': completed,
                'next_page': next_page
            })

        activity_cards.sort(key=lambda item: (item['activity'].title or '').lower())
        return render_template('reading/reading_tasks.html', activity_cards=activity_cards)
    except Exception:
        current_app.logger.exception(
            "reading.reading_tasks: failed to load activities",
        )
        flash("Error loading reading activities.", "danger")
        return redirect(url_for('main.index'))

@reading_bp.route('/activity/<int:activity_id>/page/<int:page_number>', methods=['GET'])
@login_required
def reading_activity(activity_id, page_number):
    """Displays a specific page of a reading activity if unlocked."""
    current_app.logger.debug(
        "reading.reading_activity: loading page %s for activity %s",
        page_number,
        activity_id,
    )
    try:
        activity = ReadingActivity.query.get_or_404(activity_id)
        page = ReadingPage.query.filter_by(activity_id=activity_id, page_number=page_number).first_or_404()

        progress = UserReadingProgress.query.filter_by(user_id=current_user.id, activity_id=activity_id).first()
        if not progress:
            current_app.logger.debug(
                "reading.reading_activity: no progress found for user %s activity %s; creating entry",
                current_user.id,
                activity_id,
            )
            progress = UserReadingProgress(user_id=current_user.id, activity_id=activity_id, unlocked_pages=[1])
            db.session.add(progress)
            db.session.commit()
            current_app.logger.debug(
                "reading.reading_activity: created initial progress for user %s activity %s",
                current_user.id,
                activity_id,
            )

        unlocked_pages = progress.unlocked_pages if isinstance(progress.unlocked_pages, list) else [1]
        current_app.logger.debug(
            "reading.reading_activity: unlocked_pages=%s for user %s activity %s",
            unlocked_pages,
            current_user.id,
            activity_id,
        )

        if page_number not in unlocked_pages:
            current_app.logger.debug(
                "reading.reading_activity: page %s not unlocked for user %s (unlocked=%s)",
                page_number,
                current_user.id,
                unlocked_pages,
            )
            flash("You haven't unlocked this page yet.", "warning")
            highest_unlocked = max(unlocked_pages) if unlocked_pages else 1
            current_app.logger.debug(
                "reading.reading_activity: redirecting user %s to highest unlocked page %s",
                current_user.id,
                highest_unlocked,
            )
            return redirect(url_for('reading.reading_activity', activity_id=activity_id, page_number=highest_unlocked))

        current_app.logger.debug(
            "reading.reading_activity: page %s unlocked for user %s",
            page_number,
            current_user.id,
        )
        return render_template('reading/activity.html', activity=activity, page=page, unlocked_pages=unlocked_pages)
    except Exception:
        db.session.rollback()
        current_app.logger.exception(
            "reading.reading_activity: error loading page %s for activity %s",
            page_number,
            activity_id,
        )
        flash("Error loading reading page.", "danger")
        return redirect(url_for('reading.reading_tasks'))


@reading_bp.route('/activity/<int:activity_id>/unlock/<int:page_number>', methods=['POST'])
@login_required
def unlock_page(activity_id, page_number):
    """API endpoint called by JavaScript to mark a page as unlocked."""
    current_app.logger.debug(
        "reading.unlock_page: attempting to unlock page %s for activity %s user %s",
        page_number,
        activity_id,
        current_user.id,
    )
    try:
        progress = UserReadingProgress.query.filter_by(user_id=current_user.id, activity_id=activity_id).first()
        if not progress:
            current_app.logger.debug(
                "reading.unlock_page: no progress found for user %s activity %s; creating entry",
                current_user.id,
                activity_id,
            )
            progress = UserReadingProgress(user_id=current_user.id, activity_id=activity_id, unlocked_pages=[1])
            db.session.add(progress)
            unlocked_pages = progress.unlocked_pages if isinstance(progress.unlocked_pages, list) else [1]
        else:
            unlocked_pages = progress.unlocked_pages if isinstance(progress.unlocked_pages, list) else [1]

        current_app.logger.debug(
            "reading.unlock_page: unlocked pages before change=%s for user %s activity %s",
            unlocked_pages,
            current_user.id,
            activity_id,
        )

        if page_number not in unlocked_pages:
            current_app.logger.debug(
                "reading.unlock_page: adding page %s to unlocked list",
                page_number,
            )
            if not isinstance(unlocked_pages, list):
                unlocked_pages = [1]  # Reset if data is bad
            unlocked_pages.append(page_number)
            unlocked_pages.sort()
            progress.unlocked_pages = unlocked_pages
            current_app.logger.debug(
                "reading.unlock_page: unlocked list assigned=%s",
                progress.unlocked_pages,
            )

            # --- TELL SQLALCHEMY THE FIELD WAS MODIFIED ---
            flag_modified(progress, "unlocked_pages")
            current_app.logger.debug(
                "reading.unlock_page: flag_modified called for unlocked_pages",
            )
            # ---------------------------------------------

            db.session.commit()
            current_app.logger.debug(
                "reading.unlock_page: commit successful for page %s",
                page_number,
            )

            # Optional: Verify read after commit (for debugging)
            # verify_progress = UserReadingProgress.query.filter_by(user_id=current_user.id, activity_id=activity_id).first()
            # print(f"DEBUG: unlock_page - VERIFY Read after commit: {verify_progress.unlocked_pages if verify_progress else 'Not found'}")

        else:
            current_app.logger.debug(
                "reading.unlock_page: page %s already unlocked",
                page_number,
            )

        return jsonify({'success': True, 'unlocked': progress.unlocked_pages})

    except Exception:
        db.session.rollback()
        current_app.logger.exception(
            "reading.unlock_page: error unlocking page %s for activity %s user %s",
            page_number,
            activity_id,
            current_user.id,
        )
        return jsonify({'success': False, 'error': 'Database error during unlock'}), 500


@reading_bp.route('/activity/create', methods=['GET', 'POST'])
@login_required
#@admin_required # Optional
def create_activity():
    """Handles the creation of a new reading activity."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        page_size_str = request.form.get('page_size', '100').strip()

        if not title or not content or not page_size_str.isdigit():
            flash('Invalid input...', 'danger')
            return render_template('reading/create_activity.html'), 400

        page_size = int(page_size_str)
        if page_size <= 0:
            flash('Words per page must be positive.', 'danger')
            return render_template('reading/create_activity.html'), 400

        try:
            activity = ReadingActivity(title=title)
            db.session.add(activity)
            db.session.flush()

            words = content.split()
            if not words:
                pages_data = [[]]
            else:
                pages_data = [
                    words[i:i + page_size]
                    for i in range(0, len(words), page_size)
                ]

            for idx, page_words in enumerate(pages_data):
                page_content = ' '.join(page_words)
                page = ReadingPage(
                    content=page_content,
                    page_number=idx + 1,
                    activity_id=activity.id,
                )
                db.session.add(page)

            db.session.commit()
            flash('Reading activity created successfully!', 'success')
            return redirect(
                url_for(
                    'reading.reading_activity',
                    activity_id=activity.id,
                    page_number=1,
                )
            )
        except Exception:
            db.session.rollback()
            current_app.logger.exception(
                "reading.create_activity: error creating activity '%s'",
                title,
            )
            flash("Error creating activity.", "danger")
            return render_template('reading/create_activity.html'), 500

    return render_template('reading/create_activity.html')
