# Design System

Version: 1.0.0

Status: UI/UX Specification

---

# Overview

This document defines the full UI/UX design language for AERA.

It covers:

- Pages
- Buttons
- Panels
- Cards
- Navigation
- Inputs
- Modals
- Toggles
- Status indicators
- Lists
- Tables
- Hologram interaction
- Voice interaction
- Responsive behavior
- Motion
- Accessibility
- Theme rules

The goal is to keep AERA visually clean, highly usable, and consistent across all modules.

---

# Design Philosophy

## 1. Minimal but Powerful

The interface should stay visually simple while the background system handles complexity.

---

## 2. AI First

Most intelligence should appear through behavior, not clutter.

The UI should feel smart without feeling busy.

---

## 3. Human Friendly

Use layouts, motion, and feedback that feel natural.

---

## 4. Consistent

Every page should follow the same visual logic.

---

## 5. Fast

UI should respond instantly, with lightweight transitions and clear states.

---

# Global Layout

AERA uses a modular layout structure.

```
┌─────────────────────────────────────────────────────────────────┐
│ logo       Dashboard  Macros  Apps  Gallery Phone Settings      │
├──────────────┬──────────────────────────────────────┬───────────┤
│              │                                      │ Side Panel│
│   hologram   │                                      │           │
│  system info │                                      │ Context   │
│              │             voice orb                │ Insights  │
│   workspace  │                                      │ Transcript│
│              │                                      │ Status    │
│              │             tap to speck             │ Actions   │
│              │                                      │           │
└──────────────┴──────────────────────────────────────┴───────────┘
```

---

# Layout Regions

## Header

Contains:

- Logo
- Page title
- Search
- Notifications
- AI status
- User profile
- Model status

---

## Sidebar

Contains primary navigation:

- Dashboard
- Macros
- Apps
- Gallery
- Phone
- Settings

On smaller screens, the sidebar collapses into a drawer or bottom navigation.

---

## Main Content

The primary working area for each page.

---

## Side Panel

Used for:

- Context
- Transcript
- AI details
- Memory details
- File details
- Actions

---

# Design Tokens

## Colors

Use a dark-first interface with optional light theme.

Core palette:

- Background
- Surface
- Elevated Surface
- Primary Accent
- Secondary Accent
- Success
- Warning
- Error
- Info
- Border
- Text Primary
- Text Secondary
- Text Muted

---

## Typography

Use a clear, modern sans-serif system.

Hierarchy:

- Display
- H1
- H2
- H3
- Body Large
- Body
- Caption
- Label
- Code

---

## Spacing

Standard spacing scale:

- 4
- 8
- 12
- 16
- 20
- 24
- 32
- 40
- 48

---

## Radius

Rounded corners should be used consistently.

- Small: 8px
- Medium: 12px
- Large: 16px
- Extra Large: 24px

---

## Shadows

Use soft, subtle shadows only for elevation.

Avoid heavy shadow stacking.

---

# Motion Rules

Motion should feel smooth and purposeful.

## Allowed Motion

- Fade
- Slide
- Scale
- Glow
- Pulse
- Hover lift
- Soft expand

## Avoid

- Excessive bounce
- Overly flashy animations
- Constant motion without purpose
- Distracting transitions

---

# Responsive Behavior

## Desktop

Full layout:

- Sidebar
- Main content
- Side panel

## Tablet

- Sidebar collapses
- Side panel becomes overlay or drawer

## Mobile

- Bottom navigation or drawer
- Full-screen panels
- Simple touch targets
- Voice-first interaction encouraged

---

# Core UI Components

# Buttons

Buttons are one of the most important visual elements in AERA.

## Button Types

### Primary Button

Used for the main action on a page.

Example:

- Start
- Save
- Send
- Run
- Open

Style:

- Strong accent color
- Medium to large padding
- Rounded corners
- Clear label

---

### Secondary Button

Used for supporting actions.

Example:

- Cancel
- Close
- Back
- Edit

Style:

- Neutral surface
- Soft border
- Subtle hover

---

### Tertiary Button

Used for low-priority actions.

Example:

- More
- Details
- View
- Info

Style:

- Minimal border or text button

---

### Destructive Button

Used for dangerous actions.

Example:

- Delete
- Remove
- Reset
- Disconnect

Style:

- Error color
- Confirmation before execution

---

### Icon Button

