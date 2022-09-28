#BBD's Krita Script Starter Feb 2018
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
from . import ui

default_url = "http://127.0.0.1:7860"

samplers = ["Euler a", "Euler", 'LMS', 'Heun', 'DPM2', 'DPM2 a', 'DDIM', 'PLMS']
samplers_img2img = ["Euler a", "Euler", 'LMS', 'Heun', 'DPM2', 'DPM2 a', 'DDIM']
upscalers = ["None", "Lanczos"]
realesrgan_models = ['RealESRGAN_x4plus', 'RealESRGAN_x4plus_anime_6B']

DOCKER_NAME = 'sd frontend'
DOCKER_ID = 'pykrita_sd_frontend'

#TODO: (SD-)Upscaling
#TODO: Outpainting
#TODO: some scripts?

class MyExtension(Extension):

    def __init__(self, parent):
        # This is initialising the parent, always important when subclassing.
        super().__init__(parent)

        self.docker = None
    def getDocker(self):

        if self.docker == None:
            dockersList = Krita.instance().dockers()
            for docker in dockersList:
                if docker.objectName() == DOCKER_ID:
                    self.docker= docker

        return self.docker
    def setup(self):
        pass

    def createActions(self, window):
        sdCheckReady_action = window.createAction("sdCheckReady", "SD Check requirements and fix", "tools/scripts")
        def f():

            toast(" mem")
            docker = self.getDocker()
            mode = docker.tabWidget.tabText( docker.tabWidget.currentIndex()) 
            loop_max = 32
            while not docker.checkReady(mode) and loop_max >0:
                #TODO: fix this, a bit unsafe if waiting on the "create Document" dialog. (infinite loop w/o user input)
                docker.checkReady(mode)
                loop_max -= 1
        sdCheckReady_action.triggered.connect(f)

        sdGenerate_action = window.createAction("sdGenerate", "SD Generate if ready", "tools/scripts")
        def f2():
            toastError(" lol")
            docker = self.getDocker()
            mode = docker.tabWidget.tabText( docker.tabWidget.currentIndex()) 
            docker.generate()
        sdGenerate_action.triggered.connect(f2)


config = QSettings(QSettings.IniFormat, QSettings.UserScope, "krita", "sd_frontend")

def box4var(label,list):
    gbox = QGroupBox(label)
    hbox = QHBoxLayout()

    for item in list:
        hbox.addWidget(item)

    gbox.setLayout(hbox)
    #gbox.setMaximumWidth(512)
    return gbox

def createSmartGroupBox(key, value):
    width = 0.5
    widgets = []
    if value == None or key.startswith("!"):  # ! means no gui. 'it just werks' (tm)
        return None, None

    elif key.find("prompt") != -1:
        widgets = [QPlainTextEdit(str(value))]
        width= 1.0

    elif key == "seed":
        line = QLineEdit()
        line.setText("-1")

        reset = QPushButton("🎲")
        reset.clicked.connect(lambda: staticInsert(reset, "-1"))

        keep = QPushButton("♻️")

        keep.clicked.connect(lambda: fetchAndInsert(keep, "seed"))

        widgets = [line,reset,keep]

    elif key == "subseed":
        line = QLineEdit()
        line.setText("-1")

        reset = QPushButton("🎲")
        reset.clicked.connect(lambda: staticInsert(reset, "-1"))

        keep = QPushButton("♻️")

        keep.clicked.connect(lambda: fetchAndInsert(keep, "subseed"))

        widgets = [line,reset,keep]

    elif type(value) is bool:
        chk = QCheckBox()
        chk.setChecked(value)
        widgets = [chk]
    elif type(value) is int:
        sb = QSpinBox()
        sb.setMaximum(1024)
        sb.setValue(value)
        widgets = [sb]
    elif type(value) is float:
        doublespinbox = QDoubleSpinBox()
        doublespinbox.setMinimum(-10.0)
        doublespinbox.setMaximum(30.0)
        doublespinbox.setValue(value)
        if key == "cfg_scale":
            doublespinbox.setSingleStep(0.5)
            width = 0.5
        else:
            doublespinbox.setSingleStep(.01)   
        widgets = [doublespinbox]      
    elif isinstance(value, list):
        cb = QComboBox()
        cb.addItems(value)
        widgets = [cb]
    else:
        widgets = [QPushButton(str(value))]
      
    return width, box4var(key, widgets)


