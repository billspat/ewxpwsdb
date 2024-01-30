from typing import Literal

# STATION_TYPE = Literal['ZENTRA', 'ONSET', 'DAVIS', 'RAINWISE', 'SPECTRUM', 'LOCOMOS', 'GENERIC'] 
STATION_TYPE_LIST =   ['ZENTRA', 'ONSET', 'DAVIS', 'RAINWISE', 'SPECTRUM', 'LOCOMOS', 'GENERIC']

# from .weather_station import WeatherStation  
from .davis import DavisStation, DavisConfig
from .locomos import LocomosStation, LocomosConfig
from .rainwise import RainwiseStation, RainwiseConfig
from .spectrum import SpectrumStation, SpectrumConfig
from .onset import OnsetStation, OnsetConfig
from .zentra import ZentraStation, ZentraConfig

STATION_CLASS_TYPES = {'ZENTRA': ZentraStation, 'ONSET': OnsetStation, 'DAVIS': DavisStation,'RAINWISE': RainwiseStation, 'SPECTRUM':SpectrumStation, 'LOCOMOS':LocomosStation }
CONFIG_CLASS_TYPES = {'ZENTRA': ZentraConfig, 'ONSET': OnsetConfig, 'DAVIS': DavisConfig,'RAINWISE': RainwiseConfig, 'SPECTRUM':SpectrumConfig, 'LOCOMOS':LocomosConfig }
