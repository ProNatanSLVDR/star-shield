# Roulette Feature Documentation

---

## Introduction & Purpose

The Roulette feature is a gamified review incentive system that allows establishments to encourage customers to leave reviews by offering them a chance to win prizes through a spinning wheel game.

### Key Design Philosophy

**IMPORTANT**: The roulette feature uses a "fake verification" system that creates the illusion that reviews are verified, when in reality they are not. This is intentional to incentivize customers to leave reviews through psychological design rather than technical verification.

---

## Feature Overview

The roulette feature presents customers with a spinning wheel game where they can win prizes after completing a simple action: leaving a review and returning to spin.

### Key Components

1. **Review Link Requirement** - Users must click a review link before spinning (fake verification mechanism)
2. **Wheel Visualization** - Canvas-based animated spinning wheel displaying prizes
3. **Prize System** - Configurable prizes with probability-based distribution
4. **Prize Codes** - Unique alphanumeric codes generated for winners
5. **Code Verification** - Public verification page for prize codes
6. **Analytics** - Tracking system for views, spins, and prize wins

---

## User Flow & Fake Verification Mechanism

### Detailed Flow

1. **Initial Page Load**
   - User sees simple instruction: **"Leave a review and come back to get your spin!"**
   - No mention of 30-second timer to users
   - Natural instruction encourages users to actually post a review
   - Creates expectation that review must be posted before returning

2. **Review Link Click**
   - User clicks the review link (opens in new tab)
   - Click timestamp is stored in `localStorage` (`roulette_review_clicked_{etablissement_id}`)
   - 30-second timer starts silently in background (NOT shown to user)

3. **Waiting Period** (User Experience)
   - User leaves to post review (natural flow)
   - No countdown timer visible to user
   - User returns after posting review (or just after delay)
   - Creates natural expectation that review was "verified"

4. **Spin Enabled**
   - After 30 seconds elapse silently, spin button becomes available
   - User returns and can spin the wheel
   - Appears as if system verified their review (but didn't)

5. **Prize Result**
   - If prize won: unique code generated and displayed
   - If "nothing" prize: thank you message

6. **Code Verification**
   - Prize codes can be verified via `/verify/<code>/` URL
   - Admin can mark codes as used

### Cooldown Mechanism

- Configurable days between spins (cookie-based)
- Separate from the 30-second fake verification timer
- Prevents abuse by limiting how often users can spin

---

## Configuration & Setup

### Admin Dashboard Settings

Establishments can configure the roulette feature through the admin dashboard at `/dashboard/etablissement/roulette/`.


#### Cooldown Period

- **Setting**: `roulette_spin_cooldown_days`
- **Default**: 14 days
- **Description**: Number of days a user must wait between spins
- **Range**: Minimum 1 day

#### Prize Configuration

- **Maximum Prizes**: 8 (including the "nothing" prize)
- **Required Fields**:
  - **Name**: Prize name (e.g., "Free Meal", "10% Discount")
  - **Icon**: FontAwesome icon class (e.g., `fa-solid fa-gift`)
  - **Probability**: Percentage chance (1-100%)
  - **Is Nothing Prize**: Checkbox to mark as "no prize" option

#### Probability Validation

- **Requirement**: Sum of all prize probabilities must equal exactly 100%
- **Validation**: Form validation ensures this constraint
- **Example**:
  - Prize 1: 10%
  - Prize 2: 20%
  - Prize 3: 30%
  - Nothing: 40%
  - **Total**: 100% ✓