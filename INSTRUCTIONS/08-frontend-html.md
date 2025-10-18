# Todo 8: Frontend HTML Structure

## Objective
Create a beautiful, responsive HTML structure for the AIFlash frontend with Tinder-style card interface, search functionality, and modal system.

## Files to Create

### 1. `frontend/index.html`
Create the complete HTML structure:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Flash — research-grade AI breakthroughs & model releases, fast.</title>
    <meta name="description" content="AI Flash delivers daily AI research breakthroughs and model releases in a fast, digestible format.">
    
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    
    <!-- Custom CSS -->
    <link rel="stylesheet" href="styles.css">
    
    <!-- Favicon -->
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⚡</text></svg>">
</head>
<body class="bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 min-h-screen">
    <!-- Header -->
    <header class="bg-black/20 backdrop-blur-md border-b border-white/10 sticky top-0 z-50">
        <div class="max-w-6xl mx-auto px-4 py-4">
            <div class="flex items-center justify-between">
                <!-- Logo -->
                <div class="flex items-center space-x-3">
                    <div class="text-3xl">⚡</div>
                    <h1 class="text-2xl font-bold text-white">AI Flash</h1>
                </div>
                
                <!-- Search Input -->
                <div class="flex-1 max-w-2xl mx-8">
                    <div class="relative">
                        <input 
                            type="text" 
                            id="searchInput" 
                            placeholder="Let's learn today about ____ in a flash!"
                            class="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                            autocomplete="off"
                        >
                        <div class="absolute right-3 top-1/2 transform -translate-y-1/2">
                            <svg class="w-5 h-5 text-white/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                            </svg>
                        </div>
                    </div>
                </div>
                
                <!-- Status Indicator -->
                <div class="flex items-center space-x-2">
                    <div id="statusIndicator" class="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                    <span class="text-sm text-white/60">Live</span>
                </div>
            </div>
        </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-6xl mx-auto px-4 py-8">
        <!-- Topic Header (hidden by default) -->
        <div id="topicHeader" class="hidden mb-8 bg-white/5 backdrop-blur-sm rounded-xl p-6 border border-white/10">
            <div class="flex items-center justify-between mb-4">
                <h2 id="topicTitle" class="text-2xl font-bold text-white"></h2>
                <div class="flex items-center space-x-2">
                    <button id="refreshBtn" class="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors">
                        Refresh
                    </button>
                    <select id="timeframeSelect" class="px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white">
                        <option value="24h">Last 24h</option>
                        <option value="7d">Last 7 days</option>
                        <option value="30d" selected>Last 30 days</option>
                        <option value="all">All time</option>
                    </select>
                </div>
            </div>
            <p id="topicSummary" class="text-white/80 mb-2"></p>
            <p id="topicWhy" class="text-purple-300 font-medium"></p>
        </div>

        <!-- Card Container -->
        <div class="relative">
            <!-- Loading State -->
            <div id="loadingState" class="hidden text-center py-20">
                <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
                <p class="text-white/60 mt-4">Loading AI insights...</p>
            </div>

            <!-- Error State -->
            <div id="errorState" class="hidden text-center py-20">
                <div class="text-red-400 text-6xl mb-4">⚠️</div>
                <h3 class="text-xl font-semibold text-white mb-2">Something went wrong</h3>
                <p id="errorMessage" class="text-white/60 mb-4"></p>
                <button id="retryBtn" class="px-6 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors">
                    Try Again
                </button>
            </div>

            <!-- Empty State -->
            <div id="emptyState" class="hidden text-center py-20">
                <div class="text-white/40 text-6xl mb-4">📰</div>
                <h3 class="text-xl font-semibold text-white mb-2">No articles found</h3>
                <p class="text-white/60">Try a different search term or check back later</p>
            </div>

            <!-- Card Stack -->
            <div id="cardContainer" class="relative">
                <!-- Single Card (Tinder-style) -->
                <div id="currentCard" class="hidden card-stack">
                    <div class="bg-white/10 backdrop-blur-sm rounded-2xl p-8 border border-white/20 shadow-2xl min-h-[600px] flex flex-col">
                        <!-- Card Header -->
                        <div class="flex items-center justify-between mb-6">
                            <div class="flex items-center space-x-3">
                                <span id="cardSource" class="px-3 py-1 bg-purple-600/20 text-purple-300 rounded-full text-sm font-medium"></span>
                                <span id="cardDate" class="text-white/60 text-sm"></span>
                            </div>
                            <div id="cardBadges" class="flex space-x-2"></div>
                        </div>

                        <!-- Card Title -->
                        <h3 id="cardTitle" class="text-2xl font-bold text-white mb-4 leading-tight"></h3>

                        <!-- TL;DR -->
                        <div class="mb-6">
                            <div class="flex items-center space-x-2 mb-2">
                                <span class="text-sm font-semibold text-purple-300 uppercase tracking-wide">TL;DR</span>
                                <div id="synthesisWarning" class="hidden text-yellow-400 text-sm">⚠️ Limited evidence</div>
                            </div>
                            <p id="cardTldr" class="text-lg text-white/90 font-medium"></p>
                        </div>

                        <!-- Summary -->
                        <div class="mb-6">
                            <h4 class="text-sm font-semibold text-purple-300 uppercase tracking-wide mb-2">Summary</h4>
                            <p id="cardSummary" class="text-white/80 leading-relaxed"></p>
                        </div>

                        <!-- Why It Matters -->
                        <div class="mb-6">
                            <h4 class="text-sm font-semibold text-purple-300 uppercase tracking-wide mb-2">Why It Matters</h4>
                            <p id="cardWhy" class="text-white/80 font-medium"></p>
                        </div>

                        <!-- Tags -->
                        <div class="mb-6">
                            <div id="cardTags" class="flex flex-wrap gap-2"></div>
                        </div>

                        <!-- References -->
                        <div class="mb-8">
                            <h4 class="text-sm font-semibold text-purple-300 uppercase tracking-wide mb-3">References</h4>
                            <div id="cardReferences" class="flex flex-wrap gap-3"></div>
                        </div>

                        <!-- Card Actions -->
                        <div class="flex space-x-4 mt-auto">
                            <button id="nextBtn" class="flex-1 px-6 py-3 bg-white/10 hover:bg-white/20 text-white rounded-lg transition-colors border border-white/20">
                                Next
                            </button>
                            <button id="openBtn" class="flex-1 px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors font-medium">
                                Open
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Card Navigation -->
                <div id="cardNavigation" class="hidden mt-8 text-center">
                    <div class="flex items-center justify-center space-x-4">
                        <button id="prevBtn" class="p-3 bg-white/10 hover:bg-white/20 text-white rounded-full transition-colors">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
                            </svg>
                        </button>
                        <span id="cardCounter" class="text-white/60 text-sm"></span>
                        <button id="nextBtnNav" class="p-3 bg-white/10 hover:bg-white/20 text-white rounded-full transition-colors">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <!-- Card Detail Modal -->
    <div id="cardModal" class="hidden fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div class="bg-white/10 backdrop-blur-md rounded-2xl p-8 border border-white/20 shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <!-- Modal Header -->
            <div class="flex items-center justify-between mb-6">
                <h3 id="modalTitle" class="text-2xl font-bold text-white"></h3>
                <button id="closeModal" class="p-2 hover:bg-white/10 rounded-lg transition-colors">
                    <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>

            <!-- Modal Content -->
            <div id="modalContent" class="space-y-6">
                <!-- Summary -->
                <div>
                    <h4 class="text-lg font-semibold text-purple-300 mb-3">Summary</h4>
                    <p id="modalSummary" class="text-white/80 leading-relaxed"></p>
                </div>

                <!-- Why It Matters -->
                <div>
                    <h4 class="text-lg font-semibold text-purple-300 mb-3">Why It Matters</h4>
                    <p id="modalWhy" class="text-white/80 font-medium"></p>
                </div>

                <!-- Snippet -->
                <div id="modalSnippet" class="hidden">
                    <h4 class="text-lg font-semibold text-purple-300 mb-3">Excerpt</h4>
                    <p id="modalSnippetText" class="text-white/80 leading-relaxed bg-white/5 p-4 rounded-lg"></p>
                </div>

                <!-- References -->
                <div>
                    <h4 class="text-lg font-semibold text-purple-300 mb-3">References</h4>
                    <div id="modalReferences" class="space-y-3"></div>
                </div>
            </div>

            <!-- Modal Actions -->
            <div class="flex justify-end mt-8">
                <button id="modalCloseBtn" class="px-6 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors">
                    Close
                </button>
            </div>
        </div>
    </div>

    <!-- Keyboard Shortcuts Help -->
    <div id="keyboardHelp" class="hidden fixed bottom-4 right-4 bg-black/80 backdrop-blur-sm rounded-lg p-4 border border-white/20 text-white text-sm">
        <div class="flex items-center space-x-2 mb-2">
            <span class="font-semibold">Keyboard Shortcuts:</span>
        </div>
        <div class="space-y-1 text-white/80">
            <div>← <span class="text-white/60">Previous card</span></div>
            <div>→ <span class="text-white/60">Open card</span></div>
            <div>Enter <span class="text-white/60">Open card</span></div>
            <div>Esc <span class="text-white/60">Close modal</span></div>
        </div>
    </div>

    <!-- JavaScript -->
    <script src="app.js"></script>
