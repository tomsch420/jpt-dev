import pandas as pd
import pyximport
from dnutils.stats import print_stopwatches

pyximport.install()

import os
import pickle

import numpy as np
from numpy import iterable

from dnutils import out
from jpt.learning.distributions import Bool, Numeric, HistogramType, SymbolicType
from intervals import ContinuousSet as Interval
from jpt.learning.trees import JPT
from jpt.variables import Variable, SymbolicVariable, NumericVariable
from quantiles import Quantiles


class Conditional:

    def __init__(self, typ, conditionals):
        self.type = typ
        self.conditionals = conditionals
        self.p = {}

    def __getitem__(self, values):
        if not iterable(values):
            values = (values,)
        return self.p[tuple(values)]

    def __setitem__(self, evidence, dist):
        if not iterable(evidence):
            evidence = (evidence,)
        self.p[evidence] = dist

    def sample(self, evidence, n):
        if not iterable(evidence):
            evidence = (evidence,)
        return self.p[tuple(evidence)].sample(n)

    def sample_one(self, evidence):
        if not iterable(evidence):
            evidence = (evidence,)
        return self.p[tuple(evidence)].sample_one()


def restaurant():
    # declare variable types
    PatronsType = SymbolicType('Patrons', ['3', '10', '20'])
    PriceType = SymbolicType('Price', ['$', '$$', '$$$'])
    FoodType = SymbolicType('Food', ['French', 'Thai', 'Burger', 'Italian'])
    WaitEstType = SymbolicType('WaitEstimate', ['10', '30', '60', '120'])

    # define probs
    al = SymbolicVariable('Alternatives', Bool)  # Alternatives(.2)
    ba = SymbolicVariable('Bar', Bool)  # Bar(.2)
    fr = SymbolicVariable('Friday', Bool)  # Friday(1/7.)
    hu = SymbolicVariable('Hungry', Bool)  # Hungry(.8)
    pa = SymbolicVariable('Patrons', PatronsType)  # PatronsType([.2, .6, .2])
    pr = SymbolicVariable('Price', PriceType)  # Price([.1, .7, .2])
    ra = SymbolicVariable('Rain', Bool)  # Rain(.3)
    re = SymbolicVariable('Reservation', Bool)  # Reservation(.1)
    fo = SymbolicVariable('Food', FoodType)  # Food([.1, .2, .4, .3])
    wa = SymbolicVariable('WaitEst', WaitEstType)  # WaitEst([.3, .4, .2, .1])

    numsamples = 500
    # variables = [ba, ra, re]
    variables = [al, ba, fr, hu, pa, pr, ra, re, fo, wa]

    # data = [[ba.dist(.2).sample_one(), ra.dist(.3).sample_one(), re.dist(.2).sample_one()] for _ in range(numsamples)]

    data = [[al.dist(.2).sample_one_label(),
             ba.dist(.2).sample_one_label(),
             fr.dist(1/7.).sample_one_label(),
             hu.dist(.8).sample_one_label(),
             pa.dist([.2, .6, .2]).sample_one_label(),
             pr.dist([.1, .7, .2]).sample_one_label(),
             ra.dist(.3).sample_one_label(),
             re.dist(.1).sample_one_label(),
             fo.dist([.1, .2, .4, .3]).sample_one_label(),
             wa.dist([.3, .4, .2, .1]).sample_one_label()] for _ in range(numsamples)]

    jpt = JPT(variables, name='Restaurant', min_samples_leaf=30, min_impurity_improvement=0)
    jpt.learn(data)
    out(jpt)
    jpt.plot(plotvars=variables, view=True)
    # candidates = jpt.apply({ba: True, re: False})
    q = {ba: True, re: False}
    e = {ra: False}
    res = jpt.infer(q, e)
    out(f'P({",".join([f"{k.name}={v}" for k, v in q.items()])}{" | " if e else ""}'
        f'{",".join([f"{k.name}={v}" for k, v in e.items()])}) = {res.result}')
    print(res.explain())


