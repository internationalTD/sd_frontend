import math
import os
import urllib.parse
import urllib.request
import json
from io import BytesIO
from PyQt5.Qt import QByteArray
import base64
import copy

from krita import *
from .defs import *
from .utils import *

#ui_priority_config = QSettings(QSettings.IniFormat, QSettings.UserScope, "krita", "sd_frontend_ui")
config = QSettings(QSettings.IniFormat, QSettings.UserScope, "krita", "sd_frontend_ui")


samplers = ["Euler a", "Euler", 'LMS', 'Heun', 'DPM2', 'DPM2 a', 'DDIM', 'PLMS']
samplers_img2img = ["Euler a", "Euler", 'LMS', 'Heun', 'DPM2', 'DPM2 a', 'DDIM']

parameter_widgetinfo = {}

parameter_widgetinfo["prompt"] = {
    "inputtype" : "prompt",
    "default" : "a cute dog"}

parameter_widgetinfo["negative_prompt"] = {
    "inputtype" : "prompt",
    "default" : "evil"}    

parameter_widgetinfo["steps"] = {
    "inputtype" : "QSpinBox",
    "default" : 20,
    "range" : [1, 512, 1]
    }

parameter_widgetinfo["sampler"] = {
    "inputtype" : "QComboBox",
    "default" : "Euler a",
    "ComboBoxOptions" : samplers
    }

parameter_widgetinfo["restore_faces"] = {
    "inputtype" : "QCheckBox",
    "default" : False
    }

parameter_widgetinfo["tiling"] = { 
    "inputtype" : "QCheckBox",  
    "default" : False
    }

parameter_widgetinfo["batch_count"] = {
    "inputtype" : "QSpinBox",
    "default" : 1,
    "range" : [1,64, 1]
    }

parameter_widgetinfo["batch_size"] = {    
    "inputtype" : "QSpinBox",
    "default" : 1,
    "range" : [1,64, 1]
    }

parameter_widgetinfo["cfg_scale"] = {
    "inputtype" : "QDoubleSpinBox",
    "default" : 7,
    "range" : [-64,64, 0.5]
    }
    
parameter_widgetinfo["seed"] = {
    "inputtype" : "seed",
    "default" : -1
    }
parameter_widgetinfo["subseed"] = {
    "inputtype" : "seed",
    "default" : -1
    }
parameter_widgetinfo["subseed_strength"] = {
    "inputtype" : "QDoubleSpinBox",
    "default" : 0,
    "range" : [0, 1, 0.05]
    }
parameter_widgetinfo["seed_resize_from_h"] = {
    "inputtype" : "QSpinBox",
    "default" : 0,
    "range" : [0, 1024, 64]
    }
parameter_widgetinfo["seed_resize_from_w"] = {
    "inputtype" : "QSpinBox",
    "default" : 0,
    "range" : [0, 1024, 64]
    }
#parameter_widgetinfo["!img_height"] = {
#parameter_widgetinfo["!img_width"] = {

parameter_widgetinfo["highres_fix"] = {
    "inputtype" : "QCheckBox",
    "default" : False
    }
parameter_widgetinfo["highres_fix_scale_latent"] = {
    "inputtype" : "QCheckBox",
    "default" : False
    }

parameter_widgetinfo["highres_fix_noise_scale"] = {
    "inputtype" : "QDoubleSpinBox",
    "default" : 0.7,
    "range" : [0, 1, 0.01]
    }

parameter_widgetinfo["denoising_strength"] = {
    "inputtype" : "QDoubleSpinBox",
    "default" : 0.75,
    "range" : [0, 1, 0.01]
    }
parameter_widgetinfo["mask_blur"] = {
    "inputtype" : "QSpinBox",
    "default" : 4,
    "range" : [0,512,1]
    }
parameter_widgetinfo["masked_content"] = {
    "inputtype" : "QComboBox",
    "default" : "fill",
    "ComboBoxOptions" : ["fill", "original", "latent noise", "latent nothing"]
    }

parameter_widgetinfo["inpaint_at_full_res"] = {
    "inputtype" : "QCheckBox",
    "default" : False
    }

#outpainting mk2:
parameter_widgetinfo["outpainting_pixels_to_expand"] = { 
    "inputtype" : "QSpinBox",
    "default" : 8,
    "range" : [8,128,8]
    }

parameter_widgetinfo["outpainting_mask_blur"] = {
    "inputtype" : "QSpinBox",
    "default" : 4,
    "range" : [0,64,1]
    }

parameter_widgetinfo["outpainting_directions"] = { 
    "inputtype" : "outpainting_directions",
    "default" : ["left","right","up","down"],
    }

parameter_widgetinfo["outpainting_falloff_exponent"] = { 
    "inputtype" : "QDoubleSpinBox",
    "default" : 1,
    "range" : [0,4,0.01]
    }

parameter_widgetinfo["outpainting_color_variation"] = {
    "inputtype" : "QDoubleSpinBox",
    "default" : 0.05,
    "range" : [0,1,0.01]
    }

#SD Upscale:
parameter_widgetinfo["upscale_tile_overlap"] = {
    "inputtype" : "QSpinBox",
    "default" : 64,
    "range" : [16,256,16],
    #"map_function" : str
}

parameter_widgetinfo["upscaler"] = {
    "inputtype" :"QComboBox",
    #Combobox default is first item for now
    "ComboBoxOptions" : ["Lanczos", "None", "Real-ESRGAN 4x plus", "Real-ESRGAN 4x plus anime 6B", "LDSR"]
}

#parameter_widgetinfo["!Script"    

