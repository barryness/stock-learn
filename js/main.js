/* ============================================================
   main.js — App entry point (uses global: Toc, Search, Utils, COURSE_TOC, COURSE_CONTENT)
   ============================================================ */

(function() {
    'use strict';

    // ---- Globals from other scripts ----
    const T = window.Toc;
    const S = window.Search;
    const U = window.Utils;

    // ---- State ----
    let currentSectionId = null;
    let theme = U.storeGet('theme', 'light');
    let fontSize = U.storeGet('fontSize', 'medium');

    // ---- DOM refs ----
    function $(sel) { return document.querySelector(sel); }
    function $$(sel) { return document.querySelectorAll(sel); }

    const sidebar = $('#sidebar');
    const sidebarOverlay = $('#sidebar-overlay');
    const tocTreeEl = $('#toc-tree');
    const mainContent = $('#main-content');
    const contentBody = $('#content-body');
    const welcomeSection = $('#welcome-section');
    const searchInput = $('#search-input');
    const searchResults = $('#search-results');
    const themeToggle = $('#theme-toggle');
    const fontSmall = $('#font-small');
    const fontMedium = $('#font-medium');
    const fontLarge = $('#font-large');
    const mobileMenuBtn = $('#mobile-menu-btn');
    const backToTop = $('#back-to-top');
    const progressBar = $('#progress-bar');
    const chapterNav = $('#chapter-nav');
    const navbarBrand = $('#navbar-brand');

    // ---- Init on DOM ready ----
    function init() {
        applyTheme();
        applyFontSize();

        // Load TOC
        if (typeof COURSE_TOC !== 'undefined' && COURSE_TOC.length > 0) {
            T.buildTocTree(COURSE_TOC, tocTreeEl, navigateTo);
        }
        // Build search index
        if (typeof COURSE_CONTENT !== 'undefined') {
            S.buildIndex(COURSE_CONTENT);
        }
        // Scroll spy
        T.setupScrollSpy();

        // Bookshelf
        if (typeof BOOKS_DATA !== 'undefined' && typeof Bookshelf !== 'undefined') {
            Bookshelf.init();
        }

        // Events
        setupSidebarResize();
        setupNavbarEvents();
        setupScrollEvents();
        setupKeyboardShortcuts();

        // Render welcome cards
        renderWelcomeCards();

        // Hash routing
        const hash = window.location.hash.replace('#', '');
        if (hash && typeof COURSE_CONTENT !== 'undefined' && COURSE_CONTENT[hash]) {
            navigateTo({ sectionId: hash });
        }

        // Navbar brand click → go home
        if (navbarBrand) {
            navbarBrand.addEventListener('click', function(e) {
                e.preventDefault();
                showWelcome();
            });
        }

        console.log('[stock-learn] Initialized. ' +
            (typeof COURSE_TOC !== 'undefined' ? COURSE_TOC.length + ' chapters, ' : 'no chapters, ') +
            (typeof COURSE_CONTENT !== 'undefined' ? Object.keys(COURSE_CONTENT).length + ' sections loaded.' : 'no content.'));
    }

    // ---- Navigation ----
    function navigateTo(opts) {
        const sectionId = opts.sectionId;
        if (!sectionId || typeof COURSE_CONTENT === 'undefined') return;
        const data = COURSE_CONTENT[sectionId];
        if (!data || !data.markdown) {
            console.warn('[stock-learn] No content for:', sectionId);
            return;
        }

        currentSectionId = sectionId;
        window.location.hash = sectionId;

        // Show content, hide welcome
        if (welcomeSection) welcomeSection.style.display = 'none';
        if (mainContent) mainContent.style.display = 'block';

        // Render
        renderContent(data, sectionId);

        // TOC active state
        T.setActiveTocItem(sectionId);

        // Chapter nav
        updateChapterNav(sectionId);

        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });

        // Close mobile sidebar
        closeSidebar();
    }

    function showWelcome() {
        currentSectionId = null;
        window.location.hash = '';
        if (welcomeSection) welcomeSection.style.display = '';
        if (mainContent) mainContent.style.display = '';
        if (contentBody) contentBody.innerHTML = '';
        if (chapterNav) chapterNav.innerHTML = '';

        // Remove active states
        document.querySelectorAll('.toc-section-item.active, .toc-chapter-header.active').forEach(function(el) {
            el.classList.remove('active');
        });

        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // ---- Content Rendering ----
    function convertAsciiArt(md) {
        var lines = md.split('\n');
        var result = [];
        var inCodeBlock = false;
        var asciiBuffer = [];
        var asciiRe = /[┌┐└┘├┤┬┴┼│─]/;

        function isDataRow(line) {
            var parts = line.split('│');
            if (parts.length < 3) return false;
            var inner = [];
            for (var k = 1; k < parts.length - 1; k++) { inner.push(parts[k].trim()); }
            return inner.some(function(c) { return c.length > 0; });
        }

        function parseRow(line) {
            var parts = line.split('│');
            var cells = [];
            for (var k = 1; k < parts.length - 1; k++) { cells.push(parts[k].trim()); }
            return cells;
        }

        function classifyBuffer(buf) {
            var dataRows = [];
            var hasHeaderSep = false;
            for (var r = 0; r < buf.length; r++) {
                if (/[├┼┤]/.test(buf[r]) && /[─]/.test(buf[r])) { hasHeaderSep = true; }
                if (isDataRow(buf[r])) { dataRows.push(parseRow(buf[r])); }
            }
            if (dataRows.length >= 2 || (dataRows.length >= 1 && hasHeaderSep)) {
                var cols = dataRows[0].length;
                var consistent = true;
                for (var r = 1; r < dataRows.length; r++) {
                    if (dataRows[r].length !== cols) { consistent = false; break; }
                }
                if (consistent && cols >= 2) return { type: 'table', rows: dataRows };
            }
            return { type: 'code', lines: buf };
        }

        function rowsToMarkdownTable(rows) {
            if (rows.length === 0) return '';
            var out = [];
            out.push('| ' + rows[0].join(' | ') + ' |');
            var sep = '|' + rows[0].map(function() { return ' --- '; }).join('|') + '|';
            out.push(sep);
            for (var r = 1; r < rows.length; r++) {
                out.push('| ' + rows[r].join(' | ') + ' |');
            }
            return out.join('\n');
        }

        function flushBuffer() {
            if (asciiBuffer.length === 0) return;
            var classification = classifyBuffer(asciiBuffer);
            if (classification.type === 'table') {
                result.push('');
                result.push(rowsToMarkdownTable(classification.rows));
                result.push('');
            } else {
                result.push('```');
                for (var b = 0; b < asciiBuffer.length; b++) { result.push(asciiBuffer[b]); }
                result.push('```');
            }
            asciiBuffer = [];
        }

        for (var i = 0; i < lines.length; i++) {
            var line = lines[i];

            if (/^\s*```/.test(line)) {
                flushBuffer();
                inCodeBlock = !inCodeBlock;
                result.push(line);
                continue;
            }

            if (inCodeBlock) {
                result.push(line);
                continue;
            }

            if (asciiRe.test(line)) {
                asciiBuffer.push(line);
            } else {
                flushBuffer();
                result.push(line);
            }
        }
        flushBuffer();

        return result.join('\n');
    }

    function renderContent(data, sectionId) {
        var html = '';
        var md = convertAsciiArt(data.markdown);

        if (typeof marked !== 'undefined') {
            marked.setOptions({ breaks: false, gfm: true });
            html = marked.parse(md);
        } else {
            html = basicMarkdownToHtml(md);
        }

        html = addHeadingIds(html);
        html = processImages(html, data.chapterDir);
        html = processCodeBlocks(html);

        const exerciseHtml = renderExerciseSection(data);

        const wrapper = document.createElement('div');
        wrapper.className = 'content-section active';
        wrapper.id = sectionId;

        const bodyDiv = document.createElement('div');
        bodyDiv.className = 'content-body';
        bodyDiv.innerHTML = html + exerciseHtml;

        wrapper.appendChild(bodyDiv);

        contentBody.innerHTML = '';
        contentBody.appendChild(wrapper);

        // Syntax highlighting
        if (typeof hljs !== 'undefined') {
            contentBody.querySelectorAll('pre code').forEach(function(block) {
                hljs.highlightElement(block);
            });
        }

        // Setup interactive features
        setupCopyButtons();
        setupLightbox(contentBody);
    }

    function addHeadingIds(html) {
        return html.replace(/<(h[23])>(.*?)<\/\1>/gi, function(match, tag, text) {
            const id = text.replace(/<[^>]+>/g, '').toLowerCase()
                .replace(/[^\w一-鿿]+/g, '-').replace(/^-+|-+$/g, '');
            return '<' + tag + ' id="' + id + '">' + text + '</' + tag + '>';
        });
    }

    function processImages(html, chapterDir) {
        return html.replace(/<img\s+src="([^"]+)"([^>]*)>/gi, function(match, src, rest) {
            let newSrc = src;
            if (!src.includes('/') && !src.startsWith('http')) {
                newSrc = 'assets/images/' + src;
            }
            return '<img src="' + newSrc + '"' + (rest || '') + ' loading="lazy" class="content-img">';
        });
    }

    function processCodeBlocks(html) {
        return html.replace(/(<pre><code[^>]*>)/g, '<div class="code-block-wrapper">$1')
                   .replace(/(<\/code><\/pre>)/g, '$1</div>');
    }

    function renderExerciseSection(data) {
        if (!data.pyFiles || data.pyFiles.length === 0) return '';
        let h = '<div style="margin-top:40px"><h2>配套练习代码</h2><div class="exercise-actions">';
        data.pyFiles.forEach(function(pyFile) {
            h += '<a class="exercise-download-btn" href="assets/exercises/' + pyFile + '" download>';
            h += '<i class="fas fa-download"></i> 下载 ' + pyFile + '</a>';
        });
        h += '</div></div>';
        return h;
    }

    function basicMarkdownToHtml(md) {
        let html = md;
        html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>');
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
        html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
        html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
        html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
        html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
        html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
        html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
        html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1">');
        html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
        html = html.replace(/^---$/gm, '<hr>');
        html = html.replace(/^>\s?(.+)$/gm, '<blockquote>$1</blockquote>');
        html = html.replace(/\n\n/g, '</p><p>');
        html = '<p>' + html + '</p>';
        return html;
    }

    // ---- Chapter Navigation ----
    function updateChapterNav(sectionId) {
        const allSections = [];
        if (typeof COURSE_TOC !== 'undefined') {
            COURSE_TOC.forEach(function(ch) {
                ch.sections.forEach(function(sec) {
                    allSections.push(sec.id);
                });
            });
        }

        const idx = allSections.indexOf(sectionId);
        let prevHtml = '';
        let nextHtml = '';

        if (idx > 0) {
            const prevData = COURSE_CONTENT[allSections[idx - 1]];
            prevHtml = '<a href="#' + allSections[idx - 1] + '" class="nav-prev" data-section="' + allSections[idx - 1] + '">← ' + (prevData ? prevData.sectionTitle : '上一节') + '</a>';
        } else {
            prevHtml = '<span class="nav-placeholder"></span>';
        }

        if (idx >= 0 && idx < allSections.length - 1) {
            const nextData = COURSE_CONTENT[allSections[idx + 1]];
            nextHtml = '<a href="#' + allSections[idx + 1] + '" class="nav-next" data-section="' + allSections[idx + 1] + '">' + (nextData ? nextData.sectionTitle : '下一节') + ' →</a>';
        }

        chapterNav.innerHTML = prevHtml + nextHtml;
        chapterNav.querySelectorAll('a').forEach(function(link) {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                navigateTo({ sectionId: link.dataset.section });
            });
        });
    }

    // ---- Copy Buttons ----
    function setupCopyButtons() {
        contentBody.querySelectorAll('.code-block-wrapper').forEach(function(wrapper) {
            if (wrapper.querySelector('.copy-btn')) return;
            const btn = document.createElement('button');
            btn.className = 'copy-btn';
            btn.innerHTML = '<i class="fas fa-copy"></i> 复制代码';
            btn.addEventListener('click', function() {
                const code = wrapper.querySelector('code');
                const text = code ? code.textContent : '';
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(text).then(function() {
                        btn.innerHTML = '<i class="fas fa-check"></i> 已复制';
                        btn.classList.add('copied');
                        setTimeout(function() {
                            btn.innerHTML = '<i class="fas fa-copy"></i> 复制代码';
                            btn.classList.remove('copied');
                        }, 2000);
                    });
                } else {
                    const range = document.createRange();
                    range.selectNodeContents(code);
                    const sel = window.getSelection();
                    sel.removeAllRanges();
                    sel.addRange(range);
                    btn.textContent = '请按 Ctrl+C';
                    setTimeout(function() { btn.innerHTML = '<i class="fas fa-copy"></i> 复制代码'; }, 2000);
                }
            });
            wrapper.appendChild(btn);
        });
    }

    // ---- Image Lightbox ----
    let lightboxEl = null;

    function setupLightbox(container) {
        if (!lightboxEl) {
            lightboxEl = document.createElement('div');
            lightboxEl.className = 'lightbox';
            lightboxEl.innerHTML = '<span class="lightbox-close">&times;</span><img src="" alt=""><div class="lightbox-caption"></div>';
            document.body.appendChild(lightboxEl);

            lightboxEl.querySelector('.lightbox-close').addEventListener('click', closeLightbox);
            lightboxEl.addEventListener('click', function(e) {
                if (e.target === lightboxEl) closeLightbox();
            });
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') closeLightbox();
            });
        }

        container.querySelectorAll('img.content-img').forEach(function(img) {
            if (img.dataset.lightboxed) return;
            img.dataset.lightboxed = '1';
            img.addEventListener('click', function(e) {
                e.preventDefault();
                openLightbox(img.src, img.alt);
            });
        });
    }

    function openLightbox(src, alt) {
        if (!lightboxEl) return;
        lightboxEl.querySelector('img').src = src;
        lightboxEl.querySelector('.lightbox-caption').textContent = alt || '';
        lightboxEl.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    function closeLightbox() {
        if (!lightboxEl) return;
        lightboxEl.classList.remove('active');
        document.body.style.overflow = '';
    }

    // ---- Theme ----
    function applyTheme() {
        document.documentElement.setAttribute('data-theme', theme);
        if (themeToggle) {
            const icon = themeToggle.querySelector('i');
            if (icon) icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        }
        U.storeSet('theme', theme);
    }

    function toggleTheme() {
        theme = theme === 'dark' ? 'light' : 'dark';
        applyTheme();
    }

    // ---- Font Size ----
    function applyFontSize() {
        document.documentElement.setAttribute('data-font', fontSize);
        document.querySelectorAll('.navbar-actions button[data-font]').forEach(function(btn) {
            btn.classList.toggle('active', btn.dataset.font === fontSize);
        });
        U.storeSet('fontSize', fontSize);
    }

    function setFontSize(size) {
        fontSize = size;
        applyFontSize();
    }

    // ---- Navbar Events ----
    function setupNavbarEvents() {
        if (themeToggle) themeToggle.addEventListener('click', toggleTheme);
        if (fontSmall) fontSmall.addEventListener('click', function() { setFontSize('small'); });
        if (fontMedium) fontMedium.addEventListener('click', function() { setFontSize('medium'); });
        if (fontLarge) fontLarge.addEventListener('click', function() { setFontSize('large'); });
        if (mobileMenuBtn) mobileMenuBtn.addEventListener('click', toggleSidebar);
        if (sidebarOverlay) sidebarOverlay.addEventListener('click', closeSidebar);

        // Search
        if (searchInput) {
            searchInput.addEventListener('input', U.debounce(handleSearch, 200));
            searchInput.addEventListener('focus', function() {
                if (searchInput.value.trim().length >= 2) handleSearch();
            });
        }
        document.addEventListener('click', function(e) {
            if (searchResults && !searchInput.parentElement.contains(e.target) && !searchResults.contains(e.target)) {
                searchResults.classList.remove('active');
            }
        });
    }

    function handleSearch() {
        const query = searchInput.value.trim();
        if (query.length < 2) {
            searchResults.classList.remove('active');
            return;
        }
        const results = S.search(query);
        S.renderResults(results, searchResults, function(result) {
            searchResults.classList.remove('active');
            searchInput.value = '';
            navigateTo({ sectionId: result.sectionId });
        });
        searchResults.classList.add('active');
    }

    function toggleSidebar() {
        if (sidebar) sidebar.classList.toggle('open');
        if (sidebarOverlay) sidebarOverlay.classList.toggle('active');
    }

    function closeSidebar() {
        if (sidebar) sidebar.classList.remove('open');
        if (sidebarOverlay) sidebarOverlay.classList.remove('active');
    }

    // ---- Sidebar Resize ----
    function setupSidebarResize() {
        var handle = $('#sidebar-resize-handle');
        if (!handle || !sidebar) return;

        var startX, startWidth;
        var savedWidth = U.storeGet('sidebarWidth');
        if (savedWidth) {
            document.documentElement.style.setProperty('--sidebar-width', savedWidth + 'px');
        }

        handle.addEventListener('mousedown', function(e) {
            e.preventDefault();
            startX = e.clientX;
            startWidth = sidebar.offsetWidth;
            handle.classList.add('active');
            sidebar.classList.add('resizing');
            document.body.style.cursor = 'col-resize';
        });

        document.addEventListener('mousemove', function(e) {
            if (startX === undefined) return;
            var delta = e.clientX - startX;
            var newWidth = Math.max(220, Math.min(600, startWidth + delta));
            document.documentElement.style.setProperty('--sidebar-width', newWidth + 'px');
            sidebar.style.width = newWidth + 'px';
        });

        document.addEventListener('mouseup', function() {
            if (startX === undefined) return;
            handle.classList.remove('active');
            sidebar.classList.remove('resizing');
            document.body.style.cursor = '';
            var finalWidth = sidebar.offsetWidth;
            U.storeSet('sidebarWidth', finalWidth);
            startX = undefined;
        });
    }

    // ---- Scroll ----
    function setupScrollEvents() {
        window.addEventListener('scroll', U.throttle(function() {
            const show = window.scrollY > 400;
            if (backToTop) backToTop.classList.toggle('visible', show);
            if (progressBar) {
                const scrollH = document.documentElement.scrollHeight - window.innerHeight;
                const pct = scrollH > 0 ? (window.scrollY / scrollH) * 100 : 0;
                progressBar.style.width = Math.min(pct, 100) + '%';
            }
        }, 100));

        if (backToTop) {
            backToTop.addEventListener('click', function() {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            });
        }
    }

    // ---- Keyboard ----
    function setupKeyboardShortcuts() {
        document.addEventListener('keydown', function(e) {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                if (searchInput) searchInput.focus();
            }
            if (e.key === 'Escape') {
                if (searchResults) searchResults.classList.remove('active');
            }
        });
    }

    // ---- Welcome Cards ----
    function renderWelcomeCards() {
        const grid = $('#welcome-grid');
        if (!grid || typeof COURSE_TOC === 'undefined') return;

        grid.innerHTML = '';
        const stageDescs = [
            '投资认知与复利思维', '股票本质与三大市场', '基金入门与定投策略',
            '财报解读与造假识别', '估值方法与DCF建模', '基金组合与资产配置',
            '技术分析与K线语言', '量化回测与因子模型', '个人投资系统构建'
        ];

        COURSE_TOC.forEach(function(chapter, chIdx) {
            const firstSection = chapter.sections[0];
            if (!firstSection) return;

            const card = document.createElement('div');
            card.className = 'welcome-card';
            card.dataset.sectionId = firstSection.id;
            card.innerHTML = '<div class="card-num">0' + (chIdx + 1) + '</div>' +
                '<div class="card-title">' + chapter.title + '</div>' +
                '<div class="card-desc">' + (stageDescs[chIdx] || '') + '</div>';
            card.addEventListener('click', function() {
                if (typeof COURSE_CONTENT !== 'undefined' && COURSE_CONTENT[firstSection.id]) {
                    navigateTo({ sectionId: firstSection.id });
                }
            });
            grid.appendChild(card);
        });
    }

    // ---- Boot ----
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
