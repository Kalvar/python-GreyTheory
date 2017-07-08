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

gm11.add_pattern(533.0, "x1")
gm11.add_pattern(665.0, "x2")
gm11.add_pattern(655.0, "x3")
gm11.add_pattern(740.0, "x4")
gm11.forecast()

# Looks GM11 the results for example as below:
gm11.print_forecasted_results()