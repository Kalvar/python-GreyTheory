#!/usr/bin/python 
# -*- coding: utf-8 -*-

from grey_theory import GreyTheory

grey = GreyTheory()


# GM0N
gm0n = grey.gm0n

gm0n.add_outputs([1., 1., 1., 1., 1., 1.], "x1")
gm0n.add_patterns([.75, 1.22, .2, 1., 1., 1.], "x2")
gm0n.add_patterns([.5, 1., .7, .66, 1., .5], "x3")
gm0n.add_patterns([1., 1.09, .4, .33, .66, .25], "x4")
gm0n.add_patterns([.25, .99, 1., .66, .33, .25], "x5")

gm0n.analyze()

# Looks GM0N the results as below:
gm0n.print_analyzed_results()
gm0n.print_influence_degrees()

# GM1N
gm1n = grey.gm1n

gm1n.add_outputs([2., 11., 1.5, 2., 2.2, 3.], "x1")
gm1n.add_patterns([3., 13.5, 1., 3., 3., 4.], "x2")
gm1n.add_patterns([2., 11., 3.5, 2., 3., 2.], "x3")
gm1n.add_patterns([4., 12., 2., 1., 2., 1.], "x4")
gm1n.add_patterns([1., 10., 5., 2., 1., 1.], "x5")

gm1n.analyze()

# Looks GM1N the results as below:
gm1n.print_analyzed_results()
gm1n.print_influence_degrees()

# GM11
gm11 = grey.gm11

# To try customized alpha for IAGO of Z.
gm11.alpha = 0.5
gm11.convolution = True # Convolutional forecasting of GM11.
gm11.stride = 1 
gm11.length = 4

# gm11.add_pattern(533.0, "x1")
# gm11.add_pattern(665.0, "x2")
# gm11.add_pattern(655.0, "x3")
# gm11.add_pattern(740.0, "x4")

gm11.add_pattern(223.3, "a1")
gm11.add_pattern(227.3, "a2")
gm11.add_pattern(230.5, "a3")
gm11.add_pattern(238.1, "a4")
gm11.add_pattern(242.9, "a5")
gm11.add_pattern(251.1, "a6")

gm11.forecast()

# To record last forecasted result.
#last_forecasted_results = gm11.forecasted_outputs

# To clean all forecasted results. 
#gm11.clean_forecasted()

# In next iteration of forecasting, we wanna continue use last forecasted results to do next forecasting, 
# but if we removed gm11.forecasted_outputs list before,  
# we can use continue_forecasting() to extend / recall the last for ecasted result come back to be convolutional features. 
#gm11.continue_forecasting(last_forecasted_results)

# Looks GM11 the results for example as below:
gm11.print_forecasted_results()

"""
# multiprocessing examples:
# for GM0N, GM1N
queue = []
queue.append(gm0n.deepcopy())
queue.append(gm0n.deepcopy())
queue.append(gm0n.deepcopy())
queue.append(gm0n.deepcopy())
queue.append(gm0n.deepcopy())
queue.append(gm0n.deepcopy())
queue.append(gm0n.deepcopy())

grey.run.gm0n(queue)

for gm in queue:
    gm.print_influence_degrees()

# for GM11
gm11_queue = []
gm11_queue.append(gm11.deepcopy())
gm11_queue.append(gm11.deepcopy())
gm11_queue.append(gm11.deepcopy())
gm11_queue.append(gm11.deepcopy())
gm11_queue.append(gm11.deepcopy())
gm11_queue.append(gm11.deepcopy())
gm11_queue.append(gm11.deepcopy())

grey.run.gm11(gm11_queue)

for gm in gm11_queue:
    gm.print_forecasted_results()

"""
