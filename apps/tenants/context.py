from contextvars import ContextVar

_current_restaurant = ContextVar('current_restaurant', default=None)


def get_current_restaurant():
    return _current_restaurant.get()


def set_current_restaurant(restaurant):
    _current_restaurant.set(restaurant)


def clear_current_restaurant():
    _current_restaurant.set(None)
