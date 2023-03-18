from __future__ import division
import pyomo.environ as pyo
import numpy as np

model = pyo.AbstractModel()
# define sets
model.RelationTypes = pyo.Set()  # set of tasks relatioships
model.K = pyo.Set()  # Set of tasks
model.M = pyo.Set()  # Set of crafters

# Set P_UNIVERSE -  auxiliary set of all possible relations
def P_UNIVERSE_init(model):
    return ((k1, k2) for k1 in model.K for k2 in model.K if k1 != k2)
model.P_UNIVERSE = pyo.Set(initialize=P_UNIVERSE_init)

# Set P_ALL -  auxiliary  of all relations
def P_ALL_init(model):
    return ((k1, k2, r) for (k1, k2) in model.P_UNIVERSE for r in model.RelationTypes)
model.P_ALL = pyo.Set(initialize=P_ALL_init, within=model.P_UNIVERSE * model.RelationTypes)

# Set P_free - free precedence relations
def P_free_init(model):
    return ((k1, k2) for (k1, k2, r) in model.P_ALL if r == "FREE")
model.P_free = pyo.Set(initialize=P_free_init, within=model.P_UNIVERSE)

# Set P_same - same crafter precedence relations
def P_same_init(model):
    return ((k1, k2) for (k1, k2, r) in model.P_ALL if r == "SAME")
model.P_same = pyo.Set(initialize=P_same_init, within=model.P_UNIVERSE)

# Set P_prot - protected precedence relations
def P_prot_init(model):
    return ((k1, k2) for (k1, k2, r) in model.P_ALL if r == "PROTECTED")
model.P_prot = pyo.Set(initialize=P_prot_init, within=model.P_UNIVERSE)

# Set P_mutex - mutual exclusion relations
def P_mutex_init(model):
    return ((k1, k2) for (k1, k2, r) in model.P_ALL if r == "MUTEX")
model.P_mutex = pyo.Set(initialize=P_mutex_init, within=model.P_UNIVERSE)

# Set P_parallel - parallel execution relations
def P_parallel_init(model):
    return ((k1, k2) for (k1, k2, r) in model.P_ALL if r == "PARALLEL")
#TODO: The parallel rule should be depended on available timeslots - it's not mandatory to do the task together.
model.P_parallel = pyo.Set(initialize=P_parallel_init, within=model.P_UNIVERSE)

# Set P_Together - Together execution relationsq (Must do together)
def P_Together_init(model):
    return ((k1, k2) for (k1, k2, r) in model.P_ALL if r == "TOGETHER")
model.P_Together = pyo.Set(initialize=P_Together_init, within=model.P_UNIVERSE)

# Set P_prec all precedence relations
model.P_prec = pyo.Set(
    initialize=model.P_same.union(model.P_prot).union(model.P_free),
    within=model.P_UNIVERSE,
)

"""
# Set K_craft - only tasks associated with the right crafter
def K_craft_init(model):
    return ((k, m) for (k1, k2, r) in model.K_All if r == "PARALLEL")


model.K_craft = pyo.Set(initialize=P_parallel_init, within=model.P_UNIVERSE)
"""
# define parameters

model.U_exec = pyo.Param(model.K)
#execution time of task k if done by Crafter m

model.C_exec = pyo.Param(model.M)
#execution cost of task k if done by Crafter m

model.N_crafter = pyo.Param(model.M)  
# predefined maximum number of used job slots for crafter m

model.M_Count = pyo.Param(model.M)
# number of available crafters per m

# Define set of time slots for execution
def J_slots_init(model):
    return [(m, i) for m in model.M for i in range(1, 2 * model.N_crafter[m] + 1)]  
# 30 mins slots 2*8=16 slots
model.J_slots = pyo.Set(initialize=J_slots_init, dimen=2, ordered=True)

# Define set of cost per task k for crafter m
def Cost_crafter_init(model):
    return {(m, k): model.U_exec[k] * model.C_exec[m] for m in model.C_exec for k in model.U_exec}
model.Cost_crafter_Set = pyo.Set(initialize=Cost_crafter_init, dimen=2, ordered=True)
model.Cost_crafter = pyo.Param(model.Cost_crafter_Set, initialize=Cost_crafter_init)


model.T_day_start = pyo.Param(model.M)  # starting time of the day
model.T_day_end = pyo.Param(model.M)  # ending time of the day
model.U_WORKDAY = pyo.Param(model.M) #TODO:Make calculated

model.K_all = pyo.Param(model.K,model.M)

def K_all_init(model):
    return [(k,m,model.K_all[k,m]) for k,m in model.K_all]
model.K_all_fixed = pyo.Set(initialize=K_all_init)

# Variables
model.al = pyo.Var(model.K, model.J_slots, within=pyo.Binary)
# al[k,m,i] denotes if task k is executed by team m on its job slot (m,i)

model.al_task = pyo.Var(model.K, model.M, within=pyo.Binary)
# al_task[k,m] denotes if task k is executed by team m on any of its job slots

model.Cost_crafter_Var= pyo.Var(model.Cost_crafter_Set,bounds=(0,300))

model.p_prot = pyo.Var(model.P_prot, within=pyo.Binary)
# p_prot[k1,k2] denotes if, for the protected precedence relation (k1,k2)

model.p_mutex = pyo.Var(model.P_mutex, within=pyo.Binary)
# p_mutex[k1,k2] denotes if the mutual exclusion relation (k1,k2)

