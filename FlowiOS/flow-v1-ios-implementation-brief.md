# FLOW V1 - IMPLEMENTATION BRIEF (FINAL)

## Target
`flow/static/index.html`

## Scope
UI/CSS updates + Localization logic only. Preserve all WebSocket/Python backend logic.

## Goal
Apply Flow v1 Virgil design system with source language-driven UI localization to existing working application.

---

## A. HTML STRUCTURE CHANGES

### Current Structure (Assumed):
```html
<body>
  <div class="container">
    <div class="language-selector">...</div>
    <div class="orb">...</div>
    <div class="status">...</div>
    <div class="transcript">...</div>
  </div>
</body>
```

### New Structure (Required):
```html
<body>
  <!-- Trust Bar -->
  <div class="trust-bar">
    <div class="status-dot"></div>
    <span class="status-text" id="trust-bar-text">Live · English ↔ Português (Brasil)</span>
  </div>

  <!-- Main Container -->
  <div class="container">
    <!-- Header -->
    <header class="header">
      <h1 class="wordmark">F L O W</h1>
      <p class="subtitle" id="subtitle">"DIASPORA INTERPRETER"</p>
      <div class="language-status">
        <span class="lang-active" id="lang-source">ENGLISH</span>
        <span class="lang-arrow">↔</span>
        <span class="lang-inactive" id="lang-target">PORTUGUÊS (BRASIL)</span>
      </div>
    </header>

    <!-- Content Grid -->
    <div class="content-grid">
      <!-- Gold Spine -->
      <div class="gold-spine">
        <span class="spine-label" id="spine-label">FLOW SYSTEM</span>
      </div>

      <!-- Content Column -->
      <div class="content-column">
        <!-- Translation Panel -->
        <div class="translation-panel">
          <span class="panel-label" id="panel-label">"TRANSLATION"</span>
          <div id="translation-turns">
            <!-- Turns inserted here dynamically -->
          </div>
        </div>

        <!-- Orb Section -->
        <div class="orb-section">
          <div class="orb-container">
            <!-- Adinkra SVG layer -->
            <svg class="adinkra-layer" viewBox="0 0 160 160">
              <!-- Dwennimmen paths -->
              <path d="M 50 80 Q 50 60, 55 50 Q 60 40, 70 45 Q 75 50, 72 60 Q 68 70, 60 72 Q 52 74, 50 68" 
                    fill="none" stroke="#D4AF37" stroke-width="3" stroke-linecap="round"/>
              <path d="M 50 68 Q 48 75, 52 82" 
                    fill="none" stroke="#D4AF37" stroke-width="3" stroke-linecap="round"/>
              <path d="M 110 80 Q 110 60, 105 50 Q 100 40, 90 45 Q 85 50, 88 60 Q 92 70, 100 72 Q 108 74, 110 68" 
                    fill="none" stroke="#D4AF37" stroke-width="3" stroke-linecap="round"/>
              <path d="M 110 68 Q 112 75, 108 82" 
                    fill="none" stroke="#D4AF37" stroke-width="3" stroke-linecap="round"/>
              <path d="M 55 90 L 60 95 L 100 95 L 105 90" 
                    fill="none" stroke="#D4AF37" stroke-width="2.5" stroke-linecap="round"/>
            </svg>
            
            <div class="orb-base"></div>
            <div class="orb-ring"></div>
            <div class="orb-icon">
              <svg viewBox="0 0 24 24" fill="none">
                <path d="M12 15C13.6569 15 15 13.6569 15 12V6C15 4.34315 13.6569 3 12 3C10.3431 3 9 4.34315 9 6V12C9 13.6569 10.3431 15 12 15Z" 
                      stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M19 12C19 15.866 15.866 19 12 19M12 19C8.13401 19 5 15.866 5 12M12 19V22M12 22H15M12 22H9" 
                      stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
          </div>

          <!-- Instructions -->
          <div class="orb-instructions">
            <p class="instruction-label" id="instruction-label">"INSTRUCTION"</p>
            <p class="instruction-primary" id="orb-state">HOLD TO SPEAK</p>
            <p class="instruction-text" id="instruction-detail">
              Press and hold the orb to activate live translation. 
              Speak naturally. Flow adapts to your voice.
            </p>
            
            <div class="microcopy-block">
              <p class="microcopy" id="microcopy">
                YOUR ACCENT BELONGS HERE.<br>
                SPEAK AS YOU ARE. FLOW ADAPTS.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</body>
```