def alarm():

    E = SymbolicVariable('Earthquake', Bool)  # .02
    B = SymbolicVariable('Burglary', Bool)  # Bool(.01)
    A = SymbolicVariable('Alarm', Bool)
    M = SymbolicVariable('MaryCalls', Bool)
    J = SymbolicVariable('JohnCalls', Bool)

    A_ = Conditional(Bool, [E.domain, B.domain])
    A_[True, True] = Bool(.95)
    A_[True, False] = Bool(.94)
    A_[False, True] = Bool(.29)
    A_[False, False] = Bool(.001)

    M_ = Conditional(Bool, [A])
    M_[True] = Bool(.7)
    M_[False] = Bool(.01)

    J_ = Conditional(Bool, [A])
    J_[True] = Bool(.9)
    J_[False] = Bool(.05)

    c = 0.
    t = 1
    for i in range(t):

        # Construct the CSV for learning
        data = []
        for i in range(1000):
            e = E.dist(.2).sample_one()
            b = B.dist(.1).sample_one()
            a = A_.sample_one([e, b])
            m = M_.sample_one(a)
            j = J_.sample_one(a)

            data.append([e, b, a, m, j])

        # sample check
        out('Probabilities as determined by sampled data')
        d = np.array(data).T
        for var, x in zip([E, B, A, M, J], d):
            unique, counts = np.unique(x, return_counts=True)
            out(var.name, list(zip(unique, counts, counts/sum(counts))))

        tree = JPT(variables=[E, B, A, M, J], name='Alarm', min_impurity_improvement=0)
        tree.learn(data)
        tree.sklearn_tree()
        # tree.plot(plotvars=[E, B, A, M, J])
        # conditional
        # q = {A: True}
        # e = {E: False, B: True}

        # joint
        # q = {A: True, E: False, B: True}
        # e = {}

        # diagnostic
        q = {A: True}
        e = {M: True}

        c += tree.infer(q, e).result

    # tree = JPT(variables=[E, B, A, M, J], name='Alarm', min_impurity_improvement=0)
    # tree.learn(data)
    # out(tree)
    res = tree.infer(q, e)
    res.explain()

    print_stopwatches()
    print('AVG', c/t)
    # tree.plot(plotvars=[E, B, A, M, J])


def test_merge():
    X = HistogramType('YesNo', ['Y', 'N'])
    mn1 = X([20, 30])
    out('MN1', mn1, mn1.p, mn1.d)

    mn2 = X([10, 12])
    out('MN2', mn2, mn2.p, mn2.d)

    mnmerged = X([30, 42])
    out('MNMERGED', mnmerged, mnmerged.p, mnmerged.d)

    mn3 = mn1 + mn2
    out('MN3 as merge of MN1 and MN2', mn3, mn3.p, mn3.d, mn3==mnmerged)

    mn2 += mn1
    out('MN2 after adding MN1', mn2, mn2.p, mn2.d, mn2 == mnmerged)


def test_dists():
    a = Bool()  # initialize empty then set data
    a.set_data([True, False, False, False, False, False, False, False, False, False])
    b = Bool([1, 9])  # set counts
    c = Bool(.1)  # set probability
    d = Bool([.1, .9])  # set both probabilities; not supposed to be used like that
    out(a)
    out(b)
    out(c)
    out(d)
    out(a == b, c == d)

    # prettyprinting tests for str und repr
    FoodType = HistogramType('Food', ['French', 'Thai', 'Burger', 'Italian'])
    fo = Variable('Food', FoodType)
    dist = fo.dist([.1, .1, .1, .7])

    # should print without probs
    out('\n')
    print(dist)
    print(repr(dist))

    # should print with probs
    out('\n')
    print(a)
    print(repr(a))
    print(repr(fo.dist()))
    print(repr(Bool()))


def test_muesli():
    f = os.path.join('../' 'examples', 'data', 'human_muesli.pkl')

    data = []
    with open(f, 'rb') as fi:
        data = np.array(pickle.load(fi))
    data_ = np.array(sorted([float(x) for x in data.T[0]]))

    quantiles = Quantiles(data_, epsilon=.0001)
    cdf_ = quantiles.cdf()
    d = Numeric(cdf=cdf_)

    interval = Interval(-2.05, -2.0)
    p = d.p(interval)
    out('query', interval, p)

    print(d.cdf.pfmt())
    d.plot(name='Müsli Beispiel', view=True)


def muesli_tree():
    # f = os.path.join('../' 'examples', 'data', 'human_muesli.pkl')

    data = []
    # with open(f, 'rb') as fi:
    #     data = pickle.load(fi)
    data = pd.read_pickle('../examples/data/human_muesli.dat')
    # unique, counts = np.unique(data[2], return_counts=True)
    print(data)
    ObjectType = SymbolicType('ObjectType', data['Class'].unique())

    x = NumericVariable('X', Numeric)
    y = NumericVariable('Y', Numeric)
    o = SymbolicVariable('Object', ObjectType)

    jpt = JPT([x, y, o], name="Müslitree", min_samples_leaf=5)
    jpt.learn(columns=data.values.T)

    for clazz in data['Class'].unique():
        print(jpt.infer(query={o: clazz}, evidence={x: .9, y: [None, .45]}))


    # plotting vars does not really make sense here as all leaf-cdfs of numeric vars are only piecewise linear fcts
    # --> only for testing
    jpt.plot(plotvars=[x, y, o])


def picklemuesli():
    f = os.path.join('../' 'examples', 'data', 'human_muesli.pkl')

    data = []
    with open(f, 'rb') as fi:
        data = np.array(pickle.load(fi))

    transformed = []
    for c in data.T:
        try:
            transformed.append(np.array(c, dtype=float))
        except:
            transformed.append(np.array(c))

    with open(f, 'wb+') as fi:
        pickle.dump(transformed, fi)





def main(*args):

    # test_merge()
    # test_dists()
    # restaurant()  # for bools and strings
    # test_muesli()
    muesli_tree()  # for numerics and strings
    # picklemuesli()
    # alarm()  # for bools


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main('PyCharm')
