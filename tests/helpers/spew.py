#!/usr/bin/env python
"""Generates output incrementally, flushing after each line"""
import time

print("Split line first part", end="", flush=True)
time.sleep(0.6)
print(", second part", flush=True)

print("2nd line", flush=True)
time.sleep(1.0)
print("3rd line (last line)", flush=True)

# end of spew.py