### Key Structure Changes:
1. Add `<div class="trust-bar">` at top of `<body>`
2. Add `<header class="header">` with wordmark + subtitle + language status
3. Wrap main content in `<div class="content-grid">` (two columns: spine + content)
4. Replace `.transcript` div with `.translation-panel` using turn-based structure
5. Add `.orb-section` container holding orb + instructions
6. Add Adinkra SVG layer inside `.orb-container`
7. Add `id` attributes to all text elements that change based on language

---

## B. CSS MAPPING

### 1. Color Palette
```css
:root {
  /* Base */
  --bg-primary: #FFFEF9;      /* Warm paper */
  --surface: #FFFFFF;          /* Panels */
  --text-primary: #000000;     /* Main text */
  --text-secondary: #666666;   /* Labels */
  --text-tertiary: #999999;    /* Muted */
  
  /* Accent */
  --gold: #D4AF37;             /* Structural gold */
  
  /* Trust/Status */
  --trust-bg: #000000;
  --status-live: #10B981;      /* Green pulse */
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: var(--bg-primary);
  margin: 0;
  padding: 0;
}
```

### 2. Typography Scale
```css
/* Wordmark */
.wordmark {
  font-size: 72px;
  font-weight: 900;
  letter-spacing: 0.4em;
  color: var(--text-primary);
  line-height: 0.9;
  margin-bottom: 12px;
}

/* Subtitle */
.subtitle {
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--text-secondary);
}

.subtitle::before,
.subtitle::after {
  content: '"';
  color: var(--gold);
}

/* Language Status */
.language-status {
  margin-top: 24px;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.lang-active {
  color: var(--text-primary);
}

.lang-arrow {
  color: var(--gold);
  font-size: 16px;
}

.lang-inactive {
  color: var(--text-tertiary);
}

/* Source text (dominant) */
.turn-text.source {
  font-size: 22px;
  font-weight: 600;
  line-height: 1.6;
  color: var(--text-primary);
}

/* Translation text (secondary) */
.turn-text.translation {
  font-size: 18px;
  font-weight: 400;
  line-height: 1.6;
  color: var(--text-primary);
  opacity: 0.75;
}

/* Labels (quotation marks) */
.turn-label::before,
.turn-label::after,
.panel-label::before,
.panel-label::after,
.instruction-label::before,
.instruction-label::after {
  content: '"';
  color: var(--gold);
}

/* Instruction */
.instruction-primary {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-primary);
  margin-bottom: 20px;
  line-height: 1.2;
}

.instruction-text {
  font-size: 13px;
  font-weight: 500;
  line-height: 1.8;
  color: var(--text-secondary);
  letter-spacing: 0.03em;
  max-width: 400px;
}

/* Microcopy */
.microcopy {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-primary);
  line-height: 1.8;
}
```

### 3. Layout Grid
```css
.content-grid {
  display: grid;
  grid-template-columns: 5px 1fr;
  gap: 32px;
  flex: 1;
}

.gold-spine {
  background: var(--gold);
  width: 5px;
  position: relative;
}

.spine-label {
  position: absolute;
  top: 0;
  left: 12px;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: var(--gold);
  text-transform: uppercase;
  writing-mode: vertical-lr;
  transform: rotate(180deg);
}

.content-column {
  display: flex;
  flex-direction: column;
  gap: 48px;
}
```

### 4. Translation Panel
```css
.translation-panel {
  background: var(--surface);
  border: 2px solid var(--text-primary);
  padding: 32px;
  position: relative;
}

.panel-label {
  position: absolute;
  top: -12px;
  left: 24px;
  background: var(--bg-primary);
  padding: 0 8px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--text-primary);
}

.translation-turn {
  margin-bottom: 40px;
}

.translation-turn:last-child {
  margin-bottom: 0;
}

.turn-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 16px;
}

.turn-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-primary);
}

.turn-lang {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.1em;
  color: var(--text-tertiary);
}

.turn-divider {
  height: 2px;
  background: var(--gold);
  width: 80px;
  margin: 24px 0;
}
```

