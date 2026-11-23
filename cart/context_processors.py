from .cart import Cart


def cart(request):
    """`cart` in every template; len(cart) for the header badge costs no query."""
    return {"cart": Cart(request)}
