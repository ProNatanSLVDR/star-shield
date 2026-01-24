from typing import NamedTuple

from django.template.defaultfilters import timesince, truncatewords
from django_components import Component, Default, register
from typing_extensions import Any


@register("review")
class Review(Component):
    template_file = "template.html"

    class Kwargs(NamedTuple):
        review: Any  # Review model instance
        show_badge: bool = Default(True)
        show_timestamp: bool = Default(False)
        truncate_comment: bool = Default(False)
        truncate_words: int = Default(20)

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        review = kwargs.review
        show_badge = kwargs.show_badge
        show_timestamp = kwargs.show_timestamp
        truncate_comment = kwargs.truncate_comment
        truncate_words = kwargs.truncate_words

        # Extract review data
        is_google = review.source == "google"
        google_data = review.google_reviewer_data or {}

        # Get reviewer name
        if is_google and google_data.get("displayName"):
            reviewer_name = google_data.get("displayName")
        else:
            reviewer_name = "Anonyme"

        # Get profile picture URL
        profile_photo_url = None
        if is_google and google_data.get("profilePhotoUrl"):
            profile_photo_url = google_data.get("profilePhotoUrl")

        # Process comment
        comment = review.comment or ""
        if comment and "(Original)" in comment:
            # Use the after_original filter logic
            parts = comment.split("(Original)", 1)
            if len(parts) > 1:
                comment = parts[1].strip()

        comment_display = comment
        if truncate_comment and comment:
            comment_display = truncatewords(comment, truncate_words)

        # Get timestamp
        timestamp_display = None
        if show_timestamp:
            review_date = review.writen_at or review.created_at
            if review_date:
                timestamp_display = timesince(review_date)

        return {
            "review": review,
            "is_google": is_google,
            "reviewer_name": reviewer_name,
            "profile_photo_url": profile_photo_url,
            "rating": review.rating,
            "comment": comment,
            "comment_display": comment_display,
            "has_comment": bool(comment),
            "show_badge": show_badge,
            "show_timestamp": show_timestamp,
            "timestamp_display": timestamp_display,
        }
