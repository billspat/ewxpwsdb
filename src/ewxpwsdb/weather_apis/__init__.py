from typing import Literal

STATION_TYPE = Literal['ZENTRA', 'ONSET', 'DAVIS', 'RAINWISE', 'SPECTRUM', 'LOCOMOS', 'GENERIC'] 
STATION_TYPE_LIST =   ['ZENTRA', 'ONSET', 'DAVIS', 'RAINWISE', 'SPECTRUM', 'LOCOMOS', 'GENERIC']

# # from .weather_api import WeatherAPI, WeatherAPIConfig

from .davis_api import DavisAPI, DavisAPIConfig
from .spectrum_api import SpectrumAPI, SpectrumAPIConfig
from .zentra_api import ZentraAPI, ZentraAPIConfig
from .onset_api import OnsetAPI, OnsetAPIConfig
from .rainwise_api import RainwiseAPI, RainwiseAPIConfig

API_CLASS_TYPES = {'DAVIS': DavisAPI, 
                   'ONSET': OnsetAPI,
                   'RAINWISE': RainwiseAPI, 
                   'SPECTRUM':SpectrumAPI, 
                   'ZENTRA': ZentraAPI }

CONFIG_CLASS_TYPES = {'DAVIS': DavisAPIConfig, 
                      'ONSET': OnsetAPIConfig,
                      'RAINWISE': RainwiseAPIConfig,
                      'SPECTRUM':SpectrumAPIConfig,
                      'ZENTRA':ZentraAPIConfig}


# # waiting to be re-factored
# # from .locomos import LocomosAPI, LocomosAPIConfig
# # STATION_CLASS_TYPES = {'ZENTRA': ZentraAPI, 'ONSET': OnsetAPI, 'DAVIS': DavisAPI,'RAINWISE': RainwiseAPI, 'SPECTRUM':SpectrumAPI, 'LOCOMOS':LocomosAPI }
# # CONFIG_CLASS_TYPES = {'ZENTRA': ZentraAPIConfig, 'ONSET': OnsetAPIConfig, 'DAVIS': DavisAPIConfig,'RAINWISE': RainwiseAPIConfig, 'SPECTRUM':SpectrumAPIConfig, 'LOCOMOS':LocomosAPIConfig }
