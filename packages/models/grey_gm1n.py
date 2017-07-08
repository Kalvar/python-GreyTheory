from grey_class import *

class GreyGM1N (GreyClass):

    def add_outputs(self, outputs, pattern_key):
        self._add_outputs(outputs, pattern_key)
    
    def add_patterns(self, patterns, pattern_key):
        self._add_patterns(patterns, pattern_key)

    def analyze(self):
        ago = self.ago(self.patterns)
        ago_boxes = ago[0]
        z_boxes   = ago[1]

        # Fetchs from ago_boxes[1] to [last] then transpose it.
        factors = np.asarray(ago_boxes[1:len(ago_boxes)]).T.tolist()
        grey_equations = factors[1:len(factors)]
        # Then, to add -Z value from z_boxes into every sub-factors.
        index = -1
        for z_value in z_boxes:
            index += 1
            grey_equations[index].insert(0, -z_value)
        # Refactoring that x1 (the outputs) to be an output vector by following the Grey Theory GM(1, N) formula
        outputs = self.patterns[0][1::]
        solved_equations = self.grey_math.solve_equations(grey_equations, outputs)

        # Desc sorting the abs() equation values first, they named b(2) to b(n), but ignore the result (a) the output-goal factory in this loop
        sorts = []
        goal_factory = GreyFactory()
        length = len(solved_equations)
        for i in range(0, length):
            equation_value = abs(solved_equations[i])
            factory_info   = {}
            equation_name  = self.keys[i]
            grey_factory                = GreyFactory()
            grey_factory.name           = equation_name
            grey_factory.equation_value = equation_value
            if i > 0:
                sorts.append(grey_factory)
            else:
                goal_factory = grey_factory

        self.analyzed_results = sorted(sorts, key=lambda factory: factory.equation_value, reverse=True)
        self.analyzed_results.insert(0, goal_factory) # The output-goal always is number 1.
        ranking = -1
        for grey_factory in self.analyzed_results:
            ranking += 1
            grey_factory.ranking = ranking
            # Raning 0 is the output-goal (a), the output-goal is not the influence degree, 
            # Other paramenters are the real influence degrees of GM1N.
            if ranking > 0:
                self.influence_degrees.append(grey_factory.name)
            #print "gm1n %r" % grey_factory.name
        
            
