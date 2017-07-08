import numpy as np
from ..libs.grey_lib import GreyLib
from ..libs.grey_math import GreyMath
from grey_factory import GreyFactory
from grey_forecast import GreyForecast

class GreyClass (object):

    def __init__(self):
        self.patterns          = []
        self.keys              = []
        self.analyzed_results  = []
        self.influence_degrees = []
        self.forecasts         = []
        self.grey_lib          = GreyLib()
        self.grey_math         = GreyMath()
    
    # Those outputs are the results of all patterns.
    def _add_outputs(self, outputs, pattern_key):
        self.patterns.insert(0, outputs)
        self.keys.append(pattern_key)
    
    # Those patterns are using in AGO generator.
    def _add_patterns(self, patterns, pattern_key):
        self.patterns.append(patterns)
        self.keys.append(pattern_key)

    def ago(self, patterns):
        return self.grey_lib.ago(patterns)
    
    def print_self(self):
        print "%r" % self.__class__.__name__

    def print_analyzed_results(self):
        self.print_self()
        for factory in self.analyzed_results:
            print "Result, pattern key: %r, grey value: %r, ranking: %r" % (factory.name, factory.equation_value, factory.ranking)

    def print_influence_degrees(self):
        self.print_self()
        string = " > ".join(self.influence_degrees)
        print "Result, The keys of parameters their influence degrees (ordering): %r" % string

    def print_forecasted_results(self):
        self.print_self()
        for forecast in self.analyzed_results[0:-2]:
            print "Result, from original value %r to forecasted value is %r" % (forecast.original_value, forecast.forecast_value)
            print "The error rate is %r and k is %r" % (forecast.error_rate, forecast.k)
        
        next_moment = self.analyzed_results[-1]
        print "Forcated next moment value is %r and the average error rate %r" % (next_moment.forecast_value, next_moment.average_error_rate)
        print "The k is %r" % next_moment.k