# Todo 10: Frontend Styling and Animations

## Objective
Create beautiful, responsive CSS styling with smooth animations, glassmorphism effects, and mobile-first design using Tailwind CSS and custom CSS.

## Files to Create

### 1. `frontend/styles.css`
Create comprehensive custom styling:

```css
/* AIFlash Custom Styles */

/* ============================================================================
   ROOT VARIABLES AND BASE STYLES
   ============================================================================ */

:root {
  --primary-purple: #8b5cf6;
  --primary-purple-dark: #7c3aed;
  --glass-bg: rgba(255, 255, 255, 0.1);
  --glass-border: rgba(255, 255, 255, 0.2);
  --text-primary: #ffffff;
  --text-secondary: rgba(255, 255, 255, 0.8);
  --text-muted: rgba(255, 255, 255, 0.6);
  --shadow-glass: 0 8px 32px rgba(0, 0, 0, 0.3);
  --shadow-card: 0 20px 40px rgba(0, 0, 0, 0.4);
}

* {
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* ============================================================================
   GLASSMORPHISM EFFECTS
   ============================================================================ */

.glass {
  background: var(--glass-bg);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid var(--glass-border);
  box-shadow: var(--shadow-glass);
}

.glass-card {
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--glass-border);
  box-shadow: var(--shadow-card);
}

.glass-header {
  background: rgba(0, 0, 0, 0.2);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--glass-border);
}

/* ============================================================================
   CARD ANIMATIONS AND TRANSITIONS
   ============================================================================ */

.card-stack {
  perspective: 1000px;
  transform-style: preserve-3d;
}

.card-enter {
  animation: cardSlideIn 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.card-exit {
  animation: cardSlideOut 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes cardSlideIn {
  0% {
    opacity: 0;
    transform: translateX(100px) rotateY(15deg);
  }
  100% {
    opacity: 1;
    transform: translateX(0) rotateY(0deg);
  }
}

@keyframes cardSlideOut {
  0% {
    opacity: 1;
    transform: translateX(0) rotateY(0deg);
  }
  100% {
    opacity: 0;
    transform: translateX(-100px) rotateY(-15deg);
  }
}

.card-hover {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.card-hover:hover {
  transform: translateY(-4px) scale(1.02);
  box-shadow: 0 25px 50px rgba(0, 0, 0, 0.5);
}

/* ============================================================================
   BUTTON STYLES AND INTERACTIONS
   ============================================================================ */

.btn-primary {
  background: linear-gradient(135deg, var(--primary-purple), var(--primary-purple-dark));
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.btn-primary::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.5s;
}

.btn-primary:hover::before {
  left: 100%;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 25px rgba(139, 92, 246, 0.4);
}

.btn-secondary {
  background: var(--glass-bg);
  border: 1px solid var(--glass-border);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.15);
  transform: translateY(-1px);
}

.btn-icon {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.btn-icon:hover {
  transform: scale(1.1);
  background: rgba(255, 255, 255, 0.1);
}

/* ============================================================================
   LOADING ANIMATIONS
   ============================================================================ */

.loading-spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.loading-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.loading-dots::after {
  content: '';
  animation: dots 1.5s infinite;
}

@keyframes dots {
  0%, 20% {
    content: '';
  }
  40% {
    content: '.';
  }
  60% {
    content: '..';
  }
  80%, 100% {
    content: '...';
  }
}

/* ============================================================================
   MODAL ANIMATIONS
   ============================================================================ */

.modal-enter {
  animation: modalFadeIn 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.modal-exit {
  animation: modalFadeOut 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes modalFadeIn {
  0% {
    opacity: 0;
    transform: scale(0.9) translateY(-20px);
  }
  100% {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

@keyframes modalFadeOut {
  0% {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
  100% {
    opacity: 0;
    transform: scale(0.9) translateY(-20px);
  }
}

.modal-backdrop {
  animation: backdropFadeIn 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes backdropFadeIn {
  0% {
    opacity: 0;
  }
  100% {
    opacity: 1;
  }
}

/* ============================================================================
   BADGE AND TAG STYLES
   ============================================================================ */

.badge {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.badge-code {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.badge-data {
  background: rgba(59, 130, 246, 0.2);
  color: #3b82f6;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.badge-repro {
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.badge-benchmark {
  background: rgba(168, 85, 247, 0.2);
  color: #a855f7;
  border: 1px solid rgba(168, 85, 247, 0.3);
}

.tag {
  display: inline-flex;
  align-items: center;
  padding: 0.375rem 0.75rem;
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.8);
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.tag:hover {
  background: rgba(255, 255, 255, 0.15);
  transform: translateY(-1px);
}

/* ============================================================================
   REFERENCE LINK STYLES
   ============================================================================ */

.reference-link {
  display: inline-flex;
  align-items: center;
  padding: 0.5rem 1rem;
  background: rgba(255, 255, 255, 0.1);
  color: white;
  text-decoration: none;
  border-radius: 0.5rem;
  border: 1px solid rgba(255, 255, 255, 0.2);
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.reference-link::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
  transition: left 0.5s;
}

.reference-link:hover::before {
  left: 100%;
}

.reference-link:hover {
  background: rgba(255, 255, 255, 0.15);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.reference-link::after {
  content: '↗';
  margin-left: 0.5rem;
  font-size: 0.75rem;
  opacity: 0.7;
}

/* ============================================================================
   SEARCH INPUT STYLES
   ============================================================================ */

.search-input {
  position: relative;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.search-input:focus-within {
  transform: scale(1.02);
}

.search-input input {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.search-input input:focus {
  box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.3);
  transform: translateY(-1px);
}

/* ============================================================================
   STATUS INDICATOR ANIMATIONS
   ============================================================================ */

.status-indicator {
  position: relative;
}

.status-indicator::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.3;
  transform: translate(-50%, -50%) scale(0);
  animation: statusPulse 2s infinite;
}

@keyframes statusPulse {
  0% {
    transform: translate(-50%, -50%) scale(0);
    opacity: 0.3;
  }
  50% {
    transform: translate(-50%, -50%) scale(1.5);
    opacity: 0.1;
  }
  100% {
    transform: translate(-50%, -50%) scale(2);
    opacity: 0;
  }
}

/* ============================================================================
   RESPONSIVE DESIGN
   ============================================================================ */

@media (max-width: 768px) {
  .card-stack {
    margin: 0 1rem;
  }
  
  .glass-card {
    padding: 1.5rem;
    min-height: 500px;
  }
  
  .btn-primary,
  .btn-secondary {
    padding: 0.75rem 1.5rem;
    font-size: 0.875rem;
  }
  
  .reference-link {
    padding: 0.375rem 0.75rem;
    font-size: 0.75rem;
  }
  
  .tag {
    padding: 0.25rem 0.5rem;
    font-size: 0.75rem;
  }
}

@media (max-width: 480px) {
  .glass-card {
    padding: 1rem;
    min-height: 400px;
  }
  
  .card-title {
    font-size: 1.25rem;
    line-height: 1.4;
  }
  
  .btn-primary,
  .btn-secondary {
    padding: 0.625rem 1.25rem;
    font-size: 0.75rem;
  }
}

/* ============================================================================
   ACCESSIBILITY ENHANCEMENTS
   ============================================================================ */

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

.focus-visible {
  outline: 2px solid var(--primary-purple);
  outline-offset: 2px;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

/* ============================================================================
   UTILITY CLASSES
   ============================================================================ */

.text-gradient {
  background: linear-gradient(135deg, var(--primary-purple), #ec4899);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.shadow-glow {
  box-shadow: 0 0 20px rgba(139, 92, 246, 0.3);
}

.border-gradient {
  border: 1px solid transparent;
  background: linear-gradient(white, white) padding-box,
              linear-gradient(135deg, var(--primary-purple), #ec4899) border-box;
}

.animate-float {
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0px);
  }
  50% {
    transform: translateY(-10px);
  }
}

.animate-glow {
  animation: glow 2s ease-in-out infinite alternate;
}

@keyframes glow {
  from {
    box-shadow: 0 0 10px rgba(139, 92, 246, 0.3);
  }
  to {
    box-shadow: 0 0 20px rgba(139, 92, 246, 0.6);
  }
}

/* ============================================================================
   DARK MODE ENHANCEMENTS
   ============================================================================ */

@media (prefers-color-scheme: dark) {
  :root {
    --glass-bg: rgba(255, 255, 255, 0.05);
    --glass-border: rgba(255, 255, 255, 0.1);
  }
}

/* ============================================================================
   PRINT STYLES
   ============================================================================ */

@media print {
  .glass,
  .glass-card,
  .glass-header {
    background: white;
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
    border: 1px solid #e5e7eb;
    box-shadow: none;
  }
  
  .btn-primary,
  .btn-secondary {
    background: #f3f4f6;
    color: #374151;
    border: 1px solid #d1d5db;
  }
  
  .reference-link {
    background: #f9fafb;
    color: #374151;
    border: 1px solid #d1d5db;
  }
}
```

