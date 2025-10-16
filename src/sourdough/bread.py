def make_bread(flour_grams: int, water_grams: int) -> dict:
    """Return a simple recipe dict and hydration.

    hydration = water / flour * 100
    """
    if flour_grams <= 0:
        raise ValueError("flour_grams must be > 0")
    hydration = (water_grams / flour_grams) * 100
    return {"flour": flour_grams, "water": water_grams, "hydration": hydration}
