# Starshield Application

Starshield is a Django-based web application designed to help businesses strategically manage their online reviews, particularly on platforms like Google. It acts as a smart intermediary for customer feedback, optimizing public perception while providing valuable internal insights.

## Core Functionality

The central feature of Starshield is its conditional review redirection system:

1. **QR Code Redirection:** Businesses generate unique, customizable QR codes. When a customer scans this code (e.g., at a restaurant), they are directed to a dedicated rating page hosted within the Starshield application.

2. **Star Rating Input:** On this page, customers provide a star rating for their experience.

3. **Conditional Logic for Redirection:**
   - **Positive Feedback (Rating > Threshold):** If the customer's provided star rating exceeds a pre-defined threshold set by the business, the customer is automatically redirected to the business's official Google review page. This strategically funnels positive reviews to public platforms, enhancing the business's online reputation.
   - **Negative Feedback (Rating <= Threshold):** If the star rating is at or below the threshold, the feedback is captured privately within the Starshield system. This allows businesses to gather constructive criticism and address issues internally without immediately impacting their public online ratings.

4. **Roulette Wheel Gamification:** An optional feature that rewards customers after leaving reviews. Customers can spin a roulette wheel to win prizes, encouraging engagement and repeat visits.

## Key Features

### Review Management
- **Conditional Review Filtering:** Automatically redirects positive reviews to Google while capturing negative feedback internally
- **Review Analytics:** Track feedback views, internal/external submissions, and customer engagement metrics
- **Rating History:** Historical tracking of Google ratings over time
- **Review Import:** Automatic synchronization of reviews from Google My Business API

### QR Code Generation
- **Customizable Styling:** Multiple style options (square, rounded, circle, spaced)
- **Color Customization:** Custom fill colors, background colors, and gradient masks
- **Logo Integration:** Add custom logos to QR codes
- **Multiple Color Masks:** Solid, radial gradients, square gradients, horizontal/vertical gradients

### Roulette Wheel
- **Prize Management:** Configure prizes with custom names, icons, and probability percentages
- **Cooldown System:** Configurable cooldown periods between spins (1-180 days)
- **Prize Codes:** Unique codes generated for each prize win
- **Analytics Tracking:** Track roulette views, spins, wins, and engagement

### Google My Business Integration
- **OAuth Authentication:** Secure Google OAuth integration with encrypted credential storage
- **Automatic Establishment Import:** Import business locations directly from Google My Business
- **Review Synchronization:** Background tasks to fetch and sync reviews from Google
- **Rating Statistics:** Track average ratings and total review counts

### Subscription Management
- **Per-Establishment Billing:** Stripe-based subscriptions managed per establishment
- **Multiple Billing Cycles:** Support for monthly, quarterly, and yearly subscriptions
- **Subscription Status:** Automatic activation/deactivation based on subscription status
- **Webhook Integration:** Real-time subscription updates via Stripe webhooks

### Dashboard Features
- **Multi-Establishment Management:** Manage multiple business locations from a single dashboard
- **Onboarding Flow:** Guided multi-step setup process for new users
- **Analytics Overview:** View statistics across all establishments
- **Settings Management:** Configure thresholds, QR codes, roulette, and establishment settings

## Technical Stack

### Backend
- **Framework:** Django 5.2.6
- **Configuration:** django-configurations for environment-specific settings
- **API Framework:** django-ninja for REST API endpoints
- **Task Queue:** Google Cloud Tasks for background job processing
- **Authentication:** django-allauth with Google Social Authentication
- **Custom User Model:** Email-based authentication with mandatory email verification

### Frontend
- **HTMX Integration:** django-htmx for dynamic, interactive user interfaces with partial page updates
- **CSS Framework:** Bootstrap for responsive, mobile-first design
- **Component System:** django-components for reusable UI components
- **Template Engine:** Django templates with component-based architecture

### Database
- **Development:** SQLite
- **Production:** PostgreSQL (Cloud SQL)
- **Connection Pooling:** Configured for production with connection management

### Cloud Services
- **Hosting:** Google Cloud Run (containerized deployment)
- **Database:** Google Cloud SQL (PostgreSQL)
- **Storage:** Google Cloud Storage (static files and media)
- **Task Processing:** Google Cloud Tasks (background jobs)
- **Encryption:** Google Cloud KMS (symmetric encryption for OAuth tokens)
- **CI/CD:** Google Cloud Build

