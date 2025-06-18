import logging
from typing import Literal

# Initialize the logger
logger = logging.getLogger(__name__)

STATION_TYPE = Literal['ZENTRA', 'ONSET', 'DAVIS', 'RAINWISE', 'SPECTRUM', 'LOCOMOS', 'LICOR', None]
STATION_TYPE_LIST =   ['ZENTRA', 'ONSET', 'DAVIS', 'RAINWISE', 'SPECTRUM', 'LOCOMOS', 'LICOR']

from .davis_api import DavisAPI, DavisAPIConfig
from .locomos_api import LocomosAPI, LocomosAPIConfig
from .onset_api import OnsetAPI, OnsetAPIConfig
from .rainwise_api import RainwiseAPI, RainwiseAPIConfig
from .spectrum_api import SpectrumAPI, SpectrumAPIConfig
from .zentra_api import ZentraAPI, ZentraAPIConfig
from .licor_api import LicorAPI, LicorAPIConfig

API_CLASS_TYPES = {'DAVIS': DavisAPI,
                   'LOCOMOS':LocomosAPI, 
                   'ONSET': OnsetAPI,
                   'RAINWISE': RainwiseAPI, 
                   'SPECTRUM':SpectrumAPI, 
                   'ZENTRA': ZentraAPI,
                   'LICOR': LicorAPI
                   }

CONFIG_CLASS_TYPES = {'DAVIS': DavisAPIConfig,
                      'LOCOMOS':LocomosAPIConfig, 
                      'ONSET': OnsetAPIConfig,
                      'RAINWISE': RainwiseAPIConfig,
                      'SPECTRUM':SpectrumAPIConfig,
                      'ZENTRA':ZentraAPIConfig,
                      'LICOR':LicorAPIConfig
                      }

