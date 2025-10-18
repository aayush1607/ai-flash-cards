// AIFlash Frontend Application
class AIFlashApp {
    constructor() {
        this.currentCards = [];
        this.currentIndex = 0;
        this.isTopicView = false;
        this.currentTopic = '';
        this.isLoading = false;
        this.retryCount = 0;
        this.maxRetries = 3;
        this.retryDelay = 1000; // 1 second
        
        // Initialize the application
        this.init();
    }

    async init() {
        try {
            // Setup event listeners
            this.setupEventListeners();
            
            // Load initial morning brief
            await this.loadMorningBrief();
            
            // Show keyboard shortcuts help
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
        document.getElementById('nextBtn').addEventListener('click', () => this.nextCard());
        document.getElementById('prevBtn').addEventListener('click', () => this.prevCard());
        document.getElementById('nextBtnNav').addEventListener('click', () => this.nextCard());

        // Modal controls
        document.getElementById('closeModal').addEventListener('click', () => this.closeModal());
        document.getElementById('modalCloseBtn').addEventListener('click', () => this.closeModal());
        document.getElementById('cardModal').addEventListener('click', (e) => {
            if (e.target.id === 'cardModal') {
                this.closeModal();
            }
        });

        // Topic view controls
        document.getElementById('refreshBtn').addEventListener('click', () => this.refreshTopic());

        // Retry button
        document.getElementById('retryBtn').addEventListener('click', () => this.retry());

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboard(e));

        // Status indicator
        this.updateStatusIndicator();
    }

    async loadMorningBrief() {
        try {
            this.showLoading();
            this.isLoading = true;

            const response = await fetch('/api/morning-brief');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            this.currentCards = data.items || [];
            this.currentIndex = 0;
            this.isTopicView = false;

            if (this.currentCards.length === 0) {
                this.showEmpty();
            } else {
                this.renderCurrentCard();
                this.hideLoading();
            }

        } catch (error) {
            console.error('Error loading morning brief:', error);
            this.showError('Failed to load morning brief');
        } finally {
            this.isLoading = false;
        }
    }

