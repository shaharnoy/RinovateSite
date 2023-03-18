from __future__ import division
import pyomo.environ as pyo

model = pyo.AbstractModel()

# declare the parameters
model.m = pyo.Param(within=pyo.NonNegativeIntegers)
model.n = pyo.Param(within=pyo.NonNegativeIntegers)

# define index sets
model.I = pyo.Set()
model.J = pyo.Set()

# The coefficient and right-hand-side data are defined as indexed parameters.
# When sets are given as arguments to the Param component, they indicate that the set will index the parameter.
model.a = pyo.Param(model.I, model.J)
model.b = pyo.Param(model.I)
model.c = pyo.Param(model.J)

# the next line declares a variable indexed by the set J
model.x = pyo.Var(model.J, domain=pyo.NonNegativeReals)


def obj_expression(m):
    return pyo.summation(m.c, m.x)


model.OBJ = pyo.Objective(rule=obj_expression, sense=1)


def ax_constraint_rule(m, i):
    # return the expression for the constraint for i
    return sum(m.a[i, j] * m.x[j] for j in m.J) >= m.b[i]


# the next line creates one constraint for each member of the set model.I
model.AxbConstraint = pyo.Constraint(model.I, rule=ax_constraint_rule)

# results = pyo.SolverFactory('glpk').solve(model)
