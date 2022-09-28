import math
import os
import urllib.parse
import urllib.request
import json
import base64
import string
import random

from krita import *

def nonsense():  #for marking json values as unchangeable (won't be displayed in the gui)
    letters = string.ascii_lowercase
    result_str = '!nonsense'+ ''.join(random.choice(letters) for i in range(3))
    return result_str

fn_indices = {"txt2img" : 11, "img2img" : 30, "inpaint" : 30, "Outpainting mk2" : 30, "SD Upscale" : 30}

"""
TODO: Change this so that key == API var name, key mode a == key mode b, key has no !
       change the UI loader into expecting a value that is a dict with instructions for what to spawn, what the limits are, etc
            ex.: {"widget":"ComboBox", "values" : ["A" , "b" , "C!"], "special" : None }
                 {"widget":None, "values" : ["A" , "b" , "C!"], "special" : "img_height" }
"""

defaults = {}
ui_tags = {} 

"""
    "a cute dog", "evil", "None", "None", 
    20, "Euler a", False, False, 
    1, 1, 
    7, 
    -1, -1, 0, 0, 0, 
    False, 512, 512, 
    False, False, 0.7, 
    "None", 
    False, None, "", False, "Seed", "", "Steps", "", True, None, "", ""
    ]
"""    
defaults["txt2img"] = [
    "a cute dog","evil","None","None",
    20,"Euler a",False,False,
    1,1,
    7,
    -1,1221, 0, 512, 512,
    True, 576,448,
    True,True,0.66,
    "None",
    False, None, "", False, "Seed", "", "Steps", "", True, False, None, "", ""]


ui_tags["txt2img"] = [
    "prompt", "negative_prompt", None, None, 
    "steps", "sampler", "restore_faces", "tiling", 
    "batch_count", "batch_size", 
    "cfg_scale", 
    "seed", "subseed", "subseed_strength", "seed_resize_from_h", "seed_resize_from_w",
    None, "!img_height", "!img_width",
    "highres_fix", "highres_fix_scale_latent", "highres_fix_noise_scale",
    None,
    None, None, None, None, None, None, None, None, None, None, None, None, None
    ]

### img2img:

"""
    "a cute dog", "evil", "None", "None",
    "img here",None,None,"Draw mask",
    20,"Euler a",4,"fill",False,False,"Redraw whole image",1,1,
    7,0.75,
    -1,-1,0,
    0,0,True,
    512,512,
    "Just resize","None",64,False,"Inpaint masked","None","","","","",1,50,0,4,1,"Nonsense",8,4,["left","right","up","down"],1,0.05,8,4,"fill",["left","right","up","down"],False,None,"",False,"Seed","","Steps","",True,None,"",""
    ]

"""

defaults["img2img"] = [
    0, "a cute dog", "evil", "None", "None",
    "IMAGE GOES HERE",None,None,None,"Draw mask",
    20, "Euler a", 4, "fill", False, False, 1, 1, 
    7, 0.75,
    -1, -1, 0,
    576, 640, True,
    640, 576,
    "Just resize", False, 32, "Inpaint masked","","","None","","",1,50,0, False,4,1,"Nonsense",128,8,["left","right","up","down"],1,0.05,128,4,"fill",["left","right","up","down"],False,None,"",False,"Nonsense",64,"None","Seed","","Steps","",True,False,None,"",""
   ]

ui_tags["img2img"] = [
    None, "prompt", "negative_prompt", None, None,
    "!img_in", None, None, None, None,
    "steps", "sampler", None, None, "restore_faces", "tiling", "batch_count", "batch_size",
    "cfg_scale", "denoising_strength",
    "seed", "subseed", "subseed_strength",
    "seed_resize_from_w", "seed_resize_from_h", None,
    "!img_height", "!img_width",
    None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]


#inpaint:

