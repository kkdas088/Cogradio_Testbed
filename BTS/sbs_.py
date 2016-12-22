#!/usr/bin/env python
import random


def sense_busy():
    print "in sense_busy()"
    i = random.randint(1, 100)
    if (i<= 40):
        return True
    else:
        return False
