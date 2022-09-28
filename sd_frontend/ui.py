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
from . import defs_ui



def box4var(label,list):
    gbox = QGroupBox(label)
    hbox = QHBoxLayout()

    for item in list:
        hbox.addWidget(item)

    gbox.setLayout(hbox)
    #gbox.setMaximumWidth(512)
    return gbox

def makeInput(backend_parameter, widgetinfo):
    itype = widgetinfo["inputtype"]
    widgets = []

    if itype == "prompt":
        widgets = [QPlainTextEdit(str(widgetinfo["default"]))]

    elif itype == "seed":
        line = QLineEdit()
        line.setText("-1")

        reset = QPushButton("🎲")
        reset.clicked.connect(lambda: staticInsert(reset, "-1"))

        keep = QPushButton("♻️")

        keep.clicked.connect(lambda: fetchAndInsert(keep, backend_parameter))

        widgets = [line,reset,keep]
    elif itype == "outpainting_directions":
        widgets = []
        for name in widgetinfo["default"]:
            chk = QCheckBox(name)
            chk.setChecked(True)
            widgets.append(chk)

    elif itype == "QSpinBox":
        low, high, step = widgetinfo["range"]
        spinbox = QSpinBox()
        spinbox.setMinimum(low)
        spinbox.setMaximum(high)
        spinbox.setSingleStep(step)
        spinbox.setValue( widgetinfo["default"] )
        widgets = [spinbox]

    elif itype == "QDoubleSpinBox":
        low, high, step = widgetinfo["range"]
        doublespinbox = QDoubleSpinBox()
        doublespinbox.setMinimum(low)
        doublespinbox.setMaximum(high)
        doublespinbox.setSingleStep(step)
        doublespinbox.setValue( widgetinfo["default"] )
        widgets = [doublespinbox]    

    elif itype == "QCheckBox":
        chk = QCheckBox()
        chk.setChecked( widgetinfo["default"] )
        widgets = [chk]

    elif itype == "QComboBox":
        cb = QComboBox()
        cb.addItems( widgetinfo["ComboBoxOptions"] )
        widgets = [cb]

    return box4var(backend_parameter, widgets)

def createUITab(mode):
    tabg = QWidget()
    layout = QVBoxLayout()

    for param in ui_tags[mode]:
        if isinstance(param, str):
            if not param.startswith("!"):
                if param in defs_ui.parameter_widgetinfo:
                    layout.addWidget(makeInput(param, defs_ui.parameter_widgetinfo[param]))
                    
                else:
                    print("missing: \nparameter_widgetinfo[\""+param+"\"] = { }")

    tabg.setLayout(layout)

    scroll = QtWidgets.QScrollArea()
    scroll.setWidget(tabg)
    scroll.setWidgetResizable(True)
    ##scroll.setMaximumWidth(512)

    return scroll


def gatherParameters(tab):
    params = {}
    for child in tab.findChildren(QGroupBox):
        params[child.title()] = extractValue(child)
    return params

def gatherParameter(tab, param_name): #TODO: refactor this so that you can't weasel a !param into the groupbox labels
    param = None
    for child in tab.findChildren(QGroupBox):
        if child.title() == param_name:
            param = extractValue(child)
    if param is None:
        param = gatherSpecialParameters(param_name)

    if param is None:
        print("\nerror in gatherParameter")
        print(param_name)

    return param

def gatherSpecialParameters(param):
    d,n,s =kritaGetActives()
    if param == "!img_in":
        mask = d.nodeByName("!sdmask")
        if mask is not None:
            mask.setVisible(False)
        return pngstring()
    elif param == "!mask_in":
        print("masking")
        mask = d.nodeByName("!sdmask")
        mask.setVisible(True)
        return pngstring(mask.pixelData(s.x(),s.y(),s.width(),s.height() ))
    elif param == "!img_width":
        return s.width()
    elif param == "!img_height":
        return s.height()
    elif param == "!Script":
        return "None"