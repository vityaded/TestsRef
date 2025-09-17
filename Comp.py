{% extends "layouts/base.html" %}

{% block title %}{{ activity.title }} - Page {{ page.page_number }}{% endblock %}

{% block content %}
<h1>{{ activity.title }}</h1>
<h3>Page {{ page.page_number }}</h3>

<div id="text-container">
    {% set non_english_words = ['bonjour', 'amigo', 'sayonara', 'café', 'façade', 'jalapeño', 'résumé', 'naïve'] %}
    {% for word in page.content.split() %}
        {% set stripped_word = word.strip('.,;!?') %}
        {% set is_proper_noun = stripped_word and stripped_word[0].isupper() %}
        {% set is_non_english = stripped_word and stripped_word|lower in non_english_words %}
        {% set word_classes = 'word' %}
        {% if is_proper_noun %}
            {% set word_classes = word_classes + ' proper-noun' %}
        {% endif %}
        {% if is_non_english %}
            {% set word_classes = word_classes + ' non-english' %}
        {% endif %}
        <span class="{{ word_classes }}">{{ word }}</span>
    {% endfor %}
</div>

<button id="start-btn" class="btn btn-primary">Start Reading</button>
<button id="stop-btn" class="btn btn-secondary" disabled>Stop</button>

{% if page.page_number < activity.pages|length %}
    <button id="next-btn" class="btn btn-success" style="display: none;">Next Page</button>
{% endif %}

<!-- Display area for speech recognition results -->
<div id="speech-recognition-output" style="margin-top: 20px;">
    <h4>Speech Recognition Output:</h4>
    <p id="recognized-text" style="font-size: 1.2em; color: blue;"></p>
</div>

{% endblock %}

{% block scripts %}
{{ super() }}
<script>
document.addEventListener('DOMContentLoaded', function() {
    console.log('Page loaded and script initialized.');

    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    const nextBtn = document.getElementById('next-btn');
    const words = document.querySelectorAll('#text-container .word');
    const recognizedTextElement = document.getElementById('recognized-text');

    let wordIndex = 0;
    let isRecognizing = false;
    let incorrectAttempts = 0;
    let isSpeaking = false;

    // List of foreign words
    const nonEnglishWords = [
        'bonjour', 'amigo', 'sayonara', 'café', 'façade', 'jalapeño', 'résumé', 'naïve'
        // Add more foreign words as needed
    ];

    // Mapping of contractions to their expanded forms
    const contractions = {
        // ... (existing contractions)
    };

    const spellingVariants = {
        // ... (existing spelling variants)
    };

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        alert('Your browser does not support Speech Recognition.');
        disableSpeechRecognition();
        return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US'; // Adjust language as needed
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onstart = () => {
        isRecognizing = true;
        startBtn.disabled = true;
        stopBtn.disabled = false;
        highlightCurrentWord();
        console.log('Speech recognition started.');
    };

    recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
    };

    recognition.onend = () => {
        isRecognizing = false;
        startBtn.disabled = false;
        stopBtn.disabled = true;
        removeHighlightFromCurrentWord();
        console.log('Speech recognition ended.');

        // Restart recognition if not finished
        if (!isSpeaking && wordIndex < words.length) {
            startRecognition();
        }
    };

    recognition.onresult = (event) => {
        if (isSpeaking) {
            // Do not process speech recognition results while speaking
            return;
        }

        // Get the latest result
        let lastResult = event.results[event.results.length - 1];
        let transcript = lastResult[0].transcript.trim().toLowerCase();

        console.log('Speech recognition result received:', transcript);

        if (transcript) {
            recognizedTextElement.textContent = transcript;
            processSpokenWords(transcript);
        } else {
            console.log('No speech input.');
        }
    };

    function processSpokenWords(spokenWords) {
        // ... (existing implementation)
    }

    function isSegmentMatch(expectedWordsArray, spokenWordsArray, options) {
        // ... (existing implementation)
    }

    function countCommonLetters(word1, word2) {
        // ... (existing implementation)
    }

    function highlightCurrentWord() {
        words.forEach(word => word.classList.remove('current-word'));
        if (wordIndex < words.length) {
            words[wordIndex].classList.add('current-word');
            console.log(`Highlighting word: "${words[wordIndex].textContent}" at index ${wordIndex}`);
        }
    }

    function removeHighlightFromCurrentWord() {
        if (wordIndex < words.length) {
            words[wordIndex].classList.remove('current-word');
            console.log(`Removing highlight from word: "${words[wordIndex].textContent}" at index ${wordIndex}`);
        }
    }

 

    function startRecognition() {
        if (!isRecognizing) {
            recognition.start();
            isRecognizing = true;
        }
    }

    function stopRecognition() {
        if (isRecognizing) {
            recognition.stop();
            isRecognizing = false;
        }
    }

    startBtn.addEventListener('click', () => {
        startRecognition();
    });

    stopBtn.addEventListener('click', () => {
        stopRecognition();
    });

    nextBtn.addEventListener('click', () => {
        // ... (existing implementation)
    });

    // Pronunciation feature on word click
    const synth = window.speechSynthesis;

    if (synth) {
        words.forEach(wordElement => {
            wordElement.addEventListener('click', () => {
                const wordText = wordElement.textContent;
                playPronunciation(wordText);
            });
        });
    } else {
        alert('Your browser does not support Speech Synthesis.');
    }

    function playPronunciation(text) {
        if (isSpeaking) return; // Prevent overlapping speech synthesis
        console.log('Playing pronunciation for:', text);

        // Cancel any current speech synthesis to clear the queue
        if (synth.speaking || synth.pending) {
            synth.cancel();
        }

        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'en-US'; // Adjust language as needed

        utterance.onstart = () => {
            console.log('Speech synthesis started.');
            isSpeaking = true;
            if (isRecognizing) {
                stopRecognition();
            }
        };

        utterance.onend = () => {
            console.log('Speech synthesis ended.');
            isSpeaking = false;
            if (wordIndex < words.length) {
                startRecognition();
            }
        };

        utterance.onerror = (event) => {
            console.error('Speech synthesis error:', event.error);
            isSpeaking = false;
            if (wordIndex < words.length) {
                startRecognition();
            }
            // Retry playing the pronunciation
            setTimeout(() => {
                playPronunciation(text);
            }, 1000); // Retry after 1 second
        };

        synth.speak(utterance);
    }

    function expandContraction(word) {
        // ... (existing implementation)
    }

    function areSpellingVariants(expected, spoken) {
        // ... (existing implementation)
    }

    function wordsAreSimilar(expected, spoken) {
        // ... (existing implementation)
    }

    function levenshteinDistance(a, b) {
        // ... (existing implementation)
    }

    function disableSpeechRecognition() {
        startBtn.disabled = true;
        stopBtn.disabled = true;
        alert('Speech recognition is not supported in this browser.');
    }

});
</script>

<style>
.word {
    padding: 2px;
    cursor: pointer;
}

.proper-noun {
    font-style: italic;
}

.non-english {
    text-decoration: underline;
}

.highlighted {
    background-color: #d4edda;
}

.current-word {
    background-color: yellow;
}

.incorrect {
    border-bottom: 2px solid red;
}

.skipped {
    text-decoration: line-through;
}

.no-speech-synthesis {
    pointer-events: none;
    cursor: default;
}
</style>
{% endblock %}

