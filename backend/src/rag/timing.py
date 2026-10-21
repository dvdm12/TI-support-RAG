"""Monotonic wall-clock stage durations, including retries and failed attempts."""
from contextlib import contextmanager
from time import perf_counter


@contextmanager
def measure(timings, name):
    started = perf_counter()
    try:
        yield
    finally:
        # Accumulate repeated stages (validation/review after a correction).
        timings[name] = timings.get(name, 0.0) + perf_counter() - started
