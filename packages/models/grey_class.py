import numpy as np
from ..libs.grey_lib import GreyLib
from ..libs.grey_math import GreyMath
from grey_factory import GreyFactory
from grey_forecast import GreyForecast

class GreyClass (object):

    _TAG_FORECAST_NEXT_MOMENT = "forecasted_next_moment"
    _TAG_FORECAST_HISTORY     = "history"

    def __init__(self):
        self.patterns          = []
        self.keys              = []
        self.analyzed_results  = []
        self.influence_degrees = []
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
    
    def remove_all_analysis(self):
        # Deeply removing without others copied array.
        self.analyzed_results  = []
        self.influence_degrees = []
        self.forecasts         = []

        # Removing all reference links with others array.
        #del self.analyzed_results
        #del self.influence_degrees
        #del self.forecasts

    def print_self(self):
        print "%r" % self.__class__.__name__

    def print_analyzed_results(self):
        self.print_self()
        for factory in self.analyzed_results:
            print "Pattern key: %r, grey value: %r, ranking: %r" % (factory.name, factory.equation_value, factory.ranking)

    def print_influence_degrees(self):
        self.print_self()
        string = " > ".join(self.influence_degrees)
        print "The keys of parameters their influence degrees (ordering): %r" % string

    def print_forecasted_results(self):
        self.print_self()
        for forecast in self.analyzed_results:
            print "K = %r" % forecast.k
            if forecast.tag == self._TAG_FORECAST_HISTORY:
                # History.
                print "From original value %r to forecasted value is %r" % (forecast.original_value, forecast.forecast_value)
                print "The error rate is %r" % forecast.error_rate
            else:
                # Next moments.
                print "Forcated next moment value is %r" % forecast.forecast_value
        
        # Last forecasted moment.
        last_moment = self.analyzed_results[-1]
        print "The average error rate %r" % last_moment.average_error_rate

    @property
    def alpha(self):
        return self.grey_lib.alpha
    
    @alpha.setter
    def alpha(self, value = 0.5):
        self.grey_lib.alpha = value