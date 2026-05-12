import itertools
import decimal

values = {
    '5109': decimal.Decimal('2370127.51'),
    '5159': decimal.Decimal('77900.75'),
    '5209': decimal.Decimal('3129.87'),
    '5409': decimal.Decimal('1019198.67'),
    '5909': decimal.Decimal('54547.16')
}

target = decimal.Decimal('3388174.98')

# test additions and subtractions
keys = list(values.keys())
for r in range(1, len(keys)+1):
    for combo in itertools.combinations(keys, r):
        for signs in itertools.product([1, -1], repeat=r):
            total = sum(values[k] * s for k, s in zip(combo, signs))
            if abs(total - target) < decimal.Decimal('1.00'):
                print(f"Match found! {combo} with signs {signs} = {total}")