### 5. Orb States
```css
.orb-container {
  position: relative;
  width: 160px;
  height: 160px;
  flex-shrink: 0;
}

.adinkra-layer {
  position: absolute;
  width: 100%;
  height: 100%;
  opacity: 0.75;
  pointer-events: none;
  z-index: 1;
}

.orb-base {
  position: absolute;
  width: 100%;
  height: 100%;
  background: #000000;
  border-radius: 50%;
  z-index: 2;
}

.orb-ring {
  position: absolute;
  width: 100%;
  height: 100%;
  border: 5px solid var(--gold);
  border-radius: 50%;
  box-sizing: border-box;
  z-index: 3;
  transition: border-width 0.3s ease;
}

.orb-icon {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 4;
}

.orb-icon svg {
  width: 48px;
  height: 48px;
  color: #FFFFFF;
}

/* State: Listening */
.orb-container.listening .orb-ring {
  border-width: 7px;
}

/* State: Translating */
.orb-container.translating .orb-ring {
  border-style: dashed;
  animation: rotate 3s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* State: Speaking */
.orb-container.speaking .orb-ring {
  animation: pulse-ring 1.5s ease-in-out infinite;
}

@keyframes pulse-ring {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

/* State: Error */
.orb-container.error .orb-ring {
  border-color: #DC2626;
  animation: flash 0.5s ease-out;
}

@keyframes flash {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
```

### 6. Trust Bar
```css
.trust-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  background: var(--trust-bg);
  padding: 10px 32px;
  display: flex;
  align-items: center;
  gap: 10px;
  border-bottom: 3px solid var(--gold);
  z-index: 100;
}

.status-dot {
  width: 8px;
  height: 8px;
  background: var(--status-live);
  border-radius: 50%;
  animation: pulse-dot 2s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(1.1); }
}

.status-text {
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.1em;
  color: #FFFFFF;
  text-transform: uppercase;
}
```

### 7. Orb Section
```css
.orb-section {
  display: flex;
  align-items: flex-start;
  gap: 40px;
  margin-top: auto;
  padding-top: 60px;
}

.orb-instructions {
  flex: 1;
  padding-top: 20px;
}

.instruction-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--gold);
  margin-bottom: 12px;
}

.microcopy-block {
  margin-top: 24px;
  padding: 16px;
  border-left: 3px solid var(--gold);
  background: rgba(212, 175, 55, 0.05);
}
```

### 8. Responsive Breakpoints
```css
@media (max-width: 768px) {
  .wordmark {
    font-size: 48px;
    letter-spacing: 0.3em;
  }
  
  .content-grid {
    grid-template-columns: 3px 1fr;
    gap: 20px;
  }
  
  .orb-section {
    flex-direction: column;
    gap: 32px;
  }
  
  .orb-container {
    width: 140px;
    height: 140px;
  }
  
  .instruction-primary {
    font-size: 22px;
  }
}
```

---

## C. LOCALIZATION SYSTEM

### 1. UI Language Logic

```javascript
// UI language always matches source language
let sourceLang = 'en'; // or 'pt'
let targetLang = 'pt'; // or 'en'
let uiLang = sourceLang; // Always synced

// Language names for display
const LANGUAGE_NAMES = {
  en: { en: 'ENGLISH', pt: 'PORTUGUÊS (BRASIL)' },
  pt: { en: 'ENGLISH', pt: 'PORTUGUÊS (BRASIL)' }
};

// When user changes language pair
function setLanguagePair(newSource, newTarget) {
  sourceLang = newSource;
  targetLang = newTarget;
  uiLang = sourceLang; // UI follows source
  
  updateUI(); // Refresh all text
  localStorage.setItem('flow_source_lang', sourceLang);
  localStorage.setItem('flow_target_lang', targetLang);
}

// On first load (browser language detection + localStorage)
window.addEventListener('DOMContentLoaded', () => {
  const savedSource = localStorage.getItem('flow_source_lang');
  const savedTarget = localStorage.getItem('flow_target_lang');
  const browserLang = navigator.language.split('-')[0]; // 'pt', 'en', etc.
  
  if (savedSource && ['en', 'pt'].includes(savedSource)) {
    sourceLang = savedSource;
    targetLang = savedTarget || (savedSource === 'en' ? 'pt' : 'en');
  } else if (['en', 'pt'].includes(browserLang)) {
    sourceLang = browserLang;
    targetLang = browserLang === 'en' ? 'pt' : 'en';
  }
  
  uiLang = sourceLang;
  updateUI();
});
```

