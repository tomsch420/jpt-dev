import unittest
import numpy as np
import jpt.variables
from jpt.sequential_jpt import SequentialJPT

class UniformSeries:

    def __init__(self, basis_function=np.sin, epsilon=0.05):
        self.epsilon = 0.05
        self.basis_function = basis_function

    def sample(self, samples) -> np.array:
        samples = self.basis_function(samples)
        samples = samples + np.random.uniform(-self.epsilon, self.epsilon, samples.shape)
        return samples


class SequenceTest(unittest.TestCase):

    def setUp(self) -> None:
        self.g = UniformSeries()
        self.data = np.expand_dims(self.g.sample(np.arange(np.pi / 2, 10000, np.pi)), -1)
        self.variables = [jpt.variables.NumericVariable("X", precision=0.1)]

    def test_learning(self):
        tree = SequentialJPT(self.variables, min_samples_leaf=3000)
        tree.learn([self.data, self.data])


    def test_integral(self):
        tree = SequentialJPT(self.variables, min_samples_leaf=1500)
        tree.learn([self.data])
        tree.plot(plotvars=tree.variables)
        print(sum([leaf.prior*leaf.prior for leaf in tree.template_tree.leaves.values()]))
        self.assertAlmostEqual(tree.probability_mass_, 0.5)



if __name__ == '__main__':
    unittest.main()
