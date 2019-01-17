from consumer import *

def test_shc():
    shc = ServiceHostCollection(PROD='localhost')
    assert shc is not None

def test_shcw():
    pass