## Key Features to Implement

### 1. Glassmorphism Design
- **Backdrop Blur**: Modern glass effect with blur
- **Transparency**: Semi-transparent backgrounds
- **Border Effects**: Subtle border highlights
- **Shadow Effects**: Layered shadow system

### 2. Card Animations
- **Slide Transitions**: Smooth card transitions
- **3D Effects**: Perspective and rotation
- **Hover Effects**: Interactive hover states
- **Loading States**: Animated loading indicators

### 3. Button Interactions
- **Gradient Backgrounds**: Beautiful gradient buttons
- **Hover Effects**: Transform and shadow changes
- **Shine Effects**: Animated shine on hover
- **Focus States**: Accessible focus indicators

### 4. Modal System
- **Fade Animations**: Smooth modal transitions
- **Backdrop Effects**: Blurred background
- **Scale Effects**: Modal entrance/exit animations
- **Responsive Design**: Mobile-friendly modals

### 5. Status Indicators
- **Pulse Animations**: Animated status dots
- **Color Coding**: Green/yellow/red status
- **Glow Effects**: Subtle glow animations
- **Smooth Transitions**: State change animations

### 6. Badge and Tag System
- **Color Coding**: Different colors for different types
- **Hover Effects**: Interactive hover states
- **Smooth Transitions**: Animated state changes
- **Responsive Sizing**: Mobile-optimized sizes

