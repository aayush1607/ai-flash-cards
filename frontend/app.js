// AI Flash Cards Frontend Application
class AIFlashApp {
    constructor() {
        this.currentCards = [];
        this.currentIndex = 0;
        this.isTopicView = false;
        this.currentTopic = '';
        this.isLoading = false;
        this.init();
    }

    async init() {
        try {
            this.setupEventListeners();
            await this.loadMorningBrief();
            this.showKeyboardHelp();
        } catch (error) {
            console.error('Error initializing app:', error);
            this.showError('Failed to initialize application');
        }
    }

    setupEventListeners() {
        // Search functionality
        const searchInput = document.getElementById('searchInput');
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                e.stopPropagation();
                this.handleSearch();
            }
        });

        // Card navigation
        document.getElementById('nextButton').addEventListener('click', () => this.navigateCards(1));
        document.getElementById('prevButton').addEventListener('click', () => this.navigateCards(-1));

        // Touch/swipe support for mobile
        this.setupTouchEvents();

        // Modal controls
        document.getElementById('cardModal').addEventListener('click', (e) => {
            if (e.target.id === 'cardModal' || e.target.classList.contains('modal-close')) {
                this.closeCardModal();
            }
        });

        // Topic view controls
        document.getElementById('refreshBtn').addEventListener('click', () => this.clearSearch());

        // Retry button
        document.getElementById('retryBtn').addEventListener('click', () => this.retry());

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboard(e));
    }

    setupTouchEvents() {
        const cardContainer = document.getElementById('cardContainer');
        let startX = 0;
        let startY = 0;
        let endX = 0;
        let endY = 0;

        cardContainer.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
        }, { passive: true });

        cardContainer.addEventListener('touchend', (e) => {
            endX = e.changedTouches[0].clientX;
            endY = e.changedTouches[0].clientY;
            
            const deltaX = endX - startX;
            const deltaY = endY - startY;
            
            // Only trigger swipe if horizontal movement is greater than vertical
            if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 50) {
                if (deltaX > 0) {
                    // Swipe right - previous card
                    this.navigateCards(-1);
                } else {
                    // Swipe left - next card
                    this.navigateCards(1);
                }
            }
        }, { passive: true });
    }

    async loadMorningBrief() {
        if (this.isLoading) return;
        try {
            this.showLoading();
            this.isLoading = true;
            this.isTopicView = false;
            this.currentTopic = '';
            this.hideTopicHeader();

            const response = await fetch('/api/morning-brief');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            const data = await response.json();
            this.currentCards = data.items || [];
            this.currentIndex = 0;
            this.renderCurrentCard();
        } catch (error) {
            console.error('Error loading morning brief:', error);
            this.showError('Failed to load morning brief');
        } finally {
            this.isLoading = false;
            this.hideLoading();
        }
    }

    async handleSearch() {
        const searchInput = document.getElementById('searchInput');
        const query = searchInput.value.trim();

        if (!query) {
            return;
        }

        try {
            this.showLoading();
            this.isLoading = true;

            const response = await fetch(`/api/topic-feed?q=${encodeURIComponent(query)}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            this.currentCards = data.items || [];
            this.currentIndex = 0;
            this.isTopicView = true;
            this.currentTopic = query;

            // Show topic header
            this.showTopicHeader(data);

            if (this.currentCards.length === 0) {
                this.showEmpty();
            } else {
                this.renderCurrentCard();
                this.hideLoading();
            }

        } catch (error) {
            console.error('Error searching:', error);
            this.showError('Failed to search topics');
        } finally {
            this.isLoading = false;
        }
    }

    clearSearch() {
        const searchInput = document.getElementById('searchInput');
        searchInput.value = '';
        
        this.isTopicView = false;
        this.currentTopic = '';
        this.hideTopicHeader();
        
        this.loadMorningBrief();
    }

    renderCurrentCard() {
        const cardContainer = document.getElementById('cardContainer');
        cardContainer.innerHTML = '';

        if (this.currentCards.length === 0) {
            this.showEmpty();
            return;
        }

        const card = this.currentCards[this.currentIndex];
        if (!card) {
            this.showEmpty();
            return;
        }

        // Create card element
        const cardElement = document.createElement('div');
        cardElement.className = 'card card-hover';
        
        // Build references HTML
        let referencesHtml = '';
        if (card.references && card.references.length > 0) {
            referencesHtml = `
                <div class="card-references">
                    <div class="card-references-label">References</div>
                    <div class="card-references-list">
                        ${card.references.map(ref => `
                            <a href="${ref.url}" target="_blank" class="card-reference-link">
                                ${ref.label}
                            </a>
                        `).join('')}
                    </div>
                </div>
            `;
        }
        
        cardElement.innerHTML = `
            <div class="card-header">
                <span class="card-source">${card.source}</span>
                <span class="card-date">${this.formatDate(card.published_at)}</span>
            </div>
            <div class="card-content">
                <div class="card-title">${card.title}</div>
                <div class="card-tldr">${card.tl_dr}</div>
                <div class="card-summary">${card.summary}</div>
                <div class="card-footer">
                    <div class="card-why-label">Why it matters</div>
                    <div class="card-why-text">${card.why_it_matters}</div>
                </div>
                ${referencesHtml}
            </div>
        `;
        cardContainer.appendChild(cardElement);

        this.updateCardCounter();
        this.hideAllStates();
    }

    navigateCards(direction) {
        if (this.isLoading || this.currentCards.length === 0) return;

        this.currentIndex = (this.currentIndex + direction + this.currentCards.length) % this.currentCards.length;
        this.renderCurrentCard();
    }

    showCardModal(card) {
        document.getElementById('modalSource').textContent = card.source;
        document.getElementById('modalDate').textContent = this.formatDate(card.published_at);
        document.getElementById('modalTitle').textContent = card.title;
        document.getElementById('modalTldr').textContent = card.tl_dr;
        document.getElementById('modalSummary').textContent = card.summary;
        document.getElementById('modalWhy').textContent = card.why_it_matters;

        // Handle snippet visibility
        const modalSnippetDiv = document.getElementById('modalSnippet');
        const modalSnippetText = document.getElementById('modalSnippetText');
        if (card.snippet) {
            modalSnippetDiv.classList.remove('hidden');
            modalSnippetText.textContent = card.snippet;
        } else {
            modalSnippetDiv.classList.add('hidden');
            modalSnippetText.textContent = '';
        }

        // Handle synthesis warning
        const synthesisWarning = document.getElementById('synthesisWarning');
        if (card.synthesis_failed) {
            synthesisWarning.classList.remove('hidden');
        } else {
            synthesisWarning.classList.add('hidden');
        }

        // Render references
        const modalReferences = document.getElementById('modalReferences');
        modalReferences.innerHTML = '';
        if (card.references && card.references.length > 0) {
            card.references.forEach(ref => {
                const li = document.createElement('li');
                const a = document.createElement('a');
                a.href = ref.url;
                a.textContent = ref.label;
                a.target = '_blank';
                li.appendChild(a);
                modalReferences.appendChild(li);
            });
        } else {
            modalReferences.innerHTML = '<li>No references available.</li>';
        }

        // Render badges
        const modalBadges = document.getElementById('modalBadges');
        modalBadges.innerHTML = '';
        if (card.badges && card.badges.length > 0) {
            card.badges.forEach(badge => {
                const span = document.createElement('span');
                span.className = 'badge';
                span.textContent = badge;
                modalBadges.appendChild(span);
            });
        }

        // Render tags
        const modalTags = document.getElementById('modalTags');
        modalTags.innerHTML = '';
        if (card.tags && card.tags.length > 0) {
            card.tags.forEach(tag => {
                const span = document.createElement('span');
                span.className = 'tag';
                span.textContent = tag;
                modalTags.appendChild(span);
            });
        }

        document.getElementById('cardModal').classList.remove('hidden');
    }

    closeCardModal() {
        document.getElementById('cardModal').classList.add('hidden');
    }

    formatDate(dateString) {
        const options = { year: 'numeric', month: 'short', day: 'numeric' };
        return new Date(dateString).toLocaleDateString(undefined, options);
    }

    showLoading() {
        document.getElementById('loadingState').classList.remove('hidden');
        this.hideAllStates();
    }

    hideLoading() {
        document.getElementById('loadingState').classList.add('hidden');
    }

    showEmpty() {
        document.getElementById('emptyState').classList.remove('hidden');
        this.hideAllStates();
    }

    hideEmpty() {
        document.getElementById('emptyState').classList.add('hidden');
    }

    showError(message) {
        document.getElementById('errorMessage').textContent = message;
        document.getElementById('errorState').classList.remove('hidden');
        this.hideAllStates();
    }

    hideError() {
        document.getElementById('errorState').classList.add('hidden');
    }

    hideAllStates() {
        const states = ['loadingState', 'emptyState', 'errorState'];
        states.forEach(stateId => {
            document.getElementById(stateId).classList.add('hidden');
        });
    }

    showTopicHeader(data) {
        const topicHeader = document.getElementById('topicHeader');
        const topicTitle = document.getElementById('topicTitle');
        const topicSummary = document.getElementById('topicSummary');
        const topicWhy = document.getElementById('topicWhy');

        topicTitle.textContent = `"${data.topic_query}"`;
        topicSummary.textContent = data.topic_summary;
        topicWhy.textContent = data.why_it_matters;
        topicHeader.classList.remove('hidden');
    }

    hideTopicHeader() {
        const topicHeader = document.getElementById('topicHeader');
        topicHeader.classList.add('hidden');
    }

    handleKeyboard(e) {
        if (this.isLoading) return;
        
        // Don't intercept keyboard events when search input is focused
        const searchInput = document.getElementById('searchInput');
        if (document.activeElement === searchInput) {
            return;
        }

        switch (e.key) {
            case 'ArrowLeft':
                e.preventDefault();
                this.navigateCards(-1);
                break;
            case 'ArrowRight':
                e.preventDefault();
                this.navigateCards(1);
                break;
            case 'Escape':
                e.preventDefault();
                this.closeCardModal();
                break;
        }
    }

    showKeyboardHelp() {
        document.getElementById('keyboardHelp').classList.remove('hidden');
    }

    hideKeyboardHelp() {
        document.getElementById('keyboardHelp').classList.add('hidden');
    }

    retry() {
        this.loadMorningBrief();
    }

    updateCardCounter() {
        const counter = document.getElementById('cardCounter');
        counter.textContent = `${this.currentIndex + 1} of ${this.currentCards.length}`;
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new AIFlashApp();
});