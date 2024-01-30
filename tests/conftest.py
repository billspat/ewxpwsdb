import pytest

def pytest_addoption(parser):

    parser.addoption('--dburl',
                     action='store',
                     default='sqlite:///test-ewxpws.db',
                     help='sqlalchemy db url for test.  If sqlite, is created and then deleted on completion')

    parser.addoption('--file',
                     action='store',
                     default='data/test_stations.tsv',
                     help='tsv file to use for test data')
    
    parser.addoption('--no-import',
                     action='store_true',
                     help='use this to skip importing data (assumes test db already has data)')
