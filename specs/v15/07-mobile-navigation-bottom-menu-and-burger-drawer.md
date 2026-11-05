# Mobile Responsive Navigation: Bottom Menu & Burger Side Drawer

## 1. Overview
Optimized mobile and responsive navigation layout for narrow screens (`<= 760px`) across all portal layouts (Admin, Practitioner, and Client):
- **Compact Bottom Menu Bar**: Fixed at the bottom of the viewport with safe area padding, displaying exclusively the top 3 important/primary navigation menus plus a dedicated "Menu" burger trigger button.
- **Burger Side Drawer**: Accessible via the "Menu" trigger in the bottom navigation bar or swipe/tap interactions, sliding out smoothly from the left over a dimmed backdrop to reveal the complete navigation list, current user profile, search shortcuts, role switcher, and sign-out actions.
- **Responsive Workspace**: Adjusted `.portal-main` and `.detail-pane` bottom padding (`calc(4.5rem + env(safe-area-inset-bottom, 0))`) to ensure workspace content and floating controls are never obscured by the mobile navigation bar.

## 2. Important Primary Bottom Navigation
- **Portal Primary Menus**:
  - **Admin**: `Overview` (`/admin`), `Library` (`/admin/library`), `Users` (`/admin/users`) + `Menu` (Burger Drawer).
  - **Practitioner**: `Home` (`/practitioner`), `Consult` (`/practitioner/consult`), `Clients` (`/practitioner/clients`) + `Menu` (Burger Drawer).
  - **Client**: `Home` (`/client`), `Questionnaire` (`/client/questionnaire`), `Health record` (`/client/records`) + `Menu` (Burger Drawer).
- **Secondary Subpage Active Indication**:
  - When the user navigates to a secondary page not directly pinned to the bottom bar (e.g. `/admin/settings`, `/admin/audit`, `/admin/questionnaires`), the "Menu" burger button automatically displays an active highlight state (`.on`), providing intuitive location awareness.
- **Mobile Hardware Safe Insets**:
  - Bottom bar accounts for modern phone navigation gestures using `env(safe-area-inset-bottom, 0)`.

## 3. Full Menu Burger Side Drawer
- **Slide-out Sheet**:
  - Positioned fixed with smooth CSS transition (`transform: translateX(-100%)` to `translateX(0)`), width capped at `min(21rem, 84dvw)`.
- **Content Structure**:
  1. **Header**: Brand logo mark with dynamic ambient leaf accent graphics and an accessible close button (`×`).
  2. **User Profile Card**: Avatar initials, full user name, user role, and email display.
  3. **Global Search Trigger**: Quick action with search icon and keyboard shortcut badge (`⌘K`).
  4. **Full Navigation Menu**: Complete list of portal navigation routes with active indicators, icons, labels, badges, and Pro pills.
  5. **Footer Actions**: Multi-role switcher (if user has multiple assigned roles) and Sign out button.
- **Accessibility & Dismissal**:
  - Focus trapping and light-dismiss backdrop click (`rgba(0, 0, 0, 0.65)` with `backdrop-filter: blur(5px)`).
  - Keyboard `Escape` dismiss support.
  - Automatic drawer close on route navigation (`page.url.pathname` change).
  - Screen reader attributes: `aria-expanded`, `aria-controls="mobile-nav-drawer"`, `aria-label`, and `role="dialog"`.
