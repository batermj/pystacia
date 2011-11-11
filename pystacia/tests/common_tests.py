from __future__ import with_statement

from pystacia.tests import TestCase


class StateTest(TestCase):
    def setUp(self):
        self.stateful = Stateful()
    
    def test_empty(self):
        stateful = self.stateful
        state_ = stateful.state.copy()
        
        with state(stateful):
            self.assertEquals(state_, stateful.state)
            
        self.assertEquals(state_, stateful.state)
            
    def test_one(self):
        stateful = self.stateful
        stateful.state['a'] = 1
        state_ = stateful.state.copy()
        
        with state(stateful, b=3):
            self.assertEquals(stateful.state, {'a': 1, 'b': 3, 'c': None})
            
        self.assertEquals(state_, stateful.state)
        
    def test_nested(self):
        stateful = self.stateful
        stateful.state['b'] = 4
        state_ = stateful.state.copy()
        
        with state(stateful, a=1, c=2):
            self.assertEquals(stateful.state, {'a': 1, 'b': 4, 'c': 2})
            with state(stateful, a=0, b=0):
                self.assertEquals(stateful.state, {'a': 0, 'b': 0, 'c': 2})
            self.assertEquals(stateful.state, {'a': 1, 'b': 4, 'c': 2})
            
        self.assertEquals(state_, stateful.state)
        
    def test_exception(self):
        stateful = self.stateful
        stateful.state['b'] = 4
        state_ = stateful.state.copy()
        
        try:
            with state(stateful, a=0):
                self.assertEquals(stateful.state['a'], 0)
                
                raise PystaciaException('dummy')
        except PystaciaException:
            self.assertEquals(stateful.state, state_)


class Stateful(object):
    def __init__(self):
        self.state = {'a': None, 'b': None, 'c': None}
        
    def _set_state(self, k, v):
        self.state[k] = v
        
    def _get_state(self, k):
        return self.state[k]


class ResourceTest(TestCase):
    def setUp(self):
        self._store_registry = common._registry
        common._registry = self._store_registry.__class__()
    
    def tearDown(self):
        common._registry = self._store_registry
    
    def test_tracking(self):
        self.assertEquals(len(common._registry), 0)
        
        mock1 = Mock()
        
        self.assertEquals(len(common._registry), 1)
        
        mock1.close()
        
        self.assertEquals(len(common._registry), 0)
        
        mock1 = Mock()
        mock2 = Mock()
        
        self.assertEquals(len(common._registry), 2)
        
        mock1.close()
        
        self.assertEquals(len(common._registry), 1)
        
        mock2._claim()
        
        self.assertEquals(len(common._registry), 0)
        
    def test_called(self):
        mock1 = Mock()
        
        self.assertTrue(mock1.alloc_called)
        self.assertFalse(mock1.free_called)
        
        mock1.close()
        
        self.assertTrue(mock1.free_called)
        
        self.assertEquals(len(common._registry), 0)
        
        mock2 = Mock(34)
        
        self.assertFalse(mock2.alloc_called)
        self.assertFalse(mock2.free_called)
        
        mock3 = Mock(45)
        
        self.assertFalse(mock3.alloc_called)
        self.assertFalse(mock2.free_called)
        
        self.assertEquals(len(common._registry), 2)
        
        mock2.close()
        
        self.assertTrue(mock2.free_called)
        
        mock3._claim()
        
        self.assertFalse(mock3.free_called)
        
        self.assertEquals(len(common._registry), 0)
        
    def test_resource(self):
        mock1 = Mock()
        mock2 = Mock(0)
        
        self.assertEquals(mock1.resource, 42)
        self.assertEquals(mock2.resource, 0)
        
        mock2.close()
        
        self.assertRaisesRegexp(PystaciaException, 'closed',
                                lambda: mock2.resource)
        
        resource = mock1._claim()
        self.assertEquals(resource, 42)
        
        self.assertRaisesRegexp(PystaciaException, 'closed',
                                lambda:  mock1.resource)
        
        self.assertEquals(len(common._registry), 0)
        
    def test_copy(self):
        mock = Mock(3)
        
        copy1 = mock.copy()
        copy2 = mock.copy()
        
        self.assertEquals(mock.copy_count, 2)
        
        self.assertEquals(mock.resource, copy1.resource)
        self.assertEquals(copy2.resource, copy1.resource)
        
        self.assertEquals(len(common._registry), 3)
        
        mock.close()
        
        self.assertRaisesRegexp(PystaciaException, 'closed',
                                lambda: mock.copy())
        
        self.assertEquals(copy2.resource, copy1.resource)
        
        copy1.close()
        self.assertEquals(copy2._claim(), 3)
        
        self.assertEquals(len(common._registry), 0)
    
    def test_badmock(self):
        self.assertRaisesRegexp(PystaciaException, '_alloc',
                                lambda: BadMock())
        
        mock = BadMock(11)
        
        self.assertRaisesRegexp(PystaciaException, '_clone',
                                lambda: mock.copy())

from pystacia.common import Resource


class Mock(Resource):
    def __init__(self, resource=None):
        self.alloc_called = False
        self.free_called = False
        self.copy_count = 0
        
        super(Mock, self).__init__(resource)
    
    def _alloc(self):
        self.alloc_called = True
        
        return 42
        
    def _free(self):
        self.free_called = True
        
    def _clone(self):
        self.copy_count += 1
        
        return self.resource


class BadMock(Mock):
    def _alloc(self):
        pass
    
    def _clone(self):
        pass


from pystacia import common
from pystacia.common import state
from pystacia.util import PystaciaException