model.cost_execution = pyo.Var()
# all execution costs, based on the pure execution costs of tasks for the corresponding team

# TODO: change the bounderies to be driven and based on Crafter
model.t_task_start = pyo.Var(model.K, bounds=("8.00", "16.00"))  
# t_task_start[k] is the time the execution of task k starts

model.t_task_end = pyo.Var(model.K, bounds=("8.00", "16.00"))  
# t_task_end[k] is the time the execution of task k ends

model.t_task_presence_start = pyo.Var(model.K, bounds=("8.00", "16.00"))  
# t_task_presence_start[k] is the time from which the executing team for task k is present at the site

model.t_task_presence_end = pyo.Var(model.K, bounds=("8.00", "16.00"))  
# t_task_presence_end[k] is the time until which the executing team for task k is present at the site

# Obejective

# obj function should be --> sum {k in K, m in M} (al_task[k,m] * C_exec[k,m]);
def obj(model):
    #return sum(model.al_task[k, m] * model.U_exec[k, m] for k in model.K for m in model.M)
    return [(model.al_task[k, m] * model.Cost_crafter_Var[k, m]) for k in model.K for m in model.M]
#model.check = pyo.Set(initialize=obj)

#model.obj=pyo.Objective(rule=obj, sense=pyo.minimize)

# CONSTRAINTS

def c01_rule(model, k, m):
    return model.al_task[k, m] == sum(model.al[k, m, i] for i in model.J_slots if (m, i) in model.J_slots)
model.c01 = pyo.Constraint(model.K, model.M, rule=c01_rule)
# a task is executed by a crafter m if it is assigned to a job slot (m,i) of crafter m

def c02_rule(model, k):
    return 1 == sum(model.al_task[k, m] for m in model.M)
model.c02 = pyo.Constraint(model.K, rule=c02_rule)
# all tasks must be executed by exactly one crafter m

def c03_rule(model, m, i):
    if i > 1:
        return sum(model.al[k, m, i - 1] for k in model.K) >= sum(model.al[k, m, i] for k in model.K)
    else:
        return pyo.Constraint.Skip
model.C03 = pyo.Constraint(model.J_slots, rule=c03_rule)
# job slots must be used in strict order: no job slot can be skipped if the next one is used


# Task Relations
def c30_rule(model, k1, k2):
    return model.t_task_end[k1] <= model.t_task_start[k2]
model.C30 = pyo.Constraint(model.P_prec, rule=c30_rule)
# for all precedence relations, the second task may start after the first one is finished


def c31_rule(model, k1, k2, m):
    return model.al_task[k1, m] == model.al_task[k2, m]
model.C31 = pyo.Constraint(model.P_same, model.M, rule=c31_rule)
# for all same type relations, the tasks must be assigned to job slots of the same crafter


def c32_rule(model, k1, k2, m):
    return (
        model.t_task_presence_start[k2] - model.t_task_presence_end[k1]
        <= model.U_WORKDAY[m] * model.p_prot[k1, k2]
           )
model.C32 = pyo.Constraint(model.P_prot, model.M, rule=c32_rule)
# for a protected precedence relation the task presences must meet

def c37_rule(model, k1, k2, m):
    return model.t_task_start[k2] - model.t_task_end[k1] >= (-1) * model.U_WORKDAY[m] * (1 - model.p_mutex[k1, k2])
model.C37 = pyo.Constraint(model.P_mutex, model.M, rule=c37_rule)
# for any mutex the first task must end before the second task may start

def c38_rule(model, k1, k2, m):
    return (model.t_task_start[k1] - model.t_task_end[k2] >= (-1) * model.U_WORKDAY[m] * model.p_mutex[k1, k2])
model.C38 = pyo.Constraint(model.P_mutex, model.M, rule=c38_rule)
# for any mutex the second task must end before the first task may start

def c39_rule(model, k1, k2, m):
    return model.t_task_start[k1] == model.t_task_start[k2]
# TODO: make it optional if the time slots are available, otherwise it's not neccesary.
model.C39 = pyo.Constraint(model.P_parallel,model.M, rule=c39_rule)
# for parallel execution relations, tasks' starting times coincide

def c40_rule(model, k1, k2, m):
    return model.t_task_start[k1] == model.t_task_start[k2]
model.C40 = pyo.Constraint(model.P_Together,model.M, rule=c40_rule)
# for Together execution relations - they should be done at the same time

# Costs
"""
def C44_rule(model):
    return model.cost_execution == sum(
        model.al_task[k, m] * model.C_exec[k, m] for k in model.K for m in model.M
    )


model.C44 = pyo.Constraint(rule=C44_rule)
# execution costs are based solely on job slot assignment


def C48_rule(model):
    return model.time_total == model.cost_execution


model.C48 = pyo.Constraint(rule=C48_rule)
# total cost is the sum of all the cost components - todo:extend when model go wide


# obj function should be --> sum {k in K, m in M} (al_task[k,m] * C_exec[k,m]);
def obj(model):
    return sum(
        model.al_task[k, m] * model.U_exec[k, m] for k in model.K for m in model.M
    )


# check check
model.time_total = pyo.Objective(rule=obj, sense=pyo.minimize)
"""
instance = model.create_instance("firstDraft.dat")
model.construct()
#results = pyo.SolverFactory("glpk").solve(instance)
# Print the model information to a text file using pprint()
with open('abstractmodel_info.txt', 'w') as f:
    instance.pprint(ostream=f)
# pyomo solve firstDraft.py firstDraft.dat --solver='glpk'
