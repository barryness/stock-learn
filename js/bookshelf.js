/* ============================================================
   bookshelf.js — Bookshelf feature (global: window.Bookshelf)
   ============================================================ */

(function() {
    'use strict';

    var B = {};
    var currentBook = null;
    var panelEl = null;
    var overlayEl = null;

    B.init = function() {
        // Create overlay and panel
        overlayEl = document.createElement('div');
        overlayEl.className = 'bookshelf-overlay';
        overlayEl.addEventListener('click', B.close);
        document.body.appendChild(overlayEl);

        panelEl = document.createElement('div');
        panelEl.className = 'bookshelf-panel';
        document.body.appendChild(panelEl);

        // Attach to existing button in navbar
        var shelfBtn = document.getElementById('bookshelf-btn');
        if (shelfBtn) {
            shelfBtn.addEventListener('click', B.open);
        }
    };

    B.open = function() {
        if (currentBook) {
            renderBook(currentBook);
        } else {
            renderBookList();
        }
        panelEl.classList.add('active');
        overlayEl.classList.add('active');
        document.body.style.overflow = 'hidden';
    };

    B.close = function() {
        panelEl.classList.remove('active');
        overlayEl.classList.remove('active');
        document.body.style.overflow = '';
        currentBook = null;
    };

    function renderBookList() {
        var html = '<div class="bookshelf-header">';
        html += '<button class="bookshelf-back-btn" title="关闭书架"><i class="fas fa-times"></i></button>';
        html += '<h2><i class="fas fa-book-open"></i> 我的书架</h2>';
        html += '<p class="bookshelf-subtitle">经典投资理财书籍 · 精选核心内容</p>';
        html += '</div>';

        html += '<div class="bookshelf-grid">';
        for (var i = 0; i < BOOKS_DATA.length; i++) {
            var book = BOOKS_DATA[i];
            html += '<div class="book-card" data-book-id="' + book.id + '">';
            html += '<div class="book-cover" style="background: ' + book.cover + '">';
            var emojiMap = { xiaogouqianqian: '🐕', fubabaqiongbaba: '💰', congmingdetouzizhe: '🦉', nawaerbaodian: '🚀', qiongchalibaodian: '🧠' };
            html += '<span class="book-emoji">' + (emojiMap[book.id] || '📖') + '</span>';
            html += '</div>';
            html += '<div class="book-info">';
            html += '<div class="book-title">' + book.title + '</div>';
            html += '<div class="book-author">' + book.author + '</div>';
            html += '<div class="book-tagline">' + book.tagline + '</div>';
            html += '</div>';
            html += '</div>';
        }
        html += '</div>';

        panelEl.innerHTML = html;

        // Click book card
        var cards = panelEl.querySelectorAll('.book-card');
        for (var j = 0; j < cards.length; j++) {
            cards[j].addEventListener('click', function() {
                var id = this.dataset.bookId;
                var book = findBook(id);
                if (book) {
                    currentBook = book;
                    renderBook(book);
                    panelEl.scrollTop = 0;
                }
            });
        }

        // Close button
        var closeBtn = panelEl.querySelector('.bookshelf-back-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', B.close);
        }
    }

    function renderBook(book) {
        var html = '<div class="bookshelf-header">';
        html += '<button class="bookshelf-back-btn"><i class="fas fa-arrow-left"></i></button>';
        html += '<h2 style="color:' + book.cover + '">' + book.title + '</h2>';
        html += '<p class="bookshelf-subtitle">' + book.author + ' · ' + book.tagline + '</p>';
        html += '</div>';

        html += '<div class="book-content">';

        // Intro
        html += '<div class="book-intro-card">';
        html += '<p>' + book.intro  + '</p>';
        html += '</div>';

        // Chapters
        html += '<div class="book-chapters">';
        for (var i = 0; i < book.chapters.length; i++) {
            var ch = book.chapters[i];
            html += '<div class="chapter-card">';
            html += '<div class="chapter-header">';
            html += '<span class="chapter-num">' + padNum(i + 1) + '</span>';
            html += '<div class="chapter-title-wrap">';
            html += '<h3><i class="fas ' + ch.icon + ' chapter-icon"></i> ' + ch.title + '</h3>';
            html += '</div>';
            html += '</div>';

            html += '<div class="chapter-body">';
            html += '<div class="chapter-story">';
            html += '<i class="fas fa-feather-alt story-icon"></i>';
            html += '<p>' + ch.story + '</p>';
            html += '</div>';

            html += '<blockquote class="chapter-quote">';
            html += '<i class="fas fa-quote-left quote-icon"></i>';
            html += '<p>' + ch.quote + '</p>';
            html += '</blockquote>';

            html += '<div class="chapter-takeaway">';
            html += '<div class="takeaway-label">📝 核心要点</div>';
            if (Array.isArray(ch.takeaway)) {
                html += '<ul>';
                for (var t = 0; t < ch.takeaway.length; t++) {
                    html += '<li>' + ch.takeaway[t] + '</li>';
                }
                html += '</ul>';
            } else {
                html += '<p>' + ch.takeaway + '</p>';
            }
            html += '</div>';

            if (ch.tip) {
                html += '<div class="chapter-tip">' + ch.tip + '</div>';
            }

            html += '</div>'; // chapter-body
            html += '</div>'; // chapter-card
        }
        html += '</div>'; // book-chapters

        // Closing quote
        html += '<div class="book-closing">';
        html += '<i class="fas fa-quote-right closing-quote-icon"></i>';
        html += '<p>' + book.closingQuote + '</p>';
        html += '</div>';

        html += '</div>'; // book-content

        panelEl.innerHTML = html;

        // Back button → book list
        var backBtn = panelEl.querySelector('.bookshelf-back-btn');
        if (backBtn) {
            backBtn.addEventListener('click', function() {
                currentBook = null;
                renderBookList();
                panelEl.scrollTop = 0;
            });
        }
    }

    function findBook(id) {
        for (var i = 0; i < BOOKS_DATA.length; i++) {
            if (BOOKS_DATA[i].id === id) return BOOKS_DATA[i];
        }
        return null;
    }

    function padNum(n) {
        return n < 10 ? '0' + n : '' + n;
    }

    // ESC key to close
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && panelEl && panelEl.classList.contains('active')) {
            B.close();
        }
    });

    window.Bookshelf = B;
})();
