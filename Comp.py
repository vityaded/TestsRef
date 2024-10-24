{% extends "layouts/base.html" %}

{% block title %}Learn Test - {{ test_name }}{% endblock %}

{% block styles %}
  {{ super() }}
  <!-- Include Font Awesome for icons -->
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
{% endblock %}

{% block content %}
  <h1 class="my-4">{{ test_name }}</h1>

  <form method="post">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
    
    <!-- Render the test content -->
    <div id="test-content">
      {% for line in processed_content %}
        <p>{{ line | safe }}</p>
      {% endfor %}
    </div>

    <button type="submit" class="btn btn-primary">Check Answers</button>
  </form>

  <!-- Translation and pronunciation popup -->
  <div id="translation-popup" style="display: none; position: absolute; background: #f9f9f9; border: 1px solid #ccc; padding: 10px; z-index: 1000;">
    <span id="translated-word" class="font-weight-bold"></span>
    <i class="fas fa-volume-up" id="hear-pronunciation" style="cursor: pointer; margin-left: 10px;"></i>
    <button id="add-to-vocab" class="btn btn-sm btn-success" style="margin-left: 10px;">
      <i class="fas fa-plus"></i>
    </button>
  </div>
{% endblock %}

{% block scripts %}
  {{ super() }}

  <script>
    // Function to wrap text nodes in a <span> for each word
    function wrapTextNodes(element) {
      const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, null, false);
      let node;
      const nodes = [];

      // Collect all text nodes
      while ((node = walker.nextNode())) {
        nodes.push(node);
      }

      nodes.forEach(textNode => {
        const words = textNode.textContent.split(/\s+/);
        const fragment = document.createDocumentFragment();

        words.forEach((word, index) => {
          if (word.trim()) {
            const span = document.createElement('span');
            span.textContent = word;
            span.style.cursor = 'pointer';
            span.className = 'word';
            span.onclick = (event) => {
              translateAndPronounce(word.trim(), event);
            };
            fragment.appendChild(span);
            if (index < words.length - 1) {
              fragment.appendChild(document.createTextNode(' '));
            }
          }
        });

        textNode.parentNode.replaceChild(fragment, textNode);
      });
    }

    // Translation and pronunciation handling
    function translateAndPronounce(word, event) {
      fetch('{{ url_for('main.translate_word') }}?word=' + encodeURIComponent(word))
        .then(response => response.json())
        .then(data => {
          if (data.translation) {
            const popup = document.getElementById('translation-popup');
            const translatedText = document.getElementById('translated-word');
            translatedText.textContent = `${word} - ${data.translation}`;

            // Position the popup next to the clicked word
            popup.style.display = 'block';
            popup.style.left = `${event.pageX}px`;
            popup.style.top = `${event.pageY}px`;

            const pronunciationBtn = document.getElementById('hear-pronunciation');
            pronunciationBtn.onclick = function() {
              const audio = new Audio('{{ url_for('main.tts') }}?text=' + encodeURIComponent(word) + '&lang=en');
              audio.play();
            };

            const addToVocabBtn = document.getElementById('add-to-vocab');
            addToVocabBtn.onclick = function() {
              saveToVocabulary(word, data.translation);
            };
          } else {
            alert('Translation not found');
          }
        })
        .catch(error => console.error('Error:', error));
    }

    // Function to save the word to the user's personal vocabulary
    function saveToVocabulary(word, translation) {
      if (!word || !translation) {
        alert('Cannot add an empty word or translation.');
        return;
      }

      fetch('{{ url_for('vocab.add_to_vocabulary') }}', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': '{{ csrf_token() }}'
        },
        body: JSON.stringify({
          word: word,
          translation: translation
        })
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          alert(`${word} has been added to your vocabulary!`);
        } else {
          alert('Failed to add the word to your vocabulary.');
        }
      })
      .catch(error => console.error('Error:', error));
    }

    // Once the document is loaded, wrap words in the content
    document.addEventListener('DOMContentLoaded', function() {
      const content = document.getElementById('test-content');
      wrapTextNodes(content);
    });

    // Close popup when clicking outside
    document.addEventListener('click', function(event) {
      const popup = document.getElementById('translation-popup');
      if (!popup.contains(event.target) && !event.target.classList.contains('word')) {
        popup.style.display = 'none';
      }
    });
  </script>
{% endblock %}
