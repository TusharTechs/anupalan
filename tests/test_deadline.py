from datetime import date

from anupalan.deadline import compute

D = date(2025, 4, 29)


def test_fortnight_from_order():
    d = compute("The State of Punjab and PSPCL are directed to release all pending installments within a fortnight.", date(2026, 8, 3))
    assert d.due == date(2026, 8, 17)
    assert d.anchor == "order_date"


def test_weeks_from_certified_copy():
    d = compute("The respondents shall pass a speaking order within six weeks from the date of receipt of a certified copy of this order.", D)
    assert d.anchor == "receipt_of_copy"
    assert d.due == date(2025, 6, 17)  # 29 Apr + 7 days + 6 weeks
    assert d.certainty == "assumed_anchor"


def test_chained_representation():
    s = ("However, in case a fresh representation is filed within 4 weeks, the same be decided within a "
         "further period of 3 months from its receipt, in accordance with law.")
    d = compute(s, D)
    assert d.certainty == "conditional"
    assert d.due == date(2025, 8, 27)  # 29 Apr + 4 weeks = 27 May, + 3 months = 27 Aug


def test_months_from_today():
    d = compute("The claim be decided within a period of three months from today.", D)
    assert d.due == date(2025, 7, 29)
    assert d.certainty == "exact"


def test_open_ended():
    d = compute("The respondents are directed to consider the case of the petitioner expeditiously.", D)
    assert d.due is None and d.certainty == "open_ended"


def test_no_deadline():
    assert compute("The writ petition is dismissed.", D) is None