    async handleSearch() {
        const searchInput = document.getElementById('searchInput');
        const query = searchInput.value.trim();

        console.log('Search triggered for:', query);

        if (!query) {
            return;
        }

        try {
            this.showLoading();
            this.isLoading = true;

            console.log('Making API request...');
            const response = await fetch(`/api/topic-feed?q=${encodeURIComponent(query)}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            console.log('Search results:', data);
            
            this.currentCards = data.items || [];
            this.currentIndex = 0;
            this.isTopicView = true;
            this.currentTopic = query;

            // Show topic header
            this.showTopicHeader(data);

            if (this.currentCards.length === 0) {
                this.showEmpty();
            } else {
                console.log('Rendering card:', this.currentCards[0]);
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

    async refreshTopic() {
        if (!this.isTopicView || !this.currentTopic) {
            return;
        }

        // If we're in topic view, go back to morning brief
        this.clearSearch();
    }

    clearSearch() {
        // Clear search input
        const searchInput = document.getElementById('searchInput');
        searchInput.value = '';
        
        // Reset to morning brief view
        this.isTopicView = false;
        this.currentTopic = '';
        this.hideTopicHeader();
        
        // Load morning brief
        this.loadMorningBrief();
    }

    renderCurrentCard() {
        if (this.currentCards.length === 0) {
            this.showEmpty();
            return;
        }

        const card = this.currentCards[this.currentIndex];
        this.renderCard(card);
        this.updateCardCounter();
        this.hideAllStates();
    }

    renderCard(card) {
        // Basic information
        document.getElementById('cardSource').textContent = card.source;
        document.getElementById('cardDate').textContent = this.formatDate(card.published_at);
        document.getElementById('cardTitle').textContent = card.title;
        document.getElementById('cardTldr').textContent = card.tl_dr;
        document.getElementById('cardSummary').textContent = card.summary;
        document.getElementById('cardWhy').textContent = card.why_it_matters;

        // Synthesis warning
        const synthesisWarning = document.getElementById('synthesisWarning');
        if (card.synthesis_failed) {
            synthesisWarning.classList.remove('hidden');
        } else {
            synthesisWarning.classList.add('hidden');
        }

        // Badges
        this.renderBadges(card.badges);

        // Tags
        this.renderTags(card.tags);

        // References
        this.renderReferences(card.references);

        // Show card
        document.getElementById('currentCard').classList.remove('hidden');
        document.getElementById('cardNavigation').classList.remove('hidden');
    }

    renderBadges(badges) {
        const badgesContainer = document.getElementById('cardBadges');
        badgesContainer.innerHTML = '';

        badges.forEach(badge => {
            const badgeElement = document.createElement('span');
            badgeElement.className = 'px-2 py-1 bg-purple-600/20 text-purple-300 rounded text-xs font-medium';
            badgeElement.textContent = badge;
            badgesContainer.appendChild(badgeElement);
        });
    }

    renderTags(tags) {
        const tagsContainer = document.getElementById('cardTags');
        tagsContainer.innerHTML = '';

        tags.forEach(tag => {
            const tagElement = document.createElement('span');
            tagElement.className = 'px-3 py-1 bg-white/10 text-white/80 rounded-full text-sm';
            tagElement.textContent = tag;
            tagsContainer.appendChild(tagElement);
        });
    }

    renderReferences(references) {
        const referencesContainer = document.getElementById('cardReferences');
        referencesContainer.innerHTML = '';

        references.forEach(ref => {
            const refElement = document.createElement('a');
            refElement.href = ref.url;
            refElement.target = '_blank';
            refElement.rel = 'noopener noreferrer';
            refElement.className = 'px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg transition-colors border border-white/20 text-sm';
            refElement.textContent = ref.label;
            referencesContainer.appendChild(refElement);
        });
    }

    nextCard() {
        if (this.currentCards.length === 0) return;

        this.currentIndex = (this.currentIndex + 1) % this.currentCards.length;
        this.renderCurrentCard();
    }

    prevCard() {
        if (this.currentCards.length === 0) return;

        this.currentIndex = this.currentIndex === 0 ? this.currentCards.length - 1 : this.currentIndex - 1;
        this.renderCurrentCard();
    }


    showModal(card) {
        // Set modal content
        document.getElementById('modalTitle').textContent = card.title;
        document.getElementById('modalSummary').textContent = card.summary;
        document.getElementById('modalWhy').textContent = card.why_it_matters;

        // Show snippet if available
        const snippetDiv = document.getElementById('modalSnippet');
        const snippetText = document.getElementById('modalSnippetText');
        if (card.snippet) {
            snippetText.textContent = card.snippet;
            snippetDiv.classList.remove('hidden');
        } else {
            snippetDiv.classList.add('hidden');
        }

        // Render modal references
        this.renderModalReferences(card.references);

        // Show modal
        document.getElementById('cardModal').classList.remove('hidden');
    }

    renderModalReferences(references) {
        const referencesContainer = document.getElementById('modalReferences');
        referencesContainer.innerHTML = '';

        references.forEach(ref => {
            const refElement = document.createElement('a');
            refElement.href = ref.url;
            refElement.target = '_blank';
            refElement.rel = 'noopener noreferrer';
            refElement.className = 'block p-4 bg-white/5 hover:bg-white/10 rounded-lg transition-colors border border-white/20';
            refElement.innerHTML = `
                <div class="font-medium text-white">${ref.label}</div>
                <div class="text-white/60 text-sm mt-1">${ref.url}</div>
            `;
            referencesContainer.appendChild(refElement);
        });
    }

    closeModal() {
        document.getElementById('cardModal').classList.add('hidden');
    }

    updateCardCounter() {
        const counter = document.getElementById('cardCounter');
        counter.textContent = `${this.currentIndex + 1} of ${this.currentCards.length}`;
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
                this.prevCard();
                break;
            case 'ArrowRight':
                e.preventDefault();
                this.nextCard();
                break;
            case 'Escape':
                e.preventDefault();
                this.closeModal();
                break;
        }
    }

    showLoading() {
        document.getElementById('loadingState').classList.remove('hidden');
        this.hideAllStates();
    }

    hideLoading() {
        document.getElementById('loadingState').classList.add('hidden');
    }

    showError(message) {
        document.getElementById('errorMessage').textContent = message;
        document.getElementById('errorState').classList.remove('hidden');
        this.hideAllStates();
    }

    showEmpty() {
        document.getElementById('emptyState').classList.remove('hidden');
        this.hideAllStates();
    }

    hideAllStates() {
        document.getElementById('loadingState').classList.add('hidden');
        document.getElementById('errorState').classList.add('hidden');
        document.getElementById('emptyState').classList.add('hidden');
    }

    async retry() {
        if (this.isTopicView) {
            await this.handleSearch();
        } else {
            await this.loadMorningBrief();
        }
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }

    updateStatusIndicator() {
        const indicator = document.getElementById('statusIndicator');
        const statusText = indicator.nextElementSibling;

        // Check API health
        fetch('/api/health')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'healthy') {
                    indicator.className = 'w-3 h-3 bg-green-500 rounded-full animate-pulse';
                    statusText.textContent = 'Live';
                } else {
                    indicator.className = 'w-3 h-3 bg-yellow-500 rounded-full animate-pulse';
                    statusText.textContent = 'Issues';
                }
            })
            .catch(() => {
                indicator.className = 'w-3 h-3 bg-red-500 rounded-full animate-pulse';
                statusText.textContent = 'Offline';
            });
    }

    showKeyboardHelp() {
        const help = document.getElementById('keyboardHelp');
        
        // Show help for 3 seconds on load
        help.classList.remove('hidden');
        setTimeout(() => {
            help.classList.add('hidden');
        }, 3000);
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.aiflashApp = new AIFlashApp();
});

// Export for potential module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AIFlashApp;
}
