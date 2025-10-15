# Starshield Application

Starshield is a Django-based web application designed to help businesses strategically manage their online reviews, particularly on platforms like Google. It acts as a smart intermediary for customer feedback, optimizing public perception while providing valuable internal insights.

## Core Functionality

The central feature of Starshield is its conditional review redirection system:

1.  **QR Code Redirection:** Businesses generate unique QR codes. When a customer scans this code (e.g., at a restaurant), they are directed to a dedicated rating page hosted within the Starshield application.

2.  **Star Rating Input:** On this page, customers provide a star rating for their experience.

3.  **Conditional Logic for Redirection:**
    *   **Positive Feedback (Rating > Threshold):** If the customer's provided star rating exceeds a pre-defined threshold set by the business, the customer is automatically redirected to the business's official Google review page. This strategically funnels positive reviews to public platforms, enhancing the business's online reputation.
    *   **Negative Feedback (Rating <= Threshold):** If the star rating is at or below the threshold, the feedback is captured privately within the Starshield system. This allows businesses to gather constructive criticism and address issues internally without immediately impacting their public online ratings.

## Benefits for Businesses

*   **Optimized Public Ratings:** By filtering and directing only highly positive experiences to public review platforms, businesses can significantly improve their average star ratings.
*   **Enhanced Internal Improvement:** Private collection of lower-rated feedback provides actionable insights, enabling businesses to identify and rectify pain points proactively.
*   **Streamlined Feedback Collection:** Offers a simple and accessible method for customers to share their experiences.

## Technical Stack

*   **Framework:** Django (Python)
*   **Authentication:** `django-allauth` with support for Google Social Authentication, utilizing a custom User model (`auths.User`) with email as the primary identifier. Mandatory email verification is implemented.
*   **Frontend:**
    *   `django-htmx`: For dynamic, interactive user interfaces with a focus on partial page updates.
    *   `bootstrap`: A comprehensive front-end framework for developing responsive, mobile-first projects.
    *   `django_components`: Enables a component-based approach for UI development.
*   **Database:**
    *   SQLite (for development environments)
    *   PostgreSQL (for production environments)
*   **Integration:** Google My Business (GMB) API for managing business listings and facilitating redirection to accurate Google review pages.
*   **Internationalization:** Configured for French (`fr-fr`) language and `Europe/Paris` timezone.
*   **Error Handling:** Custom 404 and 500 error pages.

## Project Structure Overview

*   `/starshield`: Main Django project configuration (settings, URL routing, WSGI).
*   `/auths`: Manages the custom user model and authentication-related logic.
*   `/apps`: Contains modular Django applications:
    *   `/apps/dashboard`: Likely provides a personalized interface for users/businesses to manage their settings and view feedback.
    *   `/apps/reviews`: Implements the core review collection, conditional redirection, and internal feedback storage logic. This includes forms, views, and templates for the rating pages.
    *   `/apps/roulette`: The specific purpose of this application requires further investigation, but it might involve gamification, random selection, or a similar feature.
*   `/components`: Houses reusable UI components (e.g., `star_rating`).
