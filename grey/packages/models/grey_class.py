import numpy as np
from ..libs.grey_lib import GreyLib
from ..libs.grey_math import GreyMath
from grey_factory import GreyFactory

class GreyClass:

    def __init__(self):
        self.patterns          = []
        self.keys              = []
        self.analyzed_results  = []
        self.influence_degrees = []
        self.grey_lib          = GreyLib()
        self.grey_math         = GreyMath()
    
    # Those outputs are the results of all patterns.
    def add_outputs(self, outputs, pattern_key):
        self.patterns.insert(0, outputs)
        self.keys.append(pattern_key)
    
    # Those patterns are using in AGO generator.
    def add_patterns(self, patterns, pattern_key):
        self.patterns.append(patterns)
        self.keys.append(pattern_key)

    def ago(self):
        return self.grey_lib.ago(self.patterns)
    
    def print_self(self):
        print "%r" % self.__class__.__name__

    def print_analyzed_results(self):
        self.print_self()
        for factory in self.analyzed_results:
            print "pattern key: %r, grey value: %r, ranking: %r" % (factory.name, factory.equation_value, factory.ranking)

    def print_influence_degrees(self):
        self.print_self()
        string = " > ".join(self.influence_degrees)
        print "Printing the keys of parameters their influence degrees (ordering): %r" % string