### 2. UI Strings Dictionary

```javascript
const UI_STRINGS = {
  en: {
    // Subtitle
    subtitle: 'DIASPORA INTERPRETER',
    
    // Trust bar
    trustBar: (src, tgt) => `Live · ${LANGUAGE_NAMES.en[src]} ↔ ${LANGUAGE_NAMES.en[tgt]}`,
    
    // Spine label
    spineLabel: 'FLOW SYSTEM',
    
    // Panel label
    panelLabel: 'TRANSLATION',
    
    // Turn labels
    youSaid: 'YOU SAID',
    theyHeard: 'THEY HEARD',
    
    // Instruction labels
    instructionLabel: 'INSTRUCTION',
    
    // State labels
    states: {
      idle: 'HOLD TO SPEAK',
      listening: 'LISTENING...',
      translating: 'TRANSLATING...',
      speaking: 'SPEAKING...',
      error: "COULDN'T HEAR CLEARLY. TRY AGAIN."
    },
    
    // Instructions
    instructionDetail: 'Press and hold the orb to activate live translation. Speak naturally. Flow adapts to your voice.',
    
    // Microcopy
    microcopy: 'YOUR ACCENT BELONGS HERE.<br>SPEAK AS YOU ARE. FLOW ADAPTS.'
  },
  
  pt: {
    // Subtitle
    subtitle: 'INTÉRPRETE DA DIÁSPORA',
    
    // Trust bar
    trustBar: (src, tgt) => `Ao vivo · ${LANGUAGE_NAMES.pt[src]} ↔ ${LANGUAGE_NAMES.pt[tgt]}`,
    
    // Spine label
    spineLabel: 'SISTEMA FLOW',
    
    // Panel label
    panelLabel: 'TRADUÇÃO',
    
    // Turn labels
    youSaid: 'VOCÊ DISSE',
    theyHeard: 'ELES OUVIRAM',
    
    // Instruction labels
    instructionLabel: 'INSTRUÇÃO',
    
    // State labels
    states: {
      idle: 'SEGURE PARA FALAR',
      listening: 'OUVINDO...',
      translating: 'TRADUZINDO...',
      speaking: 'FALANDO...',
      error: 'NÃO DEU PARA OUVIR DIREITO. TENTA DE NOVO.'
    },
    
    // Instructions
    instructionDetail: 'Segure o orbe para ativar a tradução ao vivo. Fale do seu jeito. O Flow se adapta à sua voz.',
    
    // Microcopy
    microcopy: 'SEU SOTAQUE PERTENCE AQUI.<br>FALE COMO VOCÊ É. O FLOW SE ADAPTA.'
  }
};
```

### 3. UI Update Function

```javascript
function updateUI() {
  const strings = UI_STRINGS[uiLang];
  
  // Update subtitle
  document.getElementById('subtitle').textContent = strings.subtitle;
  
  // Update trust bar
  document.getElementById('trust-bar-text').textContent = strings.trustBar(sourceLang, targetLang);
  
  // Update language status
  document.getElementById('lang-source').textContent = LANGUAGE_NAMES[uiLang][sourceLang];
  document.getElementById('lang-target').textContent = LANGUAGE_NAMES[uiLang][targetLang];
  
  // Update spine label
  document.getElementById('spine-label').textContent = strings.spineLabel;
  
  // Update panel label
  document.getElementById('panel-label').textContent = strings.panelLabel;
  
  // Update instruction labels
  document.getElementById('instruction-label').textContent = strings.instructionLabel;
  document.getElementById('instruction-detail').textContent = strings.instructionDetail;
  
  // Update microcopy
  document.getElementById('microcopy').innerHTML = strings.microcopy;
  
  // Update current state label
  updateOrbState(currentState); // Re-apply current state with new language
}
```

### 4. State Update Function (Modified)

```javascript
let currentState = 'idle';

function updateOrbState(state) {
  currentState = state;
  const strings = UI_STRINGS[uiLang];
  const orbContainer = document.querySelector('.orb-container');
  const stateLabel = document.getElementById('orb-state');
  
  // Remove all state classes
  orbContainer.className = 'orb-container';
  
  // Add current state class
  orbContainer.classList.add(state);
  
  // Update label text (localized)
  stateLabel.textContent = strings.states[state] || strings.states.idle;
}

// Example WebSocket handler (existing code):
socket.on('state_change', function(data) {
  updateOrbState(data.state); // idle, listening, translating, speaking, error
});
```

