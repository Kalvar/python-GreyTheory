#!/usr/bin/python 
# -*- coding: utf-8 -*-
import sys
import json
from grey_theory import GreyTheory

# GM11
gm11 = GreyTheory().gm11
gm11.alpha = 0.5
gm11.convolution = True
gm11.stride = 1 
gm11.length = 4

numbers = json.loads(sys.argv[1])
print numbers

for (i, num) in enumerate(numbers):
  gm11.add_pattern(num, str(i))

gm11.forecast()
gm11.print_forecasted_results()