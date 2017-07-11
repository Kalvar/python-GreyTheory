from grey_class import *
import math

class GreyGM11 (GreyClass):

    def __init__(self):
        super(GreyGM11, self).__init__()
        self.forecasted_outputs = []
    
    def add_pattern(self, pattern, pattern_key):
        self._add_patterns(pattern, pattern_key)

    def __forecast_value(self, x1, a_value, b_value, k):
        return (1 - math.exp(a_value)) * (x1 - (b_value / a_value)) * math.exp(-a_value * k)
    
    def __forecast(self, patterns, period=1):
        self.remove_all_analysis()
        ago     = self.ago([patterns])
        z_boxes = ago[1]
        # Building B matrix, manual transpose z_boxes and add 1.0 to every sub-object.
        factors = []
        for z in z_boxes:
            x_t = []
            # Add negative z
            x_t.append(-z)
            x_t.append(1.0)
            factors.append(x_t)
        
        # Building Y matrix to be output-goals of equations.
        y_vectors = []
        for passed_number in patterns[1::]:
            y_vectors.append(passed_number)
        
        solved_equations = self.grey_math.solve_equations(factors, y_vectors)
        # Then, forecasting them at all include next moment value.
        analyzed_results = []
        sum_error = 0.0
        x1        = patterns[0]
        a_value   = solved_equations[0]
        b_value   = solved_equations[1]
        k         = 1
        length    = len(patterns)
        for passed_number in patterns[1::]:
            grey_forecast  = GreyForecast()
            forecast_value = self.__forecast_value(x1, a_value, b_value, k)

            original_value  = patterns[k]
            error_rate      = abs((original_value - forecast_value) / original_value)
            sum_error      += error_rate
            grey_forecast.tag = self._TAG_FORECAST_HISTORY
            grey_forecast.k   = k
            grey_forecast.original_value = original_value
            grey_forecast.forecast_value = forecast_value
            grey_forecast.error_rate     = error_rate

            analyzed_results.append(grey_forecast)
            k += 1
        
        # Continuous forecasting next moments.
        if period > 0:
            for go_head in range(0, period):
                forecast_value = self.__forecast_value(x1, a_value, b_value, k)

                grey_forecast     = GreyForecast()
                grey_forecast.tag = self._TAG_FORECAST_NEXT_MOMENT
                grey_forecast.k   = k # This k means the next moment of forecasted.
                grey_forecast.average_error_rate = sum_error / (length - 1)
                grey_forecast.forecast_value     = forecast_value
                analyzed_results.append(grey_forecast)
                k += 1

        self.analyzed_results = analyzed_results
        return analyzed_results
    
    def forecast(self, period=1):
        self.__forecast(self.patterns, period)

    # stride: the N-gram, shift step-size for each forecasting.
    # length: the Filter kernel, shift length of distance for each forecasting.
    def forecast_convolution(self, stride=1, length=4):
        pattern_count = len(self.patterns)
        # Convolution formula: (pattern_count - length) / stride + 1, 
        # e.g. (7 - 3) / 1 + 1 = 5 (Needs to shift 5 times.)
        # e.g. (7 - 3) / 3 + 1 = 2.33, to get floor() or ceil()
        # total_times at least for once.
        total_times  = long(math.floor((pattern_count - length) / stride + 1))
        convolutions = []
        stride_index = 0
        for i in range(0, total_times):
            # If it is last convolution, we directly pick it all.
            stride_length = stride_index+length
            if i == total_times - 1:
                stride_length = len(self.patterns)

            convolution_patterns = self.patterns[stride_index:stride_length]
            period_forecasts     = self.__forecast(convolution_patterns)
            convolutions.append(period_forecasts)

            # Fetchs forecasted moment and revises it to be fix with average error rate.
            forecasted_moment    = period_forecasts[-1]
            forecasted_value     = forecasted_moment.forecast_value
            revised_value        = forecasted_value + (forecasted_value * forecasted_moment.average_error_rate)
            self.forecasted_outputs.append(revised_value)

            # Next stride start index.
            stride_index += stride
        
        #print "forecasted_outputs % r" % self.forecasted_outputs

        # Using extracted convolution that forecasted values to do final forecasting.
        if total_times > 1:
            self.__forecast(self.forecasted_outputs)
            self.forecasted_outputs.append(self.last_moment)
        
        return convolutions
    
    # In next iteration of forecasting, we wanna continue use last forecasted results to do next forecasting, 
    # but if we removed gm11.forecasted_outputs list before,  
    # we can use continue_forecasting() to extend / recall the last forecasted result come back to be convolutional features. 
    def continue_forecasting(self, last_forecasted_outputs = []):
        self.forecasted_outputs.extend(last_forecasted_outputs)
    
    # Clean forecasted outputs.
    def clean_forecasted(self):
        self.forecasted_outputs = []

    @property
    def last_moment(self):
        # Last GreyForecast() object is the next moment forecasted.
        return self.analyzed_results[-1].forecast_value



    