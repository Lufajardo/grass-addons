
import unittest2 as unittest
#import unittest

from libagent import playground, anthill

class TestAnthill(unittest.TestCase):
    def setUp(self):
        self.pg = playground.Playground()
        self.pg.setregion(3,3)
        self.world = anthill.Anthill(self.pg)
        self.world.sites = [[1,1]]

    def test_addlayertopg(self):
        # gets tested in World
        pass

    def test_removelayerfrompg(self):
        # gets tested in World
        pass

    def test_getlayer(self):
        # gets tested in World
        pass

    def findposition(self):
        # gets tested in World
        pass

    def test_bear(self):
        agent = self.world.bear()
        self.assertIsInstance(agent, self.world.agenttype)
        self.assertIs(agent, self.world.agents.pop())
        self.assertEqual(0, len(self.world.agents))

    def test_move(self):
        # gets tested in World
        pass

    def test_getneighbourpositions(self):
        # gets tested in World
        pass

    def test_kill(self):
        # gets tested in World
        pass

    def test_letantsdance(self):
        # TODO: as sort of the mainloop, just let it run a few times?
        pass

    def test_getpheromone(self):
        self.assertNotEqual(9,
            self.world.playground.layers[anthill.Anthill.RESULT][0][0])
        self.world.playground.layers[anthill.Anthill.RESULT][0][0] = 9
        self.assertEqual(9, self.world.getpheromone([0,0]))

    def test_setpheromone(self):
        self.world.setpheromone([0,0], 5)
        self.assertNotEqual(4,
            self.world.playground.layers[anthill.Anthill.RESULT][0][0])
        self.world.setpheromone([0,0], 4)
        self.assertNotEqual(5,
            self.world.playground.layers[anthill.Anthill.RESULT][0][0])
        self.assertEqual(4,
            self.world.playground.layers[anthill.Anthill.RESULT][0][0])

    def volatilize(self):
        # gets tested in Playground, except for setting the values..
        pass

#    def tearDown(self):

