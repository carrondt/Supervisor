import threading
import random
import time
import math
import csv
import json
import time

import numpy as np

from deap import base
from deap import creator
from deap import tools
from deap import algorithms

import eqpy, ga_utils

# list of ga_utils parameter objects
ga_params = None

def obj_func(x):
    return 0

# {"batch_size":512,"epochs":51,"activation":"softsign",
#"dense":"2000 1000 1000 500 100 50","optimizer":"adagrad","drop":0.1378,
#"learning_rate":0.0301,"conv":"25 25 25 25 25 1"}
def create_list_of_json_strings(list_of_lists, super_delim=";"):
    # create string of ; separated jsonified maps
    res = []
    global ga_params
    for l in list_of_lists:
        jmap = {}
        for i,p in enumerate(ga_params):
            jmap[p.name] = l[i]

        jstring = json.dumps(jmap)
        res.append(jstring)

    return (super_delim.join(res))

def create_fitnesses(params_string):
    """return equivalent length tuple list
    :type params_string: str
    """
    params = params_string.split(";")
    # get length
    res = [(i,) for i in range(len(params))]
    return (res)

def queue_map(obj_func, pops):
    # Note that the obj_func is not used
    # sending data that looks like:
    # [[a,b,c,d],[e,f,g,h],...]
    if not pops:
        return []
    eqpy.OUT_put(create_list_of_json_strings(pops))
    result = eqpy.IN_get()
    split_result = result.split(';')
    # TODO determine if max'ing or min'ing and use -9999999 or 99999999
    return [(float(x),) if not math.isnan(float(x)) else (float(99999999),) for x in split_result]
    #return [(float(x),) for x in split_result]

def make_random_params():
    """
    Performs initial random draw on each parameter
    """
    global ga_params

    draws = []
    for p in ga_params:
        draws.append(p.randomDraw())

    return draws

def parse_init_params(params_file):
    init_params = []
    with open(params_file) as f_in:
        reader = csv.reader(f_in)
        header = next(reader)
        for row in reader:
            init_params.append(dict(zip(header,row)))
    return init_params

def update_init_pop(pop, params_file):
    global ga_params
    print("Reading initial population from {}".format(params_file))
    init_params = parse_init_params(params_file)
    if len(pop) > len(init_params):
        raise ValueError("Not enough initial params to set the population: size of init params < population size")

    for i, indiv in enumerate(pop):
        for j, param in enumerate(ga_params):
            indiv[j] = param.parse(init_params[i][param.name])

# keep as reference for log type
# def mutGaussian_log(x, mu, sigma, mi, mx, indpb):
#     if random.random() < indpb:
#         logx = math.log10(x)
#         logx += random.gauss(mu, sigma)
#         logx = max(mi, min(mx, logx))
#         x = math.pow(10, logx)
#     return x

# Returns a tuple of one individual
def custom_mutate(individual, indpb):
    """
    Mutates the values in list individual with probability indpb
    """

    # Note, if we had some aggregate constraint on the individual
    # (e.g. individual[1] * individual[2] < 10), we could copy
    # individual into a temporary list and mutate though until the
    # constraint was satisfied

    global ga_params
    for i, param in enumerate(ga_params):
        individual[i] = param.mutate(individual[i], mu=0, indpb=indpb)

    return individual,

def cxUniform(ind1, ind2, indpb):
    c1, c2 = tools.cxUniform(ind1, ind2, indpb)
    return (c1, c2)

def timestamp(scores):
    return str(time.time())

def run():
    """
    :param num_iter: number of generations
    :param num_pop: size of population
    :param seed: random seed
    :param strategy: one of 'simple', 'mu_plus_lambda'
    :param ga parameters file name: ga parameters file name (e.g., "ga_params.json")
    :param param_file: name of file containing initial parameters
    """
    eqpy.OUT_put("Params")
    params = eqpy.IN_get()

    # parse params
    (num_iter, num_pop, seed, strategy, mut_prob, ga_params_file, param_file) = eval('{}'.format(params))
    random.seed(seed)
    global ga_params
    ga_params = ga_utils.create_parameters(ga_params_file)

    creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
    creator.create("Individual", list, fitness=creator.FitnessMin)
    toolbox = base.Toolbox()
    toolbox.register("individual", tools.initIterate, creator.Individual,
                     make_random_params)

    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("evaluate", obj_func)
    toolbox.register("mate", cxUniform, indpb=0.5)
    mutate_indpb = mut_prob
    toolbox.register("mutate", custom_mutate, indpb=mutate_indpb)
    toolbox.register("select", tools.selTournament, tournsize=3)
    toolbox.register("map", queue_map)

    pop = toolbox.population(n=num_pop)
    if param_file != "":
        update_init_pop(pop, param_file)

    hof = tools.HallOfFame(1)
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", np.mean)
    stats.register("std", np.std)
    stats.register("min", np.min)
    stats.register("max", np.max)
    stats.register("ts", timestamp)

    # num_iter-1 generations since the initial population is evaluated once first
    mutpb = mut_prob
    start_time = time.time()
    if strategy == 'simple':
        pop, log = algorithms.eaSimple(pop, toolbox, cxpb=0.5, mutpb=mutpb, ngen=num_iter - 1,
                                   stats=stats, halloffame=hof, verbose=True)
    elif strategy == 'mu_plus_lambda':
        mu = int(math.floor(float(num_pop) * 0.5))
        lam = int(math.floor(float(num_pop) * 0.5))
        if mu + lam < num_pop:
            mu += num_pop - (mu + lam)

        pop, log = algorithms.eaMuPlusLambda(pop, toolbox, mu=mu, lambda_=lam,
                                             cxpb=0.5, mutpb=mutpb, ngen=num_iter - 1,
                                             stats=stats, halloffame=hof, verbose=True)
    else:
        raise NameError('invalid strategy: {}'.format(strategy))

    end_time = time.time()

    fitnesses = [str(p.fitness.values[0]) for p in pop]

    eqpy.OUT_put("DONE")
    # return the final population
    eqpy.OUT_put("{}\n{}\n{}\n{}\n{}".format(create_list_of_json_strings(pop), ';'.join(fitnesses),
        start_time, log, end_time))