def createTabFromJSONDict(dict):
    tabg = QWidget()
    layout = QVBoxLayout()

    stash = None
    for key in dict.keys():
        w, gbox = createSmartGroupBox(key, dict[key])
        if gbox != None:
            if stash == None and w==1.0:
                layout.addWidget(gbox)
            elif stash == None and w==0.5:
                stash = gbox
            elif stash != None and w==0.5:
                
                hbox = QHBoxLayout()

                hbox.addWidget(stash)
                hbox.addWidget(gbox)
                #vsplit.setLayout(hbox)
                layout.addLayout(hbox)

                stash = None
            
            elif stash != None and w==1.0:
                layout.addWidget(stash)
                layout.addWidget(gbox)
                stash = None
    if stash != None:
        hbox = QHBoxLayout()

        hbox.addWidget(stash)
        layout.addLayout(hbox)

        stash = None
    tabg.setLayout(layout)

    scroll = QtWidgets.QScrollArea()
    scroll.setWidget(tabg)
    scroll.setWidgetResizable(True)
    ##scroll.setMaximumWidth(512)

    return scroll    

class SD_frontend(DockWidget):

    def __init__(self):
        super().__init__()

        self.createInterface()

        
        self.setWindowTitle(DOCKER_NAME)
        print("sd frontend loaded")


    def createModeTab(self,mode):
        tab = QWidget()
        layout = QVBoxLayout()

        headerlayout= QHBoxLayout()
        btn_recycle = QPushButton("♻️")
        btn_recycle.setMaximumWidth(64)
        btn_recycle.clicked.connect(self.recycle)

        headerlayout.addWidget(btn_recycle)

        btn_run=QPushButton("Generate")
        btn_run.setStyleSheet("background-color: rgb(255, 153, 28); color: black; font: 14px;")
        btn_run.clicked.connect(self.generate)
        headerlayout.addWidget(btn_run)

        layout.addLayout(headerlayout)
        

        layout.addWidget(ui.createUITab(mode))
        tab.setLayout(layout)
        self.tabWidget.addTab(tab, mode )


    def createInterface(self):
        
        self.tabWidget = QTabWidget()

        for mode in fn_indices.keys():
            self.createModeTab(mode)
        

        widget = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(self.tabWidget)
        widget.setLayout(layout)
        self.setWidget(widget) 

    def findGroupBoxValue(self, key, tab):
        for child in tab.findChildren(QGroupBox):
            if child.title() == key:
                return extractValue(child)

    def setGroupBoxValue(self, key, tab, val):
        for child in tab.findChildren(QGroupBox):
            if child.title() == key:
                return insertValue(child, val)

    def canvasChanged(self, canvas):
        pass

    def checkReady(self, mode): #this function checks all requirements and fixes bad setup (no open document, no selection, no mask, etc.)
        
        d,n,s = kritaGetActives()

        if not d: 
            print("no document open - opening dialog")
            Krita.instance().action("file_new").trigger()
            return False

        #cursory testing: there is always a node (layer) in an open document, you cannot delete the last one, we don't need to check
        if not s:            
            
            #if the active layer has useful bounds
            rect = n.bounds()
            if rect.width()%64 == 0 and rect.height()%64 ==0:
                s=Selection()  
                s.select(rect.x(), rect.y(), rect.width(), rect.height(), 255)
                d.setSelection(s)
                print("no selection had been made - selected the active layer")
                return False    

            s=Selection()  
            s.select(0, 0, 512, 512, 255)
            d.setSelection(s)
            print("no selection had been made - selected 512,512 in top left corner")
            return False
        
        mod_w, mod_h = s.width()%64, s.height()%64

        if mod_w != 0 or mod_h !=0:
            print("selection was not multiple of 64 - resized")

            newx = s.x()-(64-mod_w)
            newy = s.y()-(64-mod_h)

            neww = s.width()+(64-mod_w)
            newh = s.height()+(64-mod_h)

            neww = max(config.value("min_size", type=int),neww)
            newh = max(config.value("min_size", type=int),newh)

            neww = min(config.value("max_size", type=int),neww)
            newh = min(config.value("max_size", type=int),newh)

            s=Selection() 
            s.select(newx, newy, neww, newh, 255)
            d.setSelection(s) 

            d.refreshProjection()
            #print(s.x() +" " + s.y())
            #print(s.width() +" " + s.height())
            return False

        if "!mask_in" in ui_tags[mode]:

            mask = d.nodeByName("!sdmask")
            if not mask or not mask.visible():
                print("mask needed - creating layer")
                
                mask=d.createNode("!sdmask", "paintlayer")
                mask.setOpacity(128)
                col_white = ManagedColor("RGBA", "U8", "")
                col_white.setComponents([1.0,1.0,1.0,1.0])
                Krita.instance().activeWindow().activeView().setForeGroundColor(col_white)
                n.parentNode().addChildNode(mask, d.topLevelNodes()[-1])

                d.setActiveNode(mask)
                return False
            """
            if n.name() != "!sdmask":
                print("mask was not selected")
                mask = d.nodeByName("!sdmask")
                d.setActiveNode(mask)
                return False
            """
            
        #if everything is ok
        return True    

    def recycle(self):
        mode = self.tabWidget.tabText( self.tabWidget.currentIndex()) 

        d, n, s = kritaGetActives()
        inputdict = getLayerinfo(n)

        for key in inputdict:
            self.setGroupBoxValue(key, self.tabWidget.currentWidget(), inputdict[key])
            #print(val)

    def generate(self):

        # Why get all the info from QT names? 
        #Because we set the QTWidget names according to the datadict keys (The gui autoconstructs) and I want this low maintenance! 
        #Adapt datadict (with help from Burp Suite interceptor or Wireshark) and you're g2g even with a new version of upstream webui.
      
        mode = self.tabWidget.tabText( self.tabWidget.currentIndex()) 

        if self.checkReady(mode):
            #print("all requirements good to go")
            pass
        else:
            #print("requirements needed fixing, click again to generate")
            return
        

        d, n, s = kritaGetActives()


        #switch this to gatherParams() then iterate over the ui_tags list and the defaultslist, deepcopy that.
        # insert parameters from ui there, and add the !params



        params = ui.gatherParameters(self.tabWidget.currentWidget())

        apidata = []
        

        #sanity checks!
        print("\n x-x-x-x-x-x-x-x \n")

        print(mode)
        print("length of JSON data lists: ui_tags, apidata ,defaults")
        print(len(defaults[mode]), end=":")
        print(len(ui_tags[mode]), end=":")
        if len(ui_tags[mode])  != len(defaults[mode]):
            print("\n[ERROR] - Sanity Check failed for ui_tags and defaults, apidata will be nonsense")


        for i in range(len(defaults[mode])):
            if ui_tags[mode][i] is not None:

                p = ui.gatherParameter(self.tabWidget.currentWidget(), ui_tags[mode][i] )
                apidata.append(p)
            else:
                apidata.append(defaults[mode][i] )

        print(len(apidata) )

        if len(apidata) == len(defaults[mode]):
            print("Sanity Check passed!")
        else:
            print("\n[ERROR] - Sanity Check failed")

        print("i\t\tdefault\t\tapi\t\ttag")
        for i in range(len(defaults[mode]) ): 
            if apidata[i] != defaults[mode][i]:
                api_clrpng = apidata[i]
                if isinstance(api_clrpng,str) and len(api_clrpng)>512:
                    api_clrpng = "!!PNGDATA!!"

                dbg_tup = (i,defaults[mode][i],api_clrpng,ui_tags[mode][i])
                print(dbg_tup)

        print("\n x-x-x-x-x-x-x-x \n")
        request(mode,apidata)



instance = Krita.instance()
instance.addExtension(MyExtension(instance))
dock_widget_factory = DockWidgetFactory(DOCKER_ID,
                                        DockWidgetFactoryBase.DockRight,
                                        SD_frontend)

instance.addDockWidgetFactory(dock_widget_factory)