Used when space is limited.

Example:

- Search
- Mic
- Settings
- Close
- Refresh

Rules:

- Always include tooltip on desktop
- Must remain readable and tappable on mobile

---

### Floating Action Button

Used for a single dominant action in a page.

Example:

- New Workflow
- Start Conversation
- Add File

---

## Button States

- Default
- Hover
- Pressed
- Focused
- Disabled
- Loading
- Success
- Error

---

# Inputs

## Text Input

Used for:

- Search
- Commands
- Forms
- Configuration

Style:

- Clear border
- Soft background
- Visible focus ring

---

## Search Bar

Used across the app for:

- Files
- Memory
- Projects
- Apps
- Gallery
- Settings

Supports:

- Inline suggestions
- Recent searches
- Semantic search

---

## Dropdown

Used for:

- Model selection
- Theme selection
- Device selection
- Language selection

---

## Toggle Switch

Used for on/off settings.

Examples:

- Voice
- Memory
- Notifications
- Local LLM
- Auto update

---

## Slider

Used for:

- Volume
- Speed
- Pitch
- Brightness
- Animation intensity
- Size

---

## Checkbox

Used for multiple selections.

---

## Radio Group

Used for single choice settings.

---

## Text Area

Used for:

- Prompts
- Notes
- Descriptions
- Logs
- Long messages

---

# Navigation

## Sidebar Navigation

Main navigation items are always visible on desktop.

---

## Top Navigation

Used for:

- Page title
- Search
- Status
- Profile
- Quick actions

---

## Breadcrumbs

Used in deep hierarchies like:

- Workspace
- Project files
- Settings subpages
- Gallery folders

---

## Tabs

Used when a page contains sub-sections.

Examples:

- AI / Voice / System
- Short-Term / Long-Term / Memory Graph
- Local / Cloud / Custom Models

---

## Drawer

Used for:

- Mobile navigation
- Detail panels
- Hidden settings
- Action menus

---

# Page Design Rules

# Dashboard

The Dashboard is the main home screen.

It should include:

- Workspace panel
- Hologram center
- Transcript panel
- Tap to Speak
- Status bar
- Drag and drop area

Design style:

- Calm
- Focused
- Futuristic
- Clean

Important elements:

- One dominant primary action
- One center AI focus area
- One transcript area
- One workspace area

---

# Macros

Macros is the memory intelligence page.

It should include:

- Memory graph
- Memory filters
- Memory type selector
- Node details
- Search bar

Design style:

- Graph-based
- Analytical
- Transparent
- Deep focus

---

# Apps

Apps should feel like a control center.

It should include:

- App cards
- Search
- Categories
- Connect / disconnect status
- Launch actions

Design style:

- Organized
- Functional
- Modular

---

# Gallery

Gallery should focus on media browsing.

It should include:

- Grid layout
- Search
- Filters
- Preview panel
- Album management

Design style:

- Visual
- Spacious
- Image-first

---

# Phone

Phone should feel like a device hub.

It should include:

- Connected devices
- Battery status
- Notifications
- Messages
- File transfer

Design style:

- Clean
- Utility-focused
- Status-driven

---

# Settings

Settings should remain simple.

Main categories:

- AI
- Voice
- System

Advanced settings should be nested.

Design style:

- Minimal
- Organized
- Easy to scan

---

# Workspace

Workspace should feel like a project intelligence panel.

It should include:

- File tree
- Editor/preview
- AI context panel
- Search
- Project info

---

# Terminal

Terminal should feel like a modern dev console.

It should include:

- Terminal output
- Command line
- History
- Suggestions
- Tabs

---

# Memory Page

Memory pages should prioritize:

- Graph
- Search
- Filters
- Node details
- Recall history

---

# Voice Page

Voice interface should include:

- Microphone state
- Listening state
- Transcript
- Response playback
- Emotion status

---

# Hologram Page

Hologram interface should include:

- Avatar
- Emotion state
- Idle animation
- Speaking animation
- Controls

---

# Buttons by Context

## Dashboard Buttons

- Tap to Speak
- Open Workspace
- Start Memory
- Drag File Here

---

## Apps Buttons

- Launch
- Connect
- Disconnect
- Settings
- Update

---

## Gallery Buttons

- Open
- Favorite
- Share
- Download
- Analyze

---

## Phone Buttons

