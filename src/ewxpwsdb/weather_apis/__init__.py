from typing import Literal

STATION_TYPE = Literal['ZENTRA', 'ONSET', 'DAVIS', 'RAINWISE', 'SPECTRUM', 'LOCOMOS', 'GENERIC'] 
STATION_TYPE_LIST =   ['ZENTRA', 'ONSET', 'DAVIS', 'RAINWISE', 'SPECTRUM', 'LOCOMOS', 'GENERIC']

from .davis_api import DavisAPI, DavisAPIConfig
from .locomos_api import LocomosAPI, LocomosAPIConfig
from .onset_api import OnsetAPI, OnsetAPIConfig
from .rainwise_api import RainwiseAPI, RainwiseAPIConfig
from .spectrum_api import SpectrumAPI, SpectrumAPIConfig
from .zentra_api import ZentraAPI, ZentraAPIConfig

API_CLASS_TYPES = {'DAVIS': DavisAPI,
                   'LOCOMOS':LocomosAPI, 
                   'ONSET': OnsetAPI,
                   'RAINWISE': RainwiseAPI, 
                   'SPECTRUM':SpectrumAPI, 
                   'ZENTRA': ZentraAPI
                   }

CONFIG_CLASS_TYPES = {'DAVIS': DavisAPIConfig,
                      'LOCOMOS':LocomosAPIConfig, 
                      'ONSET': OnsetAPIConfig,
                      'RAINWISE': RainwiseAPIConfig,
                      'SPECTRUM':SpectrumAPIConfig,
                      'ZENTRA':ZentraAPIConfig
                      }