</body>
</html>
```

## Key Features to Implement

### 1. Header Section
- **Logo**: AI Flash branding with lightning bolt icon
- **Search Input**: Prominent search bar with placeholder text
- **Status Indicator**: Live status indicator
- **Responsive Design**: Mobile-friendly layout

### 2. Main Content Area
- **Topic Header**: Hidden by default, shows for topic searches
- **Card Container**: Single card display (Tinder-style)
- **Loading States**: Spinner and loading messages
- **Error States**: Error handling with retry options
- **Empty States**: No results messaging

### 3. Card Structure
- **Card Header**: Source, date, and badges
- **Title**: Article title
- **TL;DR**: One-sentence summary with warning indicator
- **Summary**: 2-3 sentence explanation
- **Why It Matters**: Significance statement
- **Tags**: Topical tags as chips
- **References**: Link buttons for papers, code, etc.
- **Actions**: Next and Open buttons

### 4. Modal System
- **Detail Modal**: Expanded card information
- **Full Summary**: Complete article summary
- **Snippet**: Content excerpt
- **References**: All reference links
- **Close Actions**: Multiple close options

### 5. Navigation Elements
- **Card Navigation**: Previous/Next buttons
- **Counter**: Current card position
- **Keyboard Shortcuts**: Arrow keys, Enter, Esc
- **Help Display**: Keyboard shortcuts help

## HTML Structure Breakdown

### 1. Document Head
- **Meta Tags**: SEO and viewport configuration
- **Title**: Descriptive page title
- **Tailwind CSS**: CDN for styling
- **Custom CSS**: Additional styling
- **Favicon**: Lightning bolt emoji

### 2. Header Layout
- **Logo Section**: Branding and icon
- **Search Input**: Full-width search with icon
- **Status Indicator**: Live status with animation

### 3. Main Content
- **Topic Header**: Collapsible topic information
- **Card Container**: Single card display
- **State Management**: Loading, error, empty states
- **Navigation**: Card navigation controls

### 4. Modal System
- **Backdrop**: Blurred background
- **Modal Content**: Expanded information
- **Close Actions**: Multiple close methods
- **Responsive**: Mobile-friendly modal

### 5. Interactive Elements
- **Buttons**: Styled action buttons
- **Inputs**: Search and select elements
- **Links**: Reference links
- **Icons**: SVG icons for actions

## Accessibility Features

### 1. ARIA Labels
- **Semantic HTML**: Proper heading structure
- **ARIA Attributes**: Screen reader support
- **Focus Management**: Keyboard navigation
- **Alt Text**: Image descriptions

### 2. Keyboard Navigation
- **Tab Order**: Logical tab sequence
- **Focus States**: Visible focus indicators
- **Keyboard Shortcuts**: Arrow keys, Enter, Esc
- **Skip Links**: Navigation shortcuts

### 3. Responsive Design
- **Mobile First**: Mobile-optimized layout
- **Breakpoints**: Responsive design
- **Touch Friendly**: Touch-optimized buttons
- **Viewport**: Proper viewport configuration

## Validation Checklist
- [ ] HTML structure is semantically correct
- [ ] All interactive elements have proper IDs
- [ ] Accessibility attributes are present
- [ ] Responsive design works on mobile
- [ ] Modal system functions correctly
- [ ] Loading states are properly implemented
- [ ] Error handling is user-friendly
- [ ] Keyboard navigation works
- [ ] All elements have proper styling classes
- [ ] JavaScript integration points are ready

## Next Steps
After completing this todo, proceed to "09-frontend-js" to implement the JavaScript functionality for card rendering, navigation, and API integration.
