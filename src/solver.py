from pulp import *
import numpy as np
# from cvxopt import matrix, solvers
import cvxpy as cp

#open source solver: SCIP, HIGHS, CYLP
# installieren mit: python -m pip install pulp[open_py]

# Create two scalar optimization variables.
x = cp.Variable()
y = cp.Variable()

# Create two constraints.
constraints = [x + y == 1,
               x - y >= 1]

# Form objective.
obj = cp.Minimize((x - y)**2)

# Form and solve problem.
prob = cp.Problem(obj, constraints)
prob.solve()  # Returns the optimal value.
print("status:", prob.status)
print("optimal value", prob.value)
print("optimal var", x.value, y.value)

k = ...  # Dimension
w = ...  # Gewichtsmatrix w_{i,j} als numpy Array (k x k)
span_matrix = ...  # Matrix mit span(a_l, a_h) Werten (k x k)

# Optimierungsvariable x der Form k x k
x = cp.Variable((k, k))

# Variable zur Akkumulation der Summe
obj_expr = 0

for i in range(k):
    for j in range(k):
        for l in range(k):
            for h in range(k):
                obj_expr += x[i, l] * x[j, h] * span_matrix[l, h] * w[i, j]

objective = cp.Minimize(obj_expr)

# Optional: Constraints definieren
constraints = []

problem = cp.Problem(objective, constraints)

result = problem.solve()

print("Minimaler Zielfunktionswert:", result)
print("Optimale Lösung x:", x.value)