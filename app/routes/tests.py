from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from app.models import Test, TestResult, Book, LearnTestResult, LearnTestProgress
from app.forms import AddTestForm, EditTestForm
from app import db
from datetime import datetime, timezone, timedelta
import random
import re
from app.utils import admin_required, normalize_text

tests_bp = Blueprint('tests', __name__, url_prefix='/tests')

@tests_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_test():
    form = AddTestForm()
    if form.validate_on_submit():
        book_title = form.book_title.data.strip()
        test_name = form.name.data.strip()
        test_content = form.content.data.strip()
        time_limit = form.time_limit.data
        shuffle_sentences = form.shuffle_sentences.data
        shuffle_paragraphs = form.shuffle_paragraphs.data

        # Check if the book exists
        book = Book.query.filter_by(title=book_title).first()
        if not book:
            # If the book doesn't exist, create it
            book = Book(title=book_title)
            db.session.add(book)
            db.session.commit()

        # Create the new test
        new_test = Test(
            name=test_name,
            content=test_content,
            book=book,
            time_limit=time_limit,
            shuffle_sentences=shuffle_sentences,
            shuffle_paragraphs=shuffle_paragraphs,
            created_by=current_user.id
        )
        db.session.add(new_test)
        db.session.commit()

        flash('Test added successfully!', 'success')
        return redirect(url_for('main.index'))

    return render_template('tests/add_test.html', form=form)

@tests_bp.route('/edit/<int:test_id>', methods=['GET', 'POST'])
@login_required
def edit_test(test_id):
    test = Test.query.get_or_404(test_id)

    # Ensure that only the creator or an admin can edit the test
    if test.created_by != current_user.id and not current_user.is_admin:
        flash('You do not have permission to edit this test.', 'danger')
        return redirect(url_for('main.index'))

    form = EditTestForm(obj=test)

    if form.validate_on_submit():
        test.name = form.name.data
        test.time_limit = form.time_limit.data
        test.content = form.content.data
        test.shuffle_sentences = form.shuffle_sentences.data
        test.shuffle_paragraphs = form.shuffle_paragraphs.data
        db.session.commit()
        flash('Test updated successfully.', 'success')
        return redirect(url_for('main.index'))
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {getattr(form, field).label.text}: {error}", 'danger')

    return render_template('tests/edit_test.html', form=form, test=test)

@tests_bp.route('/delete/<int:test_id>', methods=['POST'])
@login_required
def delete_test(test_id):
    test = Test.query.get_or_404(test_id)

    # Ensure that only the creator or an admin can delete the test
    if test.created_by != current_user.id and not current_user.is_admin:
        flash('You do not have permission to delete this test.', 'danger')
        return redirect(url_for('main.index'))

    db.session.delete(test)
    db.session.commit()

    flash('Test deleted successfully.', 'success')
    return redirect(url_for('main.index'))

