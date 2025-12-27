# Frontend Specification: Magic SEO Plugin (Version 2.0)

This document describes the required UI/UX for the "Magic SEO" WordPress plugin.
**Target Audience**: "Claude Skills" (UI Designer / Code Generator).
**Goal**: Create a modern, React-based (or clean PHP/JS) dashboard that exposes the AI Content Engine capabilities.

---

## 1. Design Aesthetic
*   **Vibe**: "Apple meets Outdoor Vlogging". Clean, minimalist, white space, but with "magic" accents (purple/indigo gradients).
*   **Typography**: Inter or similar clean sans-serif.
*   **Components**: Cards, Toggle Switches (iOS style), Skeleton Loaders for AI states.

---

## 2. Screen: The "Command Center" (Dashboard)
The main landing page when clicking "Magic SEO" in the WP Admin sidebar.

### A. Header Area
*   **Title**: "Magic SEO Command Center"
*   **Status Indicator**:
    *   🟢 System Online (API Connected)
    *   🔴 Issues Detected (e.g., Missing API Key)

### B. "At a Glance" Cards (Row 1)
*   **Card 1: Quick Wins**
    *   **Value**: "34" (Dynamic count from GSC analysis)
    *   **Label**: "Pages ready for easy ranking gains"
    *   **Icon**: 🚀 (Rocket)
*   **Card 2: Content Health**
    *   **Value**: "Protect" / "Revive" counts.
    *   **Label**: "12 pages decaying, 5 dominating"
    *   **Icon**: 🛡️ (Shield) or 📉 (Chart)
*   **Card 3: AI Credits/Usage**
    *   **Value**: "Claude 4.5 / Imagen 4"
    *   **Label**: "Active Models"
    *   **Icon**: 🧠 (Brain)

### C. "Optimization Station" (Main Action Area)
A prominent, central input section to trigger the main workflow.
*   **Input 1: Target URL**
    *   *Placeholder*: `https://griddleking.com/my-post...`
    *   *Action*: "Fetch" button to preview current title/image.
*   **Input 2: Target Keyword**
    *   *Placeholder*: `ribeye vs rib steak`
*   **Toggle Options** (Grouped):
    *   [x] **Fix Title** (High CTR)
    *   [x] **Enhance Content** (Comparison Tables, FAQ)
    *   [x] **Generate Visuals** (Featured Image)
*   **Style Selector** (Dropdown or Segmented Control):
    *   **Option A**: "Authentic / Blogger" (Default - *Uses our new Prompt logic*)
    *   **Option B**: "Professional / Editorial"
    *   **Option C**: "Viral / Clickbait"
*   **Primary Button**:
    *   **Label**: "✨ Run Magic Optimization"
    *   **Style**: Large, Gradient Purple, Pulse effect on hover.

---

## 3. Screen: "Media Studio" (Tab)
A dedicated area for generating assets without running a full post optimization.

### A. Generator
*   **Input**: "Image Concept / Topic"
*   **Style Presets**: "Authentic Griddle", "Cinematic Macro", "Wide Landscape".
*   **Button**: "Generate Image (Imagen 4)"

### B. Asset Library
*   **Grid layout** of previously generated images.
*   **Hover Actions**: "Download", "Send to Media Library", "Delete".

---

## 4. Screen: "Settings & Connections" (Tab)
Where the user configures the "Brain".

### A. API Keys (Secure Inputs)
*   **Anthropic API Key**: `sk-ant...` (Masked input)
*   **Google Gemini API Key**: `AIza...` (Masked input)
*   **OpenAI API Key**: (Optional fallback)

### B. Vercel Connection
*   **Vercel URL**: `https://magic-seo.vercel.app`
*   **Connection Test**: "Test Ping" button.

### C. Defaults
*   **Default Image Style**: [Dropdown]
*   **Language**: [English/US]

---

## 5. Feedback & States
*   **Loading State**: When "Run Magic Optimization" is clicked:
    *   Show a progress stepper:
        1.  "Reading Content..."
        2.  "Claude is thinking (Title)..."
        3.  "Imagen is painting (Image)..."
        4.  "Finalizing..."
*   **Success State**:
    *   Confetti pop? (Optional)
    *   Show "Before vs After" comparison card.
    *   "Publish to Post" button.

---

## Technical Constraints for Designer
*   Must use standard WordPress Admin classes/structure where possible for the wrapper, OR use a React wrapper (like `@wordpress/element`).
*   The "Run Magic Optimization" button will trigger an AJAX request to our Python backend (via Vercel or local script).