### 5. Translation Display (Modified)

```javascript
function addTranslation(sourceText, sourceLangCode, translationText, targetLangCode) {
  const strings = UI_STRINGS[uiLang];
  const panel = document.getElementById('translation-turns');
  
  const turn = document.createElement('div');
  turn.className = 'translation-turn';
  turn.innerHTML = `
    <div class="turn-header">
      <span class="turn-label">${strings.youSaid}</span>
      <span class="turn-lang">— ${sourceLangCode.toUpperCase()}</span>
    </div>
    <p class="turn-text source">${escapeHtml(sourceText)}</p>
    <div class="turn-divider"></div>
    <div class="turn-header">
      <span class="turn-label">${strings.theyHeard}</span>
      <span class="turn-lang">— ${targetLangCode.toUpperCase()}</span>
    </div>
    <p class="turn-text translation">${escapeHtml(translationText)}</p>
  `;
  
  // Insert at top (most recent first)
  panel.insertBefore(turn, panel.firstChild);
}

// Helper function
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Example WebSocket handler (existing code):
socket.on('translation_complete', function(data) {
  addTranslation(
    data.source_text,
    sourceLang, // Use current source language
    data.translation_text,
    targetLang // Use current target language
  );
  updateOrbState('speaking');
});
```

---

## D. STATE MAPPING

### Backend States → UI States

| Backend State | UI State Class | Label (EN) | Label (PT) | Orb Visual |
|---|---|---|---|---|
| `idle` / `ready` | `.idle` | "HOLD TO SPEAK" | "SEGURE PARA FALAR" | 5px ring |
| `recording` / `listening` | `.listening` | "LISTENING..." | "OUVINDO..." | 7px ring |
| `processing` / `translating` | `.translating` | "TRANSLATING..." | "TRADUZINDO..." | Dashed, rotating |
| `playing` / `speaking` | `.speaking` | "SPEAKING..." | "FALANDO..." | Pulsing ring |
| `error` | `.error` | "COULDN'T HEAR CLEARLY..." | "NÃO DEU PARA OUVIR..." | Red flash |

### State Transition Flow

```
IDLE (user sees orb, instruction)
  ↓ [User presses orb]
LISTENING (ring thickens, "LISTENING...")
  ↓ [User releases orb]
TRANSLATING (dashed ring rotates, "TRANSLATING...")
  ↓ [Backend completes]
SPEAKING (ring pulses, "SPEAKING...", audio plays)
  ↓ [Audio finishes]
IDLE (returns to "HOLD TO SPEAK")

ERROR (if any step fails)
  ↓ [Brief flash]
IDLE (returns to ready state)
```

---

## E. IMPLEMENTATION CHECKLIST

### Phase 1: HTML Structure
- [ ] Add `.trust-bar` div at top of body
- [ ] Add `.header` with wordmark, subtitle, language status
- [ ] Create `.content-grid` with `.gold-spine` and `.content-column`
- [ ] Replace `.transcript` with `.translation-panel`
- [ ] Restructure orb into `.orb-section` with container + instructions
- [ ] Add Adinkra SVG layer to `.orb-container`
- [ ] Add `id` attributes to all dynamic text elements

### Phase 2: CSS Application
- [ ] Define CSS custom properties (color palette)
- [ ] Apply typography scale (72px wordmark, 22px source, 18px translation)
- [ ] Implement grid layout (5px spine + content column)
- [ ] Style translation panel (2px black border, quotation labels, gold dividers)
- [ ] Style orb states (idle, listening, translating, speaking, error)
- [ ] Add trust bar styles (black bg, gold bottom rule, pulse animation)
- [ ] Add responsive breakpoints (mobile, tablet)

### Phase 3: Localization
- [ ] Create `UI_STRINGS` dictionary (en + pt)
- [ ] Implement `setLanguagePair()` function
- [ ] Implement `updateUI()` function
- [ ] Add browser language detection on first load
- [ ] Add localStorage persistence
- [ ] Update `updateOrbState()` to use localized strings
- [ ] Update `addTranslation()` to use localized labels

