from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_login import login_required, current_user
from ..models import Book, Test
from .. import db
from ..utils import admin_required
import requests

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    books = Book.query.all()
    total_tests = sum(len(book.tests) for book in books)
    return render_template('main/index.html', books=books, total_tests=total_tests)

@main_bp.route('/book/<int:book_id>')
def book_tests(book_id):
    book = Book.query.get_or_404(book_id)
    tests = Test.query.filter_by(book_id=book.id).all()
    return render_template('main/book_tests.html', book=book, tests=tests)

@main_bp.route('/search')
def search():
    query = request.args.get('query', '').strip()
    search_option = request.args.get('search_option', 'books')

    if not query:
        flash('Please enter a search term.', 'warning')
        return redirect(url_for('main.index'))

    if search_option == 'books':
        # Search for books by title
        books = Book.query.filter(Book.title.ilike(f'%{query}%')).all()
        return render_template('main/search_results.html', books=books, query=query, search_option=search_option)
    else:
        # Search for tests by name
        tests = Test.query.filter(Test.name.ilike(f'%{query}%')).all()
        return render_template('main/search_results.html', tests=tests, query=query, search_option=search_option)

@main_bp.route('/autocomplete_search')
def autocomplete_search():
    query = request.args.get('query', '').strip()
    search_option = request.args.get('search_option', 'books')

    results = []

    if query:
        if search_option == 'books':
            # Search for matching books by title
            books = Book.query.filter(Book.title.ilike(f'%{query}%')).all()
            results = [{'label': book.title, 'value': book.title} for book in books]
        elif search_option == 'tests':
            # Search for matching tests by name
            tests = Test.query.filter(Test.name.ilike(f'%{query}%')).all()
            results = [{'label': test.name, 'value': test.name} for test in tests]

    return jsonify(results)

@main_bp.route('/tts')
def tts():
    text = request.args.get('text')
    language = request.args.get('lang', 'en')

    # Make the request to Google TTS API
    tts_url = f'https://translate.google.com/translate_tts?ie=UTF-8&tl={language}&client=gtx&q={text}'
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(tts_url, headers=headers)

    # Return the audio response
    return Response(response.content, mimetype='audio/mpeg')

@main_bp.route('/translate')
def translate_word():
    word = request.args.get('word')
    source_lang = 'en'
    target_lang = 'uk'

    if not word:
        return jsonify({'error': 'No word provided for translation'}), 400

    # Construct the translation URL for Google Translate
    translate_url = (
        f'https://translate.googleapis.com/translate_a/single?client=gtx&sl={source_lang}&tl={target_lang}&dt=t&q={word}'
    )

    try:
        # Make the request to the Google Translate API
        response = requests.get(translate_url)
        response.raise_for_status()

        translation_data = response.json()

        if translation_data and isinstance(translation_data, list) and len(translation_data) > 0:
            translation = translation_data[0][0][0]
            pronunciation_url = f'https://translate.google.com/translate_tts?ie=UTF-8&tl={source_lang}&client=gtx&q={word}'

            return jsonify({
                'translation': translation,
                'pronunciation_url': pronunciation_url
            })
        else:
            return jsonify({'error': 'Unexpected translation response format'}), 500

    except requests.RequestException as e:
        return jsonify({'error': f'Translation API request failed: {str(e)}'}), 500

@main_bp.route('/autocomplete_book')
@login_required
def autocomplete_book():
    q = request.args.get('q', '')
    books = Book.query.filter(Book.title.ilike(f'%{q}%')).all()
    titles = [book.title for book in books]
    return jsonify(titles)

@main_bp.route('/autocomplete_test')
@login_required
def autocomplete_test():
    q = request.args.get('q', '')
    tests = Test.query.filter(Test.name.ilike(f'%{q}%')).all()
    names = [test.name for test in tests]
    return jsonify(names)

@main_bp.route('/book/delete/<int:book_id>', methods=['POST'])
@login_required
@admin_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    db.session.delete(book)
    db.session.commit()
    flash('Book deleted successfully.', 'success')
    return redirect(url_for('main.index'))