@tests_bp.route('/<int:test_id>', methods=['GET', 'POST'])
@login_required
def take_test(test_id):
    test = Test.query.get_or_404(test_id)
    test_content = test.content
    time_limit = test.time_limit  # Time limit in minutes

    # Initialize variables
    processed_content = []
    correct_answers = {}
    original_order = []
    question_counter = 1

    # Function to replace answers with input fields or dropdowns
    def replace_answers(line):
        nonlocal question_counter
        dropdown_pattern = r'#\s*\[([^\]]+)\]\s*([^\#]+)\s*#'
        input_pattern = r'\[([^\]]+)\]'

        def dropdown_repl(match):
            nonlocal question_counter
            options_str = match.group(1)
            correct_answer = match.group(2).strip()
            options = [opt.strip() for opt in options_str.split(',')]
            qid = f'q{question_counter}'
            correct_answers[qid] = correct_answer
            question_counter += 1

            if request.method == 'POST':
                user_answer = request.form.get(qid, '').strip()
                # Normalize answers
                normalized_user_answer = normalize_text(user_answer)
                normalized_correct_answer = normalize_text(correct_answer)

                select_class = 'custom-select correct' if normalized_user_answer == normalized_correct_answer else 'custom-select incorrect'
                disabled = 'disabled'
            else:
                user_answer = ''
                select_class = 'custom-select'
                disabled = ''

            select_html = f'<select name="{qid}" class="{select_class}" {disabled} style="display: inline-block; width: auto;">'
            select_html += '<option value="">-- Select an option --</option>'
            for option in options:
                normalized_option = normalize_text(option)
                if request.method == 'POST':
                    selected = 'selected' if normalized_user_answer == normalized_option else ''
                else:
                    selected = ''
                select_html += f'<option value="{option}" {selected}>{option}</option>'
            select_html += '</select>'

            if request.method == 'POST' and normalized_user_answer != normalized_correct_answer:
                select_html += f' <span class="correct-answer">(Correct answer: {correct_answer})</span>'

            return select_html

        def input_repl(match):
            nonlocal question_counter
            correct_answer = match.group(1).strip()
            qid = f'q{question_counter}'
            correct_answers[qid] = correct_answer
            question_counter += 1

            if request.method == 'POST':
                user_answer = request.form.get(qid, '')
                # Normalize answers
                normalized_user_answer = normalize_text(user_answer.strip())
                normalized_correct_answer = normalize_text(correct_answer)
                input_class = 'form-control correct' if normalized_user_answer == normalized_correct_answer else 'form-control incorrect'
                readonly = 'readonly'
            else:
                user_answer = ''
                input_class = 'form-control'
                readonly = ''

            input_html = f'<input type="text" name="{qid}" value="{user_answer}" class="{input_class}" style="width: auto;" {readonly}>'

            if request.method == 'POST' and normalized_user_answer != normalized_correct_answer:
                input_html += f' <span class="correct-answer">(Correct answer: {correct_answer})</span>'

            return input_html

        # Process the line
        line = re.sub(dropdown_pattern, dropdown_repl, line)
        line = re.sub(input_pattern, input_repl, line)
        return line

    # Function to process the test content for drag-and-drop tests
    def process_content(content):
        nonlocal question_counter, original_order, processed_content
        lines = content.splitlines()

        if test.shuffle_sentences or test.shuffle_paragraphs:
            # Implement shuffling logic here if needed
            pass
        else:
            # Default behavior (no shuffling)
            for idx, line in enumerate(lines):
                processed_line = replace_answers(line)
                processed_content.append(processed_line)

    # Process the test content
    process_content(test_content)

    total_questions = question_counter - 1

    if request.method == 'POST':
        # Time limit enforcement
        start_time_str = session.get(f'start_time_{test_id}')
        if not start_time_str:
            flash('Test session expired. Please start the test again.', 'danger')
            return redirect(url_for('tests.take_test', test_id=test_id))
        else:
            start_time = datetime.fromisoformat(start_time_str)
            elapsed_time = datetime.now(timezone.utc) - start_time
            elapsed_minutes = elapsed_time.total_seconds() / 60

            if time_limit and elapsed_minutes > time_limit:
                flash('Time limit exceeded. Test submitted automatically.', 'warning')

        # Calculate score
        score = 0
        for qid, correct_answer in correct_answers.items():
            user_answer = request.form.get(qid, '').strip()
            # Normalize both answers
            normalized_user_answer = normalize_text(user_answer)
            normalized_correct_answer = normalize_text(correct_answer)

            if normalized_user_answer == normalized_correct_answer:
                score += 1

        # Save test result
        test_result = TestResult(
            score=score,
            total_questions=total_questions,
            user_id=current_user.id,
            test_id=test.id
        )
        db.session.add(test_result)
        db.session.commit()

        # Clear session
        session.pop(f'start_time_{test_id}', None)

        flash(f'You scored {score} out of {total_questions}!', 'info')
        return render_template(
            'tests/take_test.html',
            test=test,
            processed_content=processed_content,
            score=score,
            total=total_questions,
            correct_order=None,
            test_type='standard',
            correct_answers=correct_answers
        )

    else:
        # GET request: Start test, store start time in session
        session[f'start_time_{test_id}'] = datetime.now(timezone.utc).isoformat()

        return render_template(
            'tests/take_test.html',
            test=test,
            processed_content=processed_content,
            score=None,
            total=total_questions,
            time_limit=time_limit,
            correct_order=None,
            test_type='standard',
            correct_answers=correct_answers
        )