### Phase 4: State Integration
- [ ] Map backend states to UI state classes
- [ ] Update orb class changes (`.idle`, `.listening`, `.translating`, etc.)
- [ ] Test state transitions (idle → listening → translating → speaking → idle)
- [ ] Verify state labels update correctly in both languages
- [ ] Test error state (label, recovery)

### Phase 5: Testing
- [ ] Test HOLD interaction (press → listening, release → translating)
- [ ] Verify language switching updates all UI text
- [ ] Check browser language detection (pt-BR → Portuguese UI, en-US → English UI)
- [ ] Confirm localStorage persistence (reload preserves language choice)
- [ ] Test translation panel displays correctly in both languages
- [ ] Test trust bar status updates
- [ ] Test responsive layout (mobile, tablet, desktop)
- [ ] Verify quotation marks display correctly
- [ ] Check Adinkra visibility (75% opacity)

---

## F. CONSTRAINTS & ASSUMPTIONS

### DO NOT MODIFY:
- WebSocket connection logic
- Audio capture/playback
- Backend API calls
- Python server code
- Existing state machine logic
- Translation pipeline (Whisper + Claude + TTS)

### PRESERVE:
- HOLD-only interaction (no auto-detect changes)
- Language pair configuration system
- Error handling logic
- Audio streaming implementation

### ASSUME:
- Existing code has state management (`idle`, `listening`, `translating`, etc.)
- WebSocket events fire on state changes
- Translation data structure includes: `source_text`, `translation_text`
- Orb element exists and has event listeners attached
- Language pair selector already exists in current code

---

## G. SUCCESS CRITERIA

Implementation is complete when:

1. ✅ Wordmark displays at 72pt with proper tracking
2. ✅ Gold spine anchors layout (5px, visible, structural)
3. ✅ Translation panel uses quotation labels and hierarchy
4. ✅ Source text displays larger (22pt) than translation (18pt)
5. ✅ Orb states change visually (ring thickness, rotation, dashes)
6. ✅ State labels update in correct language ("HOLD TO SPEAK" / "SEGURE PARA FALAR")
7. ✅ Trust bar shows connection status with pulse animation
8. ✅ Adinkra symbol visible at 75% opacity in orb
9. ✅ Layout works on mobile (responsive breakpoints active)
10. ✅ Existing HOLD functionality preserved (no regressions)
11. ✅ **UI language matches source language (uiLang = sourceLang)**
12. ✅ **Browser language detection works on first load**
13. ✅ **Language preference persists via localStorage**
14. ✅ **All text elements update when language changes**
15. ✅ **Portuguese interface works identically to English**

---

## H. VISUAL EXAMPLES

### English Interface (sourceLang = 'en')
- Trust Bar: "Live · English ↔ Português (Brasil)"
- Subtitle: "DIASPORA INTERPRETER"
- Language Status: "ENGLISH ↔ PORTUGUÊS (BRASIL)"
- Orb State: "HOLD TO SPEAK"
- Panel Label: "TRANSLATION"
- Turn Labels: "YOU SAID" — EN / "THEY HEARD" — PT
- Instruction: "Press and hold the orb..."
- Microcopy: "YOUR ACCENT BELONGS HERE..."

### Portuguese Interface (sourceLang = 'pt')
- Trust Bar: "Ao vivo · Português (Brasil) ↔ English"
- Subtitle: "INTÉRPRETE DA DIÁSPORA"
- Language Status: "PORTUGUÊS (BRASIL) ↔ ENGLISH"
- Orb State: "SEGURE PARA FALAR"
- Panel Label: "TRADUÇÃO"
- Turn Labels: "VOCÊ DISSE" — PT / "ELES OUVIRAM" — EN
- Instruction: "Segure o orbe para ativar..."
- Microcopy: "SEU SOTAQUE PERTENCE AQUI..."

---

## I. NEXT STEPS AFTER IMPLEMENTATION

1. Test with real users (both EN and PT speakers)
2. Add more language pairs (maintain same uiLang = sourceLang pattern)
3. Consider adding language swap button (quick toggle source/target)
4. Monitor localStorage for analytics (which languages most used)
5. Potential future: Add ES (Spanish), FR (French), YO (Yoruba), etc.

---

**END OF IMPLEMENTATION BRIEF**

This document provides everything needed to implement Flow v1 Virgil design with source-driven UI localization without further back-and-forth.