### 7. Reference Links
- **Hover Effects**: Transform and shadow changes
- **Shine Animations**: Animated shine effects
- **External Indicators**: Arrow icons for external links
- **Accessibility**: Proper focus states

## Animation System

### 1. Card Transitions
```css
.card-enter {
  animation: cardSlideIn 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.card-exit {
  animation: cardSlideOut 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}
```

### 2. Button Interactions
```css
.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 25px rgba(139, 92, 246, 0.4);
}
```

### 3. Loading States
```css
.loading-spinner {
  animation: spin 1s linear infinite;
}

.loading-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
```

## Responsive Design

### 1. Mobile Breakpoints
- **768px**: Tablet adjustments
- **480px**: Mobile optimizations
- **320px**: Small mobile support

### 2. Touch Optimization
- **Larger Touch Targets**: Minimum 44px touch targets
- **Swipe Gestures**: Touch-friendly interactions
- **Hover States**: Touch-appropriate hover effects

### 3. Performance
- **Reduced Motion**: Respect user preferences
- **Efficient Animations**: GPU-accelerated animations
- **Optimized Transitions**: Smooth 60fps animations

## Accessibility Features

### 1. Focus Management
- **Visible Focus**: Clear focus indicators
- **Keyboard Navigation**: Full keyboard support
- **Screen Reader**: Proper ARIA labels

### 2. Motion Preferences
- **Reduced Motion**: Respect user preferences
- **Alternative Indicators**: Non-motion alternatives
- **Accessible Colors**: High contrast support

### 3. Print Styles
- **Print Optimization**: Clean print layouts
- **Color Adjustments**: Print-friendly colors
- **Layout Preservation**: Maintain structure

## Validation Checklist
- [ ] All animations are smooth and performant
- [ ] Glassmorphism effects work across browsers
- [ ] Responsive design works on all screen sizes
- [ ] Accessibility features are properly implemented
- [ ] Print styles are clean and readable
- [ ] Hover effects are interactive and engaging
- [ ] Loading states provide good user feedback
- [ ] Color scheme is consistent and accessible
- [ ] Typography is readable and well-spaced
- [ ] All interactive elements have proper focus states

## Next Steps
After completing this todo, proceed to "11-error-handling" to implement comprehensive error handling and fallback mechanisms.
