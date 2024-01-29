import pytest

def pytest_addoption(parser):

    parser.addoption('--dburl',
                     action='store',
                     default='sqlite:///test-ewxpws.db',
                     help='sqlalchemy db url for test.  If sqlite, is created and then deleted on completion')
