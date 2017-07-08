import numpy as np

class GreyMath:

    # Least Squares Method (LSM) to solve the equations, solves that simultaneous equations.
    def solve_equations(self, equations, equals):
        # Formula is ( B^T x B )^-1 x B^T x Yn, to be a square matrix first.
        transposed_equations = np.asarray(equations).T.tolist()
        # Doing ( B^T x B )
        square_matrix = np.dot(transposed_equations, equations)
        # Doing (B^T x Yn)
        bx_y = np.dot(transposed_equations, equals)
        # Solves equations.
        return np.linalg.solve(square_matrix, bx_y).tolist()