- Sync
- Pair Device
- Refresh
- Send File
- Clear

---

## Settings Buttons

- Save
- Reset
- Apply
- Restore Defaults

---

# Cards

Cards should be used for grouped content.

## Card Types

- App card
- Model card
- Memory card
- File card
- Device card
- Notification card
- Workflow card

## Card Structure

- Title
- Subtitle
- Status
- Action
- Metadata

---

# Tables

Tables should be used for:

- Logs
- Models
- Devices
- Performance stats
- Update history
- Security findings

Rules:

- Keep headers short
- Avoid too many columns
- Support sorting when useful

---

# Lists

Use lists for:

- Navigation
- Settings
- Agent lists
- File lists
- Memory nodes

---

# Status Indicators

Use consistent status styles.

## States

- Connected
- Disconnected
- Active
- Idle
- Running
- Paused
- Error
- Offline
- Loading
- Complete

---

# Badges

Use badges for:

- Model type
- File type
- Agent type
- Priority
- Risk level
- New
- Beta
- Local
- Cloud

---

# Modals

Use modals for:

- Confirmations
- Account actions
- Model selection
- Device pairing
- Security warnings
- Destructive actions

Rules:

- One primary action
- One cancel action
- Clear title
- Clear consequence

---

# Toasts

Use toasts for:

- Success
- Short alerts
- Background completion
- Quick notifications

---

# Panels

Panels should be used for detail-heavy side information.

Examples:

- Memory details
- Transcript details
- File metadata
- Device info
- Model info

---

# Empty States

Empty states should explain:

- What is missing
- Why it matters
- What to do next

Example:

- No project open
- No device connected
- No memory found
- No models detected

---

# Loading States

Loading should be:

- Smooth
- Short
- Informative

Use:

- Skeletons
- Spinners
- Progress bars
- Placeholder cards

---

# Error States

Errors must be:

- Clear
- Actionable
- Non-technical where possible

Must include:

- What failed
- Why it failed
- What the user can do next

---

# Accessibility

AERA UI must support:

- Keyboard navigation
- Screen readers
- High contrast mode
- Scalable text
- Visible focus states
- Sufficient color contrast
- Touch target sizing

---

# Interaction Rules

## Hover

Use subtle hover feedback.

## Click

Must feel immediate.

## Drag and Drop

Used mainly in Dashboard and Gallery.

## Long Press

Used on mobile for context menus.

## Keyboard

Everything important should be keyboard accessible.

---

# Voice UI

Voice interactions should show:

- Listening
- Processing
- Speaking
- Error
- Idle

---

# Hologram UI

The avatar should reflect:

- Emotion
- State
- Speech
- Listening
- Thinking

---

# Design Language

Visual style should feel:

- Futuristic
- Professional
- Intelligent
- Calm
- Trustworthy

Avoid visual clutter.

---

# Component Consistency

Every component should follow the same structure:

- Name
- State
- Status
- Action
- Metadata

---

# Theme Support

## Dark Theme

Default theme.

## Light Theme

Optional and fully supported.

## Accent Color

Used for:

- Buttons
- Active states
- Highlights
- Focus rings
- Primary indicators

---

# Customization

Users should be able to customize:

- Theme
- Accent color
- Font size
- Animation level
- Sidebar behavior
- Dashboard layout
- Hologram visibility

---

# Motion and Feedback

Use feedback for:

- Success
- Failure
- Processing
- Waiting
- Focus
- Alert

Feedback should be instant and subtle.

---

# Page Loading Order

Recommended order:

1. Load shell
2. Load navigation
3. Load current page
4. Load data
5. Load AI context
6. Load background updates

---

# Design Tokens Summary

- Clean surfaces
- Soft borders
- Rounded corners
- Clear hierarchy
- Gentle motion
- Strong focus states
- Minimal clutter
- AI-first behavior

---

# Future UI Features

Planned additions:

- Customizable dashboards
- Widget system
- Multi-window workspace
- Voice-first layout mode
- Hologram overlay mode
- Adaptive UI based on user habits
- Smart layout suggestions
- Plugin-based UI extensions

---

# Summary

The AERA design system is built to present complex AI capabilities in a clean, calm, and highly structured interface.

Every page, button, component, and panel follows the same visual language so the product feels consistent, intelligent, and easy to use. The UI should make powerful systems feel simple, while the background AI handles everything complicated behind the scenes.
