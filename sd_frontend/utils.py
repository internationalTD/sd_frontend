import math
import os
import urllib.parse
import urllib.request
import json
from io import BytesIO
from PyQt5.Qt import QByteArray
import base64
import copy
import re

from krita import *
from .defs import *
from . import defs_ui
from . import config
DOCKER_ID = 'pykrita_sd_frontend'

CoolIcon = QIcon() #TODO lol

temp_alphabuffer = None
def toast(message):
    Krita.instance().activeWindow().activeView().showFloatingMessage("Stable Diffusion Frontend: "+message, CoolIcon, 2000, 1)

def toastError(message):
    Krita.instance().activeWindow().activeView().showFloatingMessage("Stable Diffusion Frontend: ERROR:\n"+message, CoolIcon, 12000, 0)

def insertValue(groupBox, value):
    for widget in groupBox.findChildren(QPlainTextEdit):
        widget.setPlainText(value)
    for widget in groupBox.findChildren(QSpinBox):
        widget.setValue(value)
    for widget in groupBox.findChildren(QDoubleSpinBox):
        widget.setValue(value)
    for widget in groupBox.findChildren(QComboBox):
        widget.setCurrentText(value)
    for widget in groupBox.findChildren(QCheckBox):
        widget.setCheckState(value)
    for widget in groupBox.findChildren(QLineEdit):
        widget.setText(str(value))


def extractValue(groupBox):
    widgetinfo = defs_ui.parameter_widgetinfo[groupBox.title()]
    for widget in groupBox.findChildren(QPlainTextEdit):
        return widget.toPlainText()
    for widget in groupBox.findChildren(QSpinBox):
        if "map_function" in widgetinfo.keys():
            map_fn = widgetinfo["map_function"]
            return map_fn(widget.value())
        else:
            return widget.value()
    for widget in groupBox.findChildren(QDoubleSpinBox):
        return widget.value()
    for widget in groupBox.findChildren(QComboBox):
        return widget.currentText()

    if len(groupBox.findChildren(QCheckBox)) > 1:  ##yeah yeah i dont wanna hear it, future me
        checklist = []
        for widget in groupBox.findChildren(QCheckBox):    
            if widget.isChecked():
                checklist.append(widget.text())
        return checklist
    else:
        for widget in groupBox.findChildren(QCheckBox):
            return widget.isChecked()

    for widget in groupBox.findChildren(QLineEdit):  ##TODO: refactor, especially this line. returning an int should really only be for seeds
        print("seed?")
        print(widget.text())
        print(int(widget.text()))
        return int(widget.text())

def getLayerinfo(node):
    
    if node.name().startswith("Copy of "):
        #print("fixing layer name")
        node.setName(node.name()[len("Copy of "):])

    return json.loads(node.name())

def fetchAndInsert(widget, key):
    d,n,s = kritaGetActives()

    
    val = getLayerinfo(n)[key]

    insertValue(widget.parent(), val)
def staticInsert(widget, val):

    insertValue(widget.parent(), val)

def fetchAndInsertAll():
    d,n,s = kritaGetActives()


def kritaGetActives():
        d = Application.activeDocument()
        if not d:
            #print("returning 3none")
            return None,None,None
        n = d.activeNode()
        s = d.selection()

        return d,n,s


    

def queue_predict(body):

    req = urllib.request.Request(config.base_url)

    body_encoded = json.dumps(body).encode('utf-8')
    req.data=body_encoded
    req.add_header('Content-Type', 'application/json')
    req.add_header('Content-Length', str(len(body_encoded)))

    """
    print("Requesting Image - URL:")
    print(req.full_url)
    print("HEADERS:")
    print(req.header_items())
    print("BODY:")
    print(body_encoded)
    """

    with urllib.request.urlopen(req) as res:
        return json.loads(res.read())



def request(mode,in_data):
    body  = {"fn_index":fn_indices[mode],
    "data":in_data,
    "session_hash":None}

    res = queue_predict(body)

    #Formatting the response, so that we only have keys that correspond to an input field:

    response_dict = json.loads(res['data'][1])
    #print(res['data'][2] )

    trunc = re.search(r'some \((.*?)\) have',res['data'][2] )
    if trunc is not None:
        tok = trunc.group(1)
        
        tok = int(tok)
        #TODO: Refactor so this spaghetticode isn't necessary. Abstract this so we can set form values from anywhere. It's late.
        
        dockersList = Krita.instance().dockers()
        for docker in dockersList:
            if docker.objectName() == DOCKER_ID:  #DOCKER_ID is defined again at the top, UGLY HACK, REDO, TODO, FIXME
                tab = docker.tabWidget.currentWidget()
                
                for child in tab.findChildren(QGroupBox):
                    if child.title() == "prompt":
                        prompt_text = extractValue(child)

                        toastError("Prompt too long. Clipped \""+prompt_text[len(prompt_text)-tok:] + "\" off the end.\nSee prompt input form.")

                        prompt_text = prompt_text[:-tok]
                        insertValue(child, prompt_text)





    layerinfo = {}
    for key in response_dict:
        
        if key in ui_tags[mode]:
            layerinfo[key] = response_dict[key]



    OutputToLayers(res['data'][0], layerinfo)

def OutputToLayers(images,layerinfo):
    img_count = len(images)

    #idata = data['data'][0][0]
    global temp_alphabuffer
    if temp_alphabuffer is not None:
        temp_alphabuffer = temp_alphabuffer.convertToFormat(QImage.Format_Alpha8)
    
    for idata in images:
        
        # strip prefix, transcode the png bytes into QImage, get rgba into ptr
        idata = idata[len("data:image/png;base64,"):]
        idata = base64.decodebytes(idata.encode('utf-8'))
        imagen = QtGui.QImage()
        imagen.loadFromData( idata, 'PNG' )

        if temp_alphabuffer is not None:
            imagen.setAlphaChannel(temp_alphabuffer) #TODO: Outpainting bugged because imgsize in != imgsize out, i guess we could assume a=1.0 on new pixels in a fix
           
        ptr = imagen.bits()
        ptr.setsize(imagen.byteCount())

        #Krita Setup for the layer, including name
        d, n, s = kritaGetActives() 
        root = d.rootNode()
        n = d.createNode(json.dumps(layerinfo), "paintLayer")
        root.addChildNode(n, None)

        size = imagen.rect()

        #write pixels and refresh 
        #TODO clean this up a little for async receive. might be possible that s = None
        n.setPixelData(QByteArray(ptr.asstring()),s.x(),s.y(),size.width(),size.height())
        d.waitForDone()

        #Fixing the seeds
        layerinfo["seed"] +=1
        layerinfo["subseed"] += 1


    d.refreshProjection()

def pngstring(pixel_data=None):
    global temp_alphabuffer
    d, n, s = kritaGetActives()

    d.refreshProjection()
    #n=getLayer()     
    if not pixel_data: 
        pixel_data=d.pixelData(s.x(),s.y(),s.width(),s.height())
        
    image=QImage(pixel_data.data(),s.width(),s.height(),QImage.Format_RGBA8888).rgbSwapped()    
    temp_alphabuffer = image

    

    data = QByteArray()
    buf = QBuffer(data)
    image.save(buf, 'PNG')
    ba=data.toBase64()
    DataAsString=str(ba,"utf-8")
    image64 = "data:image/png;base64,"+DataAsString
    #image64 = DataAsString
    return image64