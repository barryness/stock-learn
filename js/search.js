/* ============================================================
   search.js — Search engine (global: window.Search)
   ============================================================ */

(function() {
    const S = {};
    let searchIndex = [];

    S.buildIndex = function(contentMap) {
        searchIndex = [];
        for (const sectionId in contentMap) {
            if (!contentMap.hasOwnProperty(sectionId)) continue;
            const data = contentMap[sectionId];
            const text = data.markdown || '';
            const plainText = text
                .replace(/```[\s\S]*?```/g, ' ')
                .replace(/`[^`]+`/g, ' ')
                .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
                .replace(/[#*>\-|]/g, ' ')
                .replace(/\s+/g, ' ')
                .toLowerCase();

            searchIndex.push({
                sectionId: sectionId,
                chapterTitle: (data.chapterTitle || '').toLowerCase(),
                sectionTitle: (data.sectionTitle || '').toLowerCase(),
                text: plainText,
                excerpt: plainText.substring(0, 300),
            });
        }
    };

    S.search = function(query, maxResults) {
        maxResults = maxResults || 15;
        if (!query || query.trim().length < 2) return [];

        const terms = query.toLowerCase().trim().split(/\s+/);
        const results = [];

        for (let i = 0; i < searchIndex.length; i++) {
            const entry = searchIndex[i];
            let score = 0;
            const matches = [];

            for (let t = 0; t < terms.length; t++) {
                const term = terms[t];
                if (entry.sectionTitle.indexOf(term) !== -1) { score += 10; matches.push('标题: ' + term); }
                if (entry.chapterTitle.indexOf(term) !== -1) { score += 5; matches.push('章节: ' + term); }

                let pos = 0;
                while ((pos = entry.text.indexOf(term, pos)) !== -1) {
                    score += 1;
                    pos += term.length;
                }
            }

            if (score > 0) {
                let excerpt = entry.excerpt;
                if (matches.length === 0 && terms.length > 0) {
                    const idx = entry.text.indexOf(terms[0]);
                    if (idx >= 0) {
                        const start = Math.max(0, idx - 80);
                        const end = Math.min(entry.text.length, idx + terms[0].length + 120);
                        excerpt = (start > 0 ? '...' : '') + entry.text.substring(start, end) + (end < entry.text.length ? '...' : '');
                    }
                }
                results.push({
                    sectionId: entry.sectionId,
                    chapterTitle: entry.chapterTitle,
                    sectionTitle: entry.sectionTitle,
                    excerpt: excerpt,
                    score: score,
                    matches: Array.from(new Set(matches)),
                });
            }
        }

        results.sort(function(a, b) { return b.score - a.score; });
        const seen = new Set();
        const unique = [];
        for (let i = 0; i < results.length; i++) {
            if (!seen.has(results[i].sectionId)) {
                seen.add(results[i].sectionId);
                unique.push(results[i]);
            }
        }
        return unique.slice(0, maxResults);
    };

    S.renderResults = function(results, container, onSelect) {
        container.innerHTML = '';
        if (results.length === 0) {
            container.innerHTML = '<div class="search-result-item" style="color:var(--color-text-secondary)">未找到结果</div>';
            return;
        }
        results.forEach(function(r) {
            const item = document.createElement('div');
            item.className = 'search-result-item';
            const titleDiv = document.createElement('div');
            titleDiv.className = 'title';
            titleDiv.textContent = r.sectionTitle;
            const chapterDiv = document.createElement('div');
            chapterDiv.className = 'chapter';
            chapterDiv.textContent = r.chapterTitle;
            item.appendChild(titleDiv);
            item.appendChild(chapterDiv);
            item.addEventListener('click', function() { onSelect(r); });
            container.appendChild(item);
        });
    };

    window.Search = S;
})();