@tests_bp.route('/learn/<int:test_id>', methods=['GET', 'POST'])
@login_required
def learn_test(test_id):
    test = Test.query.get_or_404(test_id)
    test_content = test.content

    # Initialize variables
    processed_content = []
    correct_answers = {}
    question_counter = 1
    user_correct = {}

    # Retrieve or create LearnTestProgress
    progress = LearnTestProgress.query.filter_by(user_id=current_user.id, test_id=test.id).first()
    if not progress:
        progress = LearnTestProgress(user_id=current_user.id, test_id=test.id, answers={})
        db.session.add(progress)
        db.session.commit()

    # Prepare user_answers
    if request.method == 'POST':
        user_answers = {}
    else:
        user_answers = progress.answers or {}

    # Function to replace answers with input fields or dropdowns
    def replace_answers(line):
        nonlocal question_counter
        dropdown_pattern = r'#\s*\[([^\]]+)\]\s*([^\#]+)\s*#'
        input_pattern = r'\[([^\]]+)\]'

        def dropdown_repl(match):
            nonlocal question_counter
            options_str = match.group(1)
            correct_answer = match.group(2).strip()
            options = [opt.strip() for opt in options_str.split(',')]
            qid = f'q{question_counter}'
            correct_answers[qid] = correct_answer
            question_counter += 1

            select_class = 'custom-select'

            if request.method == 'POST':
                user_answer = request.form.get(qid, '').strip()
                user_answers[qid] = user_answer
            else:
                user_answer = user_answers.get(qid, '')

            # Normalize answers for comparison
            normalized_user_answer = normalize_text(user_answer)
            normalized_correct_answer = normalize_text(correct_answer)

            # Check if user's answer is correct
            if normalized_user_answer == normalized_correct_answer:
                user_correct[qid] = True
                select_class += ' correct'
            else:
                user_correct[qid] = False

            select_html = f'<select name="{qid}" class="{select_class}">'
            select_html += '<option value="">-- Select an option --</option>'
            for option in options:
                selected = 'selected' if user_answer == option else ''
                select_html += f'<option value="{option}" {selected}>{option}</option>'
            select_html += '</select>'

            return select_html

        def input_repl(match):
            nonlocal question_counter
            correct_answer = match.group(1).strip()
            qid = f'q{question_counter}'
            correct_answers[qid] = correct_answer
            question_counter += 1

            if request.method == 'POST':
                user_answer = request.form.get(qid, '').strip()
                user_answers[qid] = user_answer
            else:
                user_answer = user_answers.get(qid, '')

            input_class = 'form-control'

            # Normalize answers for comparison
            normalized_user_answer = normalize_text(user_answer)
            normalized_correct_answer = normalize_text(correct_answer)

            # Check if user's answer is correct
            if normalized_user_answer == normalized_correct_answer:
                user_correct[qid] = True
                input_class += ' correct'
            else:
                user_correct[qid] = False

            input_html = f'<input type="text" name="{qid}" value="{user_answer}" class="{input_class}">'

            return input_html

        # Process the line
        line = re.sub(dropdown_pattern, dropdown_repl, line)
        line = re.sub(input_pattern, input_repl, line)
        return line

    # Process each line in test content
    for line in test_content.splitlines():
        processed_line = replace_answers(line)
        processed_content.append(processed_line)

    if request.method == 'POST':
        # Save user's answers
        progress.answers = user_answers
        progress.last_updated = datetime.utcnow()
        db.session.commit()

        # Check if all answers are correct
        all_correct = all(user_correct.values())
        if all_correct:
            # Save learn test result
            learn_result = LearnTestResult(
                user_id=current_user.id,
                test_id=test.id
            )
            db.session.add(learn_result)
            db.session.commit()

            flash('You have answered everything correctly! You can now proceed.', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('Some answers are incorrect or missing. Please try again.', 'danger')
    else:
        # On GET request, no need to update answers
        pass

    return render_template(
        'tests/learn_test.html',
        test_name=test.name,
        processed_content=processed_content
    )
