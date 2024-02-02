from typing import Literal

STATION_TYPE = Literal['ZENTRA', 'ONSET', 'DAVIS', 'RAINWISE', 'SPECTRUM', 'LOCOMOS', 'GENERIC'] 
STATION_TYPE_LIST =   ['ZENTRA', 'ONSET', 'DAVIS', 'RAINWISE', 'SPECTRUM', 'LOCOMOS', 'GENERIC']

# # from .weather_api import WeatherAPI, WeatherAPIConfig

from .davis_api import DavisAPI, DavisAPIConfig
from .spectrum_api import SpectrumAPI, SpectrumAPIConfig
from .zentra_api import ZentraAPI, ZentraAPIConfig

API_CLASS_TYPES = {'DAVIS': DavisAPI,'SPECTRUM':SpectrumAPI, 'ZENTRA': ZentraAPI }
CONFIG_CLASS_TYPES = {'DAVIS': DavisAPIConfig, 'SPECTRUM':SpectrumAPIConfig, 'ZENTRA':ZentraAPIConfig}


# # waiting to be re-factored
# # from .locomos import LocomosAPI, LocomosAPIConfig
# # from .rainwise import RainwiseAPI, RainwiseAPIConfig
# # from .onset import OnsetAPI, OnsetAPIConfig
# # from .zentra import ZentraAPI, ZentraAPIConfig
# # STATION_CLASS_TYPES = {'ZENTRA': ZentraAPI, 'ONSET': OnsetAPI, 'DAVIS': DavisAPI,'RAINWISE': RainwiseAPI, 'SPECTRUM':SpectrumAPI, 'LOCOMOS':LocomosAPI }
# # CONFIG_CLASS_TYPES = {'ZENTRA': ZentraAPIConfig, 'ONSET': OnsetAPIConfig, 'DAVIS': DavisAPIConfig,'RAINWISE': RainwiseAPIConfig, 'SPECTRUM':SpectrumAPIConfig, 'LOCOMOS':LocomosAPIConfig }
