from buggy_discount import calculate_discount

def test_below_threshold():
    assert calculate_discount(999) == 999

def test_exact_threshold():
    assert calculate_discount(1000) == 900

def test_above_threshold():
    assert calculate_discount(1001) == 900.9
