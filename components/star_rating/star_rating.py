from typing import NamedTuple

from django_components import Component, register


@register("star_rating")
class StarRating(Component):
    template_file = "template.html"

    class Kwargs(NamedTuple):
        input_id: str
        initial_rating: int | None
        readonly: bool

    class Defaults:
        initial_rating = None
        readonly = False

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        rating = kwargs.initial_rating if kwargs.initial_rating is not None else 0
        rating = max(0, min(5, rating))

        return {
            "input_id": kwargs.input_id,
            "rating": rating,
            "readonly": kwargs.readonly,
            "stars": range(1, 6),
        }

