from grey_class import *

class GreyGM0N (GreyClass):

    def add_outputs(self, outputs, pattern_key):
        self._add_outputs(outputs, pattern_key)
    
    def add_patterns(self, patterns, pattern_key):
        self._add_patterns(patterns, pattern_key)

    def analyze(self):
        self.remove_all_analysis()
        
        ago       = self.ago(self.patterns)
        ago_boxes = ago[0]
        z_boxes   = ago[1] # X

        # Fetchs ago matrixes after x2[1] (ago_boxes[1]) then transpose them.
        factors = np.asarray(ago_boxes[1:len(ago_boxes)]).T.tolist()
        grey_equations = factors[1:len(factors)] # Y

        # all_factors are the equations (x, y, z ...) and z_boxes are the goals of equations.
        solved_equations = self.grey_math.solve_equations(grey_equations, z_boxes) # B
        
        # Desc sorting the abs() equation values
        sorts = []
        length = len(solved_equations)
        for i in range(0, length):
            equation_value = abs(solved_equations[i])
            factory_info   = {}
            equation_name  = self.keys[i+1] # The keys of patterns are start in index 1, the index 0 is key of output-goal.
            grey_factory                = GreyFactory()
            grey_factory.name           = equation_name
            grey_factory.equation_value = equation_value
            sorts.append(grey_factory)

        # DESC
        # key=lambda d: d["equation_value"]
        self.analyzed_results = sorted(sorts, key=lambda factory: factory.equation_value, reverse=True)
        # Ranking all grey factories and setup their influence degrees step by step.
        ranking = 0
        for grey_factory in self.analyzed_results:
            ranking += 1
            grey_factory.ranking = ranking
            self.influence_degrees.append(grey_factory.name)
            #print "gm0n %r" % grey_factory.name
        

