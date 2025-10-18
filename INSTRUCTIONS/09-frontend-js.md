# Todo 9: Frontend JavaScript Functionality

## Objective
Implement comprehensive JavaScript functionality for card rendering, navigation, API integration, and user interactions with proper error handling and state management.

## Files to Create

### 1. `frontend/app.js`
Create the complete JavaScript application:

```javascript
// AIFlash Frontend Application
class AIFlashApp {
    constructor() {
        this.currentCards = [];
        this.currentIndex = 0;
        this.isTopicView = false;
        this.currentTopic = '';
        this.currentTimeframe = '30d';
        this.isLoading = false;
        
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
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.handleSearch();
            }
        });

        // Card navigation
        document.getElementById('nextBtn').addEventListener('click', () => this.nextCard());
        document.getElementById('openBtn').addEventListener('click', () => this.openCard());
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
        document.getElementById('timeframeSelect').addEventListener('change', (e) => {
            this.currentTimeframe = e.target.value;
            this.refreshTopic();
        });

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

        if (!query) {
            return;
        }

        try {
            this.showLoading();
            this.isLoading = true;

            const response = await fetch(`/api/topic-feed?q=${encodeURIComponent(query)}&timeframe=${this.currentTimeframe}`);
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

        await this.handleSearch();
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

    openCard() {
        if (this.currentCards.length === 0) return;

        const card = this.currentCards[this.currentIndex];
        this.showModal(card);
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

        switch (e.key) {
            case 'ArrowLeft':
                e.preventDefault();
                this.prevCard();
                break;
            case 'ArrowRight':
                e.preventDefault();
                this.openCard();
                break;
            case 'Enter':
                e.preventDefault();
                this.openCard();
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
```

## Key Features to Implement

### 1. Application State Management
- **Current Cards**: Array of loaded cards
- **Current Index**: Position in card stack
- **View Mode**: Morning brief vs topic view
- **Loading State**: Prevent actions during loading
- **Error Handling**: Graceful error recovery

### 2. API Integration
- **Morning Brief**: Load daily top articles
- **Topic Search**: Semantic search with topic summarization
- **Error Handling**: HTTP error handling and retry logic
- **Response Processing**: Parse and validate API responses

### 3. Card Rendering
- **Dynamic Content**: Render card data from API
- **Badge Display**: Show content badges (CODE, DATA, etc.)
- **Tag Rendering**: Display topical tags as chips
- **Reference Links**: Create clickable reference buttons
- **Date Formatting**: Human-readable date display

### 4. Navigation System
- **Card Navigation**: Next/previous card functionality
- **Keyboard Shortcuts**: Arrow keys, Enter, Esc
- **Counter Display**: Current position in stack
- **Wrap Around**: Loop to beginning/end of stack

### 5. Modal System
- **Detail View**: Expanded card information
- **Reference Display**: Full reference links
- **Snippet Display**: Content excerpts
- **Close Actions**: Multiple close methods

### 6. Search Functionality
- **Topic Search**: Semantic search with AI summarization
- **Timeframe Filtering**: 24h, 7d, 30d, all time
- **Refresh Capability**: Re-run search with same parameters
- **Topic Header**: Display topic summary and significance

### 7. User Experience
- **Loading States**: Visual feedback during operations
- **Error States**: User-friendly error messages
- **Empty States**: No results messaging
- **Status Indicator**: Live system status
- **Keyboard Help**: Shortcut reminders

## State Management

### 1. Application State
```javascript
{
    currentCards: [],           // Array of card objects
    currentIndex: 0,           // Current card position
    isTopicView: false,        // Morning brief vs topic view
    currentTopic: '',          // Current search topic
    currentTimeframe: '30d',   // Search timeframe
    isLoading: false           // Loading state
}
```

### 2. Card Object Structure
```javascript
{
    content_id: "huggingface:abc123",
    type: "blog",
    title: "New Transformer Architecture",
    source: "Hugging Face",
    published_at: "2024-01-15T10:00:00Z",
    tl_dr: "Novel transformer design reduces parameters by 50%",
    summary: "This paper introduces a new transformer architecture...",
    why_it_matters: "Enables more efficient AI models",
    badges: ["CODE", "DATA"],
    tags: ["transformer", "efficiency"],
    references: [
        {label: "Paper", url: "https://arxiv.org/..."},
        {label: "Code", url: "https://github.com/..."}
    ],
    snippet: "The new architecture uses grouped attention...",
    synthesis_failed: false
}
```

## Error Handling Strategy

### 1. API Errors
- **HTTP Errors**: Handle 400, 404, 500 status codes
- **Network Errors**: Handle connection failures
- **Timeout Errors**: Handle slow responses
- **Retry Logic**: Automatic retry for failed requests

### 2. User Interface Errors
- **Loading States**: Prevent actions during loading
- **Error Messages**: Clear, actionable error messages
- **Fallback Content**: Show partial data when possible
- **Recovery Actions**: Retry buttons and manual refresh

### 3. State Recovery
- **Invalid State**: Reset to known good state
- **Partial Data**: Handle incomplete responses
- **Navigation Errors**: Prevent invalid navigation
- **Modal Errors**: Handle modal display issues

## Performance Optimizations

### 1. API Caching
- **Response Caching**: Cache API responses
- **Debounced Search**: Prevent excessive API calls
- **Lazy Loading**: Load content as needed
- **Efficient Updates**: Update only changed elements

### 2. DOM Optimization
- **Event Delegation**: Efficient event handling
- **Minimal Reflows**: Batch DOM updates
- **Memory Management**: Clean up event listeners
- **Efficient Rendering**: Update only necessary elements

## Validation Checklist
- [ ] All API endpoints are properly integrated
- [ ] Card rendering works for all data types
- [ ] Navigation functions correctly in all directions
- [ ] Modal system displays complete information
- [ ] Search functionality works with all timeframes
- [ ] Error handling covers all failure scenarios
- [ ] Keyboard shortcuts work as expected
- [ ] Loading states provide good user feedback
- [ ] Status indicator shows accurate system health
- [ ] All user interactions are responsive

## Next Steps
After completing this todo, proceed to "10-frontend-styling" to implement the CSS styling and animations.