defaults["inpaint"] = [
    1, "a cute dog", "evil", "None", "None",
    None, None, "IMG HERE", "MASK HERE", "Upload mask",
    20, "Euler a", 4, "fill", False, False, 1, 1,
    7, 0.75,
    4321, 1234, 0,
    1024, 2048, True,
    448, 384,
    "Just resize", False, 32, "Inpaint masked", "", "", "None", "", "", 1, 50, 0, False, 4, 1, "<p style=\"margin-bottom:0.75em\">Recommended settings: Sampling Steps: 80-100,  Sampler: Euler a,  Denoising strength: 0.8</p>", 128, 8, ["left", "right", "up", "down"], 1, 0.05, 128, 4, "fill", ["left", "right", "up", "down"], False, None, "", False, "<p style=\"margin-bottom:0.75em\">Will upscale the image to twice the dimensions; use width and height sliders to set tile size</p>", 64, "None", "Seed", "", "Steps", "", True, False, None, "", ""
    ]

ui_tags["inpaint"] = [
    None, "prompt", "negative_prompt", None, None,
    None, None, "!img_in", "!mask_in", None,
    "steps", "sampler", "mask_blur", "masked_content", "restore_faces", "tiling", "batch_count", "batch_size",
    "cfg_scale", "denoising_strength", 
    "seed", "subseed", "subseed_strength",
    "seed_resize_from_w", "seed_resize_from_h", None,
    "!img_height", "!img_width",
    None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None
    ]

#Outpainting mk2:

defaults["Outpainting mk2"] = [
    0,"a cute dog","evil","None","None",
    "data:image/png;base64",None,None,None,"Draw mask",
    20, "Euler a", 4, "fill", False, False, 1, 1, 
    7, 0.75, 
    4321,1234,0.02,
    1024,2048,True,
    512,512,
    "Just resize", False, 32, "Inpaint masked", "", "", "Outpainting mk2", "", "", 1, 50, 0, False, 4, 1, "Nonsense",
    128, 8,
    ["left","right","up","down"],
    1.0, 0.05,
    128,4, "fill",["left","right","up","down"], False,None, "",False, "Nonsense",64, "None","Seed", "","Steps", "",True, False,None, "",""
    ]

ui_tags["Outpainting mk2"] = [
    None, "prompt", "negative_prompt", None, None,
    "!img_in", None, None, None, None,
    "steps", "sampler", "mask_blur", "masked_content", "restore_faces", "tiling", "batch_count", "batch_size",
    "cfg_scale", "denoising_strength",
    "seed", "subseed", "subseed_strength",
    "seed_resize_from_w", "seed_resize_from_h", None,
    "!img_height", "!img_width",
    None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None,
    "outpainting_pixels_to_expand", "outpainting_mask_blur", 
    "outpainting_directions",
    "outpainting_falloff_exponent", "outpainting_color_variation", 
    None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None
    ]

defaults["SD Upscale"] = [
    0, "a cute dog", "evil", "None", "None", 
    "data:image/png;",None,None,None,"Draw mask",
    20,"Euler a",4,"fill",False,False,1,1,
    7,0.75,
    4321,1234,0.03,
    1024,2048,True,
    512,512,
    "Just resize",False, 32,"Inpaint masked", "","", "SD upscale","", "",1, 50,0, False,4, 1,"<Nonsense", 128,8, ["left","right","up","down"],1, 0.05,128, 4,"fill", ["left","right","up","down"],False, None,"", False,"<Nonsense",
    64, "Lanczos", "Seed", "",
    "Steps","",True,False,None,"",""
    ]

ui_tags["SD Upscale"] = [
    None, "prompt", "negative_prompt", None, None,
    "!img_in", None, None, None, None,
    "steps", "sampler", None, None, "restore_faces", "tiling", "batch_count", "batch_size",
    "cfg_scale", "denoising_strength",
    "seed", "subseed", "subseed_strength",
    "seed_resize_from_w", "seed_resize_from_h", None,
    "!img_height", "!img_width",
    None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, 
    "upscale_tile_overlap", "upscaler", None, None,
    None, None, None, None, None, None, None
    ]
