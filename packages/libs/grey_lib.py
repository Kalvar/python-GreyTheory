import numpy as np

class GreyLib:
    
    def __init__(self, alpha=0.5):
        self.alpha = alpha

    # Generates AGO via patterns.
    def ago(self, patterns):
        # do ago
        ago_boxes = [] #np.array([], dtype=np.float)
        z_boxes   = []
        pattern_index = 0
        # x1 which is index 0 the output, x2 ~ xn are the inputs.
        for x_patterns in patterns:
            x_ago   = []
            sum     = 0.0
            z_value = 0.0
            x_index = 0
            for x_value in x_patterns:
                sum += x_value
                x_ago.append(sum)
                # Only first pattern need to calculate the Z value.
                if pattern_index == 0 and x_index > 0:
                    # Alpha 0.5 that means z is mean value, others alpha number means z is IAGO.
                    z_value = (self.alpha * sum) + (self.alpha * x_ago[x_index - 1])
                    z_boxes.append(z_value)
                x_index += 1
            ago_boxes.append(x_ago)
            pattern_index += 1
        
        return (ago_boxes, z_boxes)

    