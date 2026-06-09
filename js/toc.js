/* ============================================================
   toc.js — Table of contents (global: window.Toc)
   ============================================================ */

(function() {
    const T = {};

    function escapeTitle(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    T.buildTocTree = function(tocData, container, onNavigate) {
        container.innerHTML = '';

        tocData.forEach((chapter, chIdx) => {
            const chDiv = document.createElement('div');
            chDiv.className = 'toc-chapter';

            const header = document.createElement('div');
            header.className = 'toc-chapter-header';
            header.dataset.chapterId = chapter.id;
            header.innerHTML = '<span class="toggle-icon">▾</span><span>' + escapeTitle(chapter.title) + '</span>';
            header.addEventListener('click', function() { T.toggleChapter(header); });

            const sectionList = document.createElement('div');
            sectionList.className = 'toc-section-list';

            chapter.sections.forEach(function(section) {
                const secWrapper = document.createElement('div');
                secWrapper.className = 'toc-section-wrapper';

                const hasHeadings = section.headings && section.headings.some(function(h) { return h.level <= 2; });

                const secLink = document.createElement('a');
                secLink.className = 'toc-section-item';
                secLink.dataset.sectionId = section.id;
                secLink.dataset.chapterId = chapter.id;
                secLink.textContent = section.title || '文档';
                secLink.href = '#' + section.id;
                secLink.addEventListener('click', function(e) {
                    e.preventDefault();
                    if (hasHeadings) {
                        T.toggleSection(secWrapper);
                    } else {
                        onNavigate({ chapterId: chapter.id, sectionId: section.id });
                    }
                });

                secWrapper.appendChild(secLink);

                var headingList = document.createElement('div');
                headingList.className = 'toc-heading-list';

                section.headings.forEach(function(h) {
                    if (h.level > 2) return;
                    const hLink = document.createElement('a');
                    hLink.className = 'toc-heading-item';
                    hLink.dataset.sectionId = section.id;
                    hLink.dataset.headingId = h.id;
                    hLink.textContent = h.text;
                    hLink.href = '#' + section.id;
                    hLink.addEventListener('click', function(e) {
                        e.preventDefault();
                        onNavigate({ chapterId: chapter.id, sectionId: section.id });
                        setTimeout(function() {
                            const el = document.getElementById(h.id);
                            if (el) el.scrollIntoView({ behavior: 'smooth' });
                        }, 200);
                    });
                    headingList.appendChild(hLink);
                });

                secWrapper.appendChild(headingList);
                sectionList.appendChild(secWrapper);
            });

            chDiv.appendChild(header);
            chDiv.appendChild(sectionList);
            container.appendChild(chDiv);

            if (chIdx > 0) {
                header.classList.add('collapsed');
                sectionList.classList.add('collapsed');
            }
        });
    };

    T.toggleChapter = function(header) {
        header.classList.toggle('collapsed');
        const list = header.nextElementSibling;
        if (list) list.classList.toggle('collapsed');
    };

    T.toggleSection = function(wrapper) {
        wrapper.classList.toggle('collapsed');
    };

    T.setActiveTocItem = function(sectionId) {
        document.querySelectorAll('.toc-section-item.active, .toc-chapter-header.active').forEach(function(el) {
            el.classList.remove('active');
        });
        const sectionEl = document.querySelector('.toc-section-item[data-section-id="' + sectionId + '"]');
        if (sectionEl) {
            sectionEl.classList.add('active');
            // Expand parent chapter
            const chapterHeader = sectionEl.closest('.toc-chapter');
            if (chapterHeader) {
                const header = chapterHeader.querySelector('.toc-chapter-header');
                if (header) header.classList.add('active');
            }
            const sectionList = sectionEl.closest('.toc-section-list');
            if (sectionList && sectionList.classList.contains('collapsed')) {
                sectionList.classList.remove('collapsed');
                if (sectionList.previousElementSibling) {
                    sectionList.previousElementSibling.classList.remove('collapsed');
                }
            }
            // Expand parent section wrapper
            const secWrapper = sectionEl.closest('.toc-section-wrapper');
            if (secWrapper && secWrapper.classList.contains('collapsed')) {
                T.toggleSection(secWrapper);
            }
        }
    };

    T.setupScrollSpy = function(onSectionChange) {
        let currentSection = null;
        const handleScroll = Utils.throttle(function() {
            const sections = document.querySelectorAll('.content-section.active');
            if (sections.length === 0) return;
            const sectionId = sections[0].id;
            if (sectionId !== currentSection) {
                currentSection = sectionId;
                T.setActiveTocItem(sectionId);
                if (onSectionChange) onSectionChange(sectionId);
            }
        }, 150);
        window.addEventListener('scroll', handleScroll, { passive: true });
    };

    window.Toc = T;
})();