### Third-Party Integrations
- **Payments:** Stripe for subscription management
- **Email:** Brevo (formerly Sendinblue) for transactional emails
- **Google APIs:** Google My Business API v4 for business management

### Security
- **Token Encryption:** OAuth tokens encrypted using Google Cloud KMS
- **CSRF Protection:** Django CSRF middleware
- **Email Verification:** Mandatory email verification for all accounts
- **Secure Headers:** HTTPS enforcement in production

### Internationalization
- **Language:** French (fr-fr)
- **Timezone:** Europe/Paris

## Project Structure

```
/app
├── starshield/              # Main Django project configuration
│   ├── settings.py         # Environment-specific settings (Dev/Prod)
│   ├── urls.py             # Root URL configuration
│   ├── wsgi.py             # WSGI application entry point
│   ├── middleware.py       # Custom middleware (messages, etablissement selection)
│   ├── decorators.py       # Custom decorators (login_not_required, etc.)
│   ├── kms.py              # Google Cloud KMS encryption utilities
│   ├── qrcodes.py          # QR code generation utilities
│   ├── email_backends.py   # Brevo email backend
│   └── email_service.py    # Email service wrapper
│
├── apps/
│   ├── private/            # Private apps (require authentication)
│   │   ├── auths/         # Authentication and core models
│   │   │   ├── models.py           # User, GoogleCredentials, Etablissement, RatingHistory
│   │   │   ├── views.py            # Authentication views
│   │   │   └── urls.py             # Authentication URL routes
│   │   │
│   │   ├── dashboard/     # Main dashboard application
│   │   │   ├── views/              # View modules
│   │   │   │   ├── accueil.py              # Home dashboard
│   │   │   │   ├── onboarding/             # Onboarding flow
│   │   │   │   ├── etablissements/         # Establishment management
│   │   │   │   ├── etablissement/          # Single establishment views
│   │   │   │   │   ├── views.py            # Overview, settings
│   │   │   │   │   ├── filtre/             # Review filtering (threshold, QR, personalization)
│   │   │   │   │   └── roulette/           # Roulette configuration
│   │   │   │   ├── facturation/            # Billing/subscription management
│   │   │   │   └── profile/                # User profile management
│   │   │   └── templates/          # Dashboard templates
│   │   │
│   │   ├── payments/      # Stripe subscription management
│   │   │   ├── models.py           # StripeSubscription model
│   │   │   ├── services.py         # Stripe API integration
│   │   │   ├── views.py            # Subscription views
│   │   │   └── webhooks.py         # Stripe webhook handlers
│   │   │
│   │   └── tasks_api/     # Background task processing API
│   │       ├── api/
│   │       │   ├── router_v1.py    # Django Ninja API routes
│   │       │   ├── schemas.py      # API request/response schemas
│   │       │   └── task_tracking.py # Task execution tracking
│   │       ├── services/
│   │       │   ├── queue_service.py    # Cloud Tasks queue management
│   │       │   └── review_service.py   # Review fetching logic
│   │       ├── models.py           # TaskExecution model
│   │       └── urls.py             # API URL configuration
│   │
│   └── public/            # Public apps (no authentication required)
│       ├── reviews/       # Review collection application
│       │   ├── models.py       # Review, ReviewAnalytics models
│       │   ├── views.py        # Public feedback pages
│       │   ├── forms.py        # Review forms
│       │   └── templates/      # Feedback page templates
│       │
│       ├── roulette/      # Roulette wheel application
│       │   ├── models.py       # RoulettePrize, RouletteSpin, RouletteAnalytics
│       │   ├── views.py        # Public roulette wheel pages
│       │   └── templates/      # Roulette templates
│       │
│       └── routing/       # Public routing/redirects
│           ├── views.py        # QR code redirect views
│           └── urls.py         # Routing URL configuration
│
├── components/             # Reusable UI components
│   ├── button/             # Button component
│   ├── table/              # Table component
│   ├── review/             # Review component
│   └── ...                 # Other components
│
├── templates/              # Base templates
│   ├── dashboard_base.html
│   ├── 404.html
│   └── 500.html
│
├── static/                 # Static files (JS, CSS)
├── manage.py               # Django management script
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker container definition
├── cloudbuild.yaml         # Google Cloud Build configuration
└── pyproject.toml          # Python project configuration (ruff, djlint)
```