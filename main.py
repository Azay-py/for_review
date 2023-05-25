# : Использовать библиотеку высокого уровня для подключения TCP/IP (asyncio) вместо низкоуровневого socket добавить qasync для связи PyQt5 и asyncio
import snap7

import sys
import socket
import asyncio
import qasync


from snap7.util import *
from snap7.types import *

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject, pyqtSlot

SERVER_ADDRESS = '192.168.0.55'
SERVER_PORT = 59999


class TCPSocket(QObject):
    data_received = pyqtSignal(str)
    connection_status_changed = pyqtSignal(bool)

    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None
        self.connected = False

    @pyqtSlot(str)
    async def send_data(self, data):
        try:
            if self.writer is not None:
                self.writer.write(data)
                await self.writer.drain()
        except Exception as e:
            print(f"Class TCPSocket def send_data exception:{e}")

    async def start(self):
        while True:
            try:
                self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
                self.connected = True
                self.connection_status_changed.emit(True)

                while True:
                    data = await self.reader.read(100)
                    if not data:
                        break
                    self.data_received.emit(data)

            except OSError:
                self.connected = False
                self.connection_status_changed.emit(False)
                await asyncio.sleep(5)

            finally:
                if self.writer is not None:
                    self.writer.close()
                    await self.writer.wait_closed()
                self.connected = False
                self.connection_status_changed.emit(False)


def connect_to_plc(ip_address, rack, slot):
    plc = snap7.client.Client()
    try:
        plc.connect(ip_address, rack, slot)
        return plc  # Return plc object and connection status flag True
    except Exception as e:
        print(f"Connection error to PLC: {e}")
        return None  # Return None and the connection status flag False


def connect_to_tcp_ip_server():
    # : Вынести отдельно функцию подключения к серверу
    pass


def read_plc_memory(plc, byte, bit, datatype):  # define read memory function !!! MARKER Area !!!
    try:
        result = plc.read_area(snap7.types.Areas.MK, 0, byte, datatype)  # read_area(area: snap7.types.Areas, dbnumber: (equal to 0 if Marker), start: int, size: int)
        if datatype == S7WLBit:
            return get_bool(result, 0, bit)
        elif datatype == S7WLByte:
            return get_byte(result, 0)
        elif datatype == S7WLWord:
            return get_word(result, 0)
        elif datatype == S7WLInt:
            return get_int(result, 0)
        elif datatype == S7WLReal:
            return get_real(result, 0)
        elif datatype == S7WLDWord:
            return get_dword(result, 0)
        else:
            return None
    except Exception as e:
        print(f"Error reading PLC memory: {e}")
        return None


def write_plc_memory(plc, byte, bit, datatype, value):  # define write memory function !!! MARKER Area !!!
    try:
        result = plc.read_area(snap7.types.Areas.MK, 0, byte, datatype)
        if datatype == S7WLBit:
            set_bool(result, 0, bit, value)
        elif datatype == S7WLByte:
            set_byte(result, 0, value)
        elif datatype == S7WLWord:
            set_word(result, 0, value)
        elif datatype == S7WLInt:
            set_int(result, 0, value)
        elif datatype == S7WLReal:
            set_real(result, 0, value)
        elif datatype == S7WLDWord:
            set_dword(result, 0, value)
        plc.write_area(snap7.types.Areas.MK, 0, byte, result)
    except Exception as e:
        print(f"Error writing PLC memory: {e}")


class PLCThread(QThread):
    value_updated = pyqtSignal()  # сигнал для обновления GUI

    def run(self):
        try:
            while True:

                # Get PLC connection status
                plc_dict['conn_status'] = plc.get_connected()
                print(f"plc_conn_status: {plc_dict['conn_status']}")

                # Get PLC state
                plc_dict['state'] = str(plc.get_cpu_state()) # S7CpuStatusRun or S7CpuStatusStop
                print(f"plc_state: {plc_dict['state']}")

                # Get X axis values
                x_srv_dict['position'] = round(read_plc_memory(plc, 4, 0, S7WLReal), 2)
                x_srv_dict['force'] = read_plc_memory(plc, 10, 0, S7WLWord)
                x_srv_dict['speed'] = read_plc_memory(plc, 8, 0, S7WLWord)
                x_srv_dict['error'] = read_plc_memory(plc, 26, 1, S7WLBit)
                x_srv_dict['step_data_out'] = read_plc_memory(plc, 0, 0, S7WLByte)

                # Set X axis control values
                if x_srv_dict['jog_plus_btn']:
                    write_plc_memory(plc, 2, 2, S7WLBit, True)
                else:
                    write_plc_memory(plc, 2, 2, S7WLBit, False)

                if x_srv_dict['jog_minus_btn']:
                    write_plc_memory(plc, 2, 3, S7WLBit, True)
                else:
                    write_plc_memory(plc, 2, 3, S7WLBit, False)

                if x_srv_dict['return_btn']:
                    write_plc_memory(plc, 2, 5, S7WLBit, True)
                else:
                    write_plc_memory(plc, 2, 5, S7WLBit, False)

                if x_srv_dict['reset_err_btn']:
                    write_plc_memory(plc, 24, 0, S7WLBit, True)
                else:
                    write_plc_memory(plc, 24, 0, S7WLBit, False)

                if x_srv_dict['servo_on']:
                    write_plc_memory(plc, 2, 7, S7WLBit, True)
                else:
                    write_plc_memory(plc, 2, 7, S7WLBit, False)

                if x_srv_dict['drive']:
                    write_plc_memory(plc, 2, 6, S7WLBit, True)
                else:
                    write_plc_memory(plc, 2, 6, S7WLBit, False)

                write_plc_memory(plc, 25, 0, S7WLByte, x_srv_dict['step_position'])

                # Get Y axis values
                y_srv_dict['position'] = round(read_plc_memory(plc, 36, 0, S7WLReal), 2)
                y_srv_dict['speed'] = read_plc_memory(plc, 34, 0, S7WLWord)
                y_srv_dict['force'] = read_plc_memory(plc, 28, 0, S7WLWord)
                y_srv_dict['error'] = read_plc_memory(plc, 51, 3, S7WLBit)
                y_srv_dict['step_data_out'] = read_plc_memory(plc, 41, 0, S7WLByte)

                # Set Y axis control values
                if y_srv_dict['jog_plus_btn']:
                    write_plc_memory(plc, 26, 4, S7WLBit, True)
                else:
                    write_plc_memory(plc, 26, 4, S7WLBit, False)

                if y_srv_dict['jog_minus_btn']:
                    write_plc_memory(plc, 26, 5, S7WLBit, True)
                else:
                    write_plc_memory(plc, 26, 5, S7WLBit, False)

                if y_srv_dict['return_btn']:
                    write_plc_memory(plc, 26, 7, S7WLBit, True)
                else:
                    write_plc_memory(plc, 26, 7, S7WLBit, False)

                if y_srv_dict['reset_err_btn']:
                    write_plc_memory(plc, 50, 0, S7WLBit, True)
                else:
                    write_plc_memory(plc, 50, 0, S7WLBit, False)

                if y_srv_dict['servo_on']:
                    write_plc_memory(plc, 50, 2, S7WLBit, True)
                else:
                    write_plc_memory(plc, 50, 2, S7WLBit, False)

                if y_srv_dict['drive']:
                    write_plc_memory(plc, 50, 1, S7WLBit, True)
                else:
                    write_plc_memory(plc, 50, 1, S7WLBit, False)

                write_plc_memory(plc, 49, 0, S7WLByte, y_srv_dict['step_position'])

                self.value_updated.emit()  # send an update signal
                self.msleep(300)
        except Exception as e:
            print(f"PLCThread error: {e}")

            plc_dict['conn_status'] = False
            plc_dict['state'] = 'Error'

            print(f"plc_status: {plc_dict['conn_status']}")

            self.value_updated.emit()  # send an update signal
            self.msleep(300)


class TerminalWriter:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, text):
        cursor = self.text_widget.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertText(text)
        self.text_widget.setTextCursor(cursor)
        self.text_widget.ensureCursorVisible()


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):

        self.host = "192.168.0.55"
        self.port = 59999


        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1355, 812)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.stateGroupBox = QtWidgets.QGroupBox(self.centralwidget)
        self.stateGroupBox.setGeometry(QtCore.QRect(10, 20, 241, 281))
        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(False)
        font.setItalic(False)
        font.setWeight(50)
        self.stateGroupBox.setFont(font)
        self.stateGroupBox.setFlat(False)
        self.stateGroupBox.setObjectName("stateGroupBox")
        self.verticalLayoutWidget = QtWidgets.QWidget(self.stateGroupBox)
        self.verticalLayoutWidget.setGeometry(QtCore.QRect(0, 20, 161, 251))
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.stLayout = QtWidgets.QVBoxLayout(self.verticalLayoutWidget)
        self.stLayout.setContentsMargins(10, 0, 0, 0)
        self.stLayout.setObjectName("stLayout")
        self.txt_plc_con = QtWidgets.QLabel(self.verticalLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.txt_plc_con.setFont(font)
        self.txt_plc_con.setObjectName("txt_plc_con")
        self.stLayout.addWidget(self.txt_plc_con)
        self.txt_plc_state = QtWidgets.QLabel(self.verticalLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.txt_plc_state.setFont(font)
        self.txt_plc_state.setObjectName("txt_plc_state")
        self.stLayout.addWidget(self.txt_plc_state)
        self.txt_lsr_con = QtWidgets.QLabel(self.verticalLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.txt_lsr_con.setFont(font)
        self.txt_lsr_con.setObjectName("txt_lsr_con")
        self.stLayout.addWidget(self.txt_lsr_con)
        self.txt_lsr_init = QtWidgets.QLabel(self.verticalLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.txt_lsr_init.setFont(font)
        self.txt_lsr_init.setObjectName("txt_lsr_init")
        self.stLayout.addWidget(self.txt_lsr_init)
        self.verticalLayoutWidget_2 = QtWidgets.QWidget(self.stateGroupBox)
        self.verticalLayoutWidget_2.setGeometry(QtCore.QRect(160, 20, 71, 251))
        self.verticalLayoutWidget_2.setObjectName("verticalLayoutWidget_2")
        self.silLayout = QtWidgets.QVBoxLayout(self.verticalLayoutWidget_2)
        self.silLayout.setContentsMargins(10, 10, 10, 10)
        self.silLayout.setSpacing(20)
        self.silLayout.setObjectName("silLayout")
        self.ind_plc_conn = QtWidgets.QLabel(self.verticalLayoutWidget_2)
        self.ind_plc_conn.setMaximumSize(QtCore.QSize(69, 16777215))
        self.ind_plc_conn.setStyleSheet("background-color: rgb(85, 255, 0);")
        self.ind_plc_conn.setText("")
        self.ind_plc_conn.setObjectName("ind_plc_conn")
        self.silLayout.addWidget(self.ind_plc_conn)
        self.ind_plc_state = QtWidgets.QLabel(self.verticalLayoutWidget_2)
        self.ind_plc_state.setStyleSheet("background-color: rgb(85, 255, 0);")
        self.ind_plc_state.setText("")
        self.ind_plc_state.setObjectName("ind_plc_state")
        self.silLayout.addWidget(self.ind_plc_state)
        self.ind_laser_conn = QtWidgets.QLabel(self.verticalLayoutWidget_2)
        self.ind_laser_conn.setStyleSheet("background-color: rgb(85, 255, 0);")
        self.ind_laser_conn.setText("")
        self.ind_laser_conn.setObjectName("ind_laser_conn")
        self.silLayout.addWidget(self.ind_laser_conn)
        self.ind_laser_state = QtWidgets.QLabel(self.verticalLayoutWidget_2)
        self.ind_laser_state.setStyleSheet("background-color: rgb(85, 255, 0);")
        self.ind_laser_state.setText("")
        self.ind_laser_state.setObjectName("ind_laser_state")
        self.silLayout.addWidget(self.ind_laser_state)
        self.laserAndPlcControlGroupBox = QtWidgets.QGroupBox(self.centralwidget)
        self.laserAndPlcControlGroupBox.setGeometry(QtCore.QRect(10, 310, 241, 131))
        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(False)
        font.setItalic(False)
        font.setWeight(50)
        self.laserAndPlcControlGroupBox.setFont(font)
        self.laserAndPlcControlGroupBox.setFlat(False)
        self.laserAndPlcControlGroupBox.setObjectName("laserAndPlcControlGroupBox")
        self.gridLayoutWidget = QtWidgets.QWidget(self.laserAndPlcControlGroupBox)
        self.gridLayoutWidget.setGeometry(QtCore.QRect(10, 30, 221, 81))
        self.gridLayoutWidget.setObjectName("gridLayoutWidget")
        self.gridLayout = QtWidgets.QGridLayout(self.gridLayoutWidget)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.btnOpenDoor = QtWidgets.QPushButton(self.gridLayoutWidget)
        self.btnOpenDoor.setObjectName("btnOpenDoor")
        self.gridLayout.addWidget(self.btnOpenDoor, 0, 0, 1, 1)
        self.btnStartPLC = QtWidgets.QPushButton(self.gridLayoutWidget)
        self.btnStartPLC.setObjectName("btnStartPLC")
        self.gridLayout.addWidget(self.btnStartPLC, 1, 0, 1, 1)
        self.btnCloseDoor = QtWidgets.QPushButton(self.gridLayoutWidget)
        self.btnCloseDoor.setObjectName("btnCloseDoor")
        self.gridLayout.addWidget(self.btnCloseDoor, 0, 1, 1, 1)
        self.btnClosePLC = QtWidgets.QPushButton(self.gridLayoutWidget)
        self.btnClosePLC.setObjectName("btnClosePLC")
        self.gridLayout.addWidget(self.btnClosePLC, 1, 1, 1, 1)
        self.automaticModeLabel = QtWidgets.QLabel(self.centralwidget)
        self.automaticModeLabel.setGeometry(QtCore.QRect(270, 20, 591, 51))
        font = QtGui.QFont()
        font.setPointSize(30)
        font.setBold(True)
        font.setWeight(75)
        self.automaticModeLabel.setFont(font)
        self.automaticModeLabel.setScaledContents(False)
        self.automaticModeLabel.setObjectName("automaticModeLabel")
        self.statusBarTextBrowser = QtWidgets.QTextBrowser(self.centralwidget)
        self.statusBarTextBrowser.setGeometry(QtCore.QRect(270, 80, 591, 681))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.statusBarTextBrowser.setFont(font)
        self.statusBarTextBrowser.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.statusBarTextBrowser.setAutoFillBackground(False)
        self.statusBarTextBrowser.setStyleSheet("background-color: rgb(192, 255, 188);\n"
"padding-left: 10px;\n"
"padding-top: 10px;")
        self.statusBarTextBrowser.setObjectName("statusBarTextBrowser")
        self.TLVcontrolGroupBox = QtWidgets.QGroupBox(self.centralwidget)
        self.TLVcontrolGroupBox.setGeometry(QtCore.QRect(10, 460, 241, 301))
        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(False)
        font.setItalic(False)
        font.setWeight(50)
        self.TLVcontrolGroupBox.setFont(font)
        self.TLVcontrolGroupBox.setFlat(False)
        self.TLVcontrolGroupBox.setObjectName("TLVcontrolGroupBox")
        self.gridLayoutWidget_3 = QtWidgets.QWidget(self.TLVcontrolGroupBox)
        self.gridLayoutWidget_3.setGeometry(QtCore.QRect(10, 30, 221, 81))
        self.gridLayoutWidget_3.setObjectName("gridLayoutWidget_3")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.gridLayoutWidget_3)
        self.gridLayout_3.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.tagLabel = QtWidgets.QLabel(self.gridLayoutWidget_3)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.tagLabel.setFont(font)
        self.tagLabel.setObjectName("tagLabel")
        self.gridLayout_3.addWidget(self.tagLabel, 0, 0, 1, 1)

        self.valueTlvLineEdit = QtWidgets.QLineEdit(self.gridLayoutWidget_3)
        self.valueTlvLineEdit.setObjectName("valueTlvLineEdit")
        self.gridLayout_3.addWidget(self.valueTlvLineEdit, 1, 1, 1, 1)

        self.tagTlvLineEdit = QtWidgets.QLineEdit(self.gridLayoutWidget_3)
        self.tagTlvLineEdit.setObjectName("tagTlvLineEdit")

        self.gridLayout_3.addWidget(self.tagTlvLineEdit, 0, 1, 1, 1)


        self.valueLabel = QtWidgets.QLabel(self.gridLayoutWidget_3)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.valueLabel.setFont(font)
        self.valueLabel.setObjectName("valueLabel")
        self.gridLayout_3.addWidget(self.valueLabel, 1, 0, 1, 1)
        self.horizontalLayoutWidget = QtWidgets.QWidget(self.TLVcontrolGroupBox)
        self.horizontalLayoutWidget.setGeometry(QtCore.QRect(9, 119, 221, 35))
        self.horizontalLayoutWidget.setObjectName("horizontalLayoutWidget")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.horizontalLayoutWidget)
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.responseLabel = QtWidgets.QLabel(self.horizontalLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.responseLabel.setFont(font)
        self.responseLabel.setObjectName("responseLabel")
        self.horizontalLayout_2.addWidget(self.responseLabel)
        self.btnSendTLVreq = QtWidgets.QPushButton(self.horizontalLayoutWidget)
        self.btnSendTLVreq.setObjectName("btnSendTLVreq")
        self.horizontalLayout_2.addWidget(self.btnSendTLVreq)
        self.responseTlvTextEdit = QtWidgets.QTextEdit(self.TLVcontrolGroupBox)
        self.responseTlvTextEdit.setGeometry(QtCore.QRect(10, 160, 221, 141))
        self.responseTlvTextEdit.setObjectName("responseTlvTextEdit")
        self.bluechipsLogoLabel = QtWidgets.QLabel(self.centralwidget)
        self.bluechipsLogoLabel.setGeometry(QtCore.QRect(880, 80, 461, 101))
        self.bluechipsLogoLabel.setText("")
        self.bluechipsLogoLabel.setPixmap(QtGui.QPixmap("C:/Users/a.karama/Desktop/BlueChips logo 1.png"))
        self.bluechipsLogoLabel.setObjectName("bluechipsLogoLabel")
        self.servoDriveControlGroupBox = QtWidgets.QGroupBox(self.centralwidget)
        self.servoDriveControlGroupBox.setGeometry(QtCore.QRect(880, 190, 451, 571))
        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(False)
        font.setItalic(False)
        font.setWeight(50)
        self.servoDriveControlGroupBox.setFont(font)
        self.servoDriveControlGroupBox.setFlat(False)
        self.servoDriveControlGroupBox.setObjectName("servoDriveControlGroupBox")
        self.XaxisGroupBox = QtWidgets.QGroupBox(self.servoDriveControlGroupBox)
        self.XaxisGroupBox.setGeometry(QtCore.QRect(10, 30, 421, 261))
        self.XaxisGroupBox.setObjectName("XaxisGroupBox")
        self.label_11 = QtWidgets.QLabel(self.XaxisGroupBox)
        self.label_11.setGeometry(QtCore.QRect(210, 30, 111, 21))
        self.label_11.setObjectName("label_11")
        self.XerrorStatusIndicator = QtWidgets.QLabel(self.XaxisGroupBox)
        self.XerrorStatusIndicator.setGeometry(QtCore.QRect(310, 30, 20, 20))
        self.XerrorStatusIndicator.setMaximumSize(QtCore.QSize(69, 16777215))
        self.XerrorStatusIndicator.setStyleSheet("background-color: rgb(85, 255, 0);")
        self.XerrorStatusIndicator.setText("")
        self.XerrorStatusIndicator.setObjectName("XerrorStatusIndicator")
        self.XservoControlRadioButton = QtWidgets.QRadioButton(self.XaxisGroupBox)
        self.XservoControlRadioButton.setGeometry(QtCore.QRect(20, 30, 151, 21))
        self.XservoControlRadioButton.setObjectName("XservoControlRadioButton")
        self.XbtnReturnToOrigin = QtWidgets.QPushButton(self.XaxisGroupBox)
        self.XbtnReturnToOrigin.setGeometry(QtCore.QRect(20, 210, 130, 40))
        self.XbtnReturnToOrigin.setObjectName("XbtnReturnToOrigin")
        self.XbtnResetErrors = QtWidgets.QPushButton(self.XaxisGroupBox)
        self.XbtnResetErrors.setGeometry(QtCore.QRect(260, 210, 130, 40))
        self.XbtnResetErrors.setObjectName("XbtnResetErrors")
        self.XjogModeGroupBox = QtWidgets.QGroupBox(self.XaxisGroupBox)
        self.XjogModeGroupBox.setGeometry(QtCore.QRect(260, 130, 130, 70))
        self.XjogModeGroupBox.setObjectName("XjogModeGroupBox")
        self.XbtnJogMinus = QtWidgets.QPushButton(self.XjogModeGroupBox)
        self.XbtnJogMinus.setGeometry(QtCore.QRect(10, 30, 50, 30))
        self.XbtnJogMinus.setObjectName("XbtnJogMinus")
        self.XbtnJogPlus = QtWidgets.QPushButton(self.XjogModeGroupBox)
        self.XbtnJogPlus.setGeometry(QtCore.QRect(70, 30, 50, 30))
        self.XbtnJogPlus.setObjectName("XbtnJogPlus")
        self.label_6 = QtWidgets.QLabel(self.XaxisGroupBox)
        self.label_6.setGeometry(QtCore.QRect(210, 60, 75, 25))
        self.label_6.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.label_6.setObjectName("label_6")
        self.XPositionLabel = QtWidgets.QLabel(self.XaxisGroupBox)
        self.XPositionLabel.setGeometry(QtCore.QRect(290, 60, 65, 25))
        self.XPositionLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.XPositionLabel.setObjectName("XPositionLabel")
        self.label_8 = QtWidgets.QLabel(self.XaxisGroupBox)
        self.label_8.setGeometry(QtCore.QRect(20, 60, 71, 25))
        self.label_8.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.label_8.setObjectName("label_8")
        self.XPointLabel = QtWidgets.QLabel(self.XaxisGroupBox)
        self.XPointLabel.setGeometry(QtCore.QRect(90, 60, 45, 25))
        self.XPointLabel.setAutoFillBackground(False)
        self.XPointLabel.setScaledContents(True)
        self.XPointLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.XPointLabel.setWordWrap(False)
        self.XPointLabel.setObjectName("XPointLabel")
        self.label_10 = QtWidgets.QLabel(self.XaxisGroupBox)
        self.label_10.setGeometry(QtCore.QRect(360, 60, 41, 25))
        self.label_10.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.label_10.setObjectName("label_10")
        self.label_12 = QtWidgets.QLabel(self.XaxisGroupBox)
        self.label_12.setGeometry(QtCore.QRect(140, 90, 51, 25))
        self.label_12.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.label_12.setObjectName("label_12")
        self.label_13 = QtWidgets.QLabel(self.XaxisGroupBox)
        self.label_13.setGeometry(QtCore.QRect(20, 90, 71, 25))
        self.label_13.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.label_13.setObjectName("label_13")
        self.XSpeedLabel = QtWidgets.QLabel(self.XaxisGroupBox)
        self.XSpeedLabel.setGeometry(QtCore.QRect(90, 90, 45, 25))
        self.XSpeedLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.XSpeedLabel.setObjectName("XSpeedLabel")
        self.XForceLabel = QtWidgets.QLabel(self.XaxisGroupBox)
        self.XForceLabel.setGeometry(QtCore.QRect(290, 90, 65, 25))
        self.XForceLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.XForceLabel.setObjectName("XForceLabel")
        self.label_16 = QtWidgets.QLabel(self.XaxisGroupBox)
        self.label_16.setGeometry(QtCore.QRect(360, 90, 31, 25))
        self.label_16.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.label_16.setObjectName("label_16")
        self.label_17 = QtWidgets.QLabel(self.XaxisGroupBox)
        self.label_17.setGeometry(QtCore.QRect(210, 90, 75, 25))
        self.label_17.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.label_17.setObjectName("label_17")
        self.XpointModeGroupBox = QtWidgets.QGroupBox(self.XaxisGroupBox)
        self.XpointModeGroupBox.setGeometry(QtCore.QRect(10, 130, 230, 70))
        self.XpointModeGroupBox.setObjectName("XpointModeGroupBox")
        self.XpositionComboBox = QtWidgets.QComboBox(self.XpointModeGroupBox)
        self.XpositionComboBox.setGeometry(QtCore.QRect(10, 30, 121, 31))
        self.XpositionComboBox.setObjectName("XpositionComboBox")
        self.XpositionComboBox.addItem("")
        self.XpositionComboBox.addItem("")
        self.XpositionComboBox.addItem("")
        self.XbtnGo = QtWidgets.QPushButton(self.XpointModeGroupBox)
        self.XbtnGo.setGeometry(QtCore.QRect(150, 30, 71, 31))
        self.XbtnGo.setObjectName("XbtnGo")
        self.YaxisGroupBox = QtWidgets.QGroupBox(self.servoDriveControlGroupBox)
        self.YaxisGroupBox.setGeometry(QtCore.QRect(10, 300, 421, 261))
        self.YaxisGroupBox.setObjectName("YaxisGroupBox")
        self.label_54 = QtWidgets.QLabel(self.YaxisGroupBox)
        self.label_54.setGeometry(QtCore.QRect(210, 30, 111, 21))
        self.label_54.setObjectName("label_54")
        self.YerrorStatusIndicator = QtWidgets.QLabel(self.YaxisGroupBox)
        self.YerrorStatusIndicator.setGeometry(QtCore.QRect(320, 30, 20, 20))
        self.YerrorStatusIndicator.setMaximumSize(QtCore.QSize(69, 16777215))
        self.YerrorStatusIndicator.setStyleSheet("background-color: rgb(85, 255, 0);")
        self.YerrorStatusIndicator.setText("")
        self.YerrorStatusIndicator.setObjectName("YerrorStatusIndicator")
        self.YservoControlRadioButton = QtWidgets.QRadioButton(self.YaxisGroupBox)
        self.YservoControlRadioButton.setGeometry(QtCore.QRect(20, 30, 151, 21))
        self.YservoControlRadioButton.setObjectName("YservoControlRadioButton")
        self.YjogModeGroupBox = QtWidgets.QGroupBox(self.YaxisGroupBox)
        self.YjogModeGroupBox.setGeometry(QtCore.QRect(260, 130, 130, 70))
        self.YjogModeGroupBox.setObjectName("YjogModeGroupBox")
        self.YbtnJogMinus = QtWidgets.QPushButton(self.YjogModeGroupBox)
        self.YbtnJogMinus.setGeometry(QtCore.QRect(10, 30, 50, 30))
        self.YbtnJogMinus.setObjectName("YbtnJogMinus")
        self.YbtnJogPlus = QtWidgets.QPushButton(self.YjogModeGroupBox)
        self.YbtnJogPlus.setGeometry(QtCore.QRect(70, 30, 50, 30))
        self.YbtnJogPlus.setObjectName("YbtnJogPlus")
        self.label_55 = QtWidgets.QLabel(self.YaxisGroupBox)
        self.label_55.setGeometry(QtCore.QRect(210, 60, 75, 25))
        self.label_55.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.label_55.setObjectName("label_55")
        self.YPositionLabel = QtWidgets.QLabel(self.YaxisGroupBox)
        self.YPositionLabel.setGeometry(QtCore.QRect(290, 60, 65, 25))
        self.YPositionLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.YPositionLabel.setObjectName("YPositionLabel")
        self.label_57 = QtWidgets.QLabel(self.YaxisGroupBox)
        self.label_57.setGeometry(QtCore.QRect(20, 60, 71, 25))
        self.label_57.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.label_57.setObjectName("label_57")
        self.YPointLabel = QtWidgets.QLabel(self.YaxisGroupBox)
        self.YPointLabel.setGeometry(QtCore.QRect(90, 60, 45, 25))
        self.YPointLabel.setAutoFillBackground(False)
        self.YPointLabel.setScaledContents(True)
        self.YPointLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.YPointLabel.setWordWrap(False)
        self.YPointLabel.setObjectName("YPointLabel")
        self.label_59 = QtWidgets.QLabel(self.YaxisGroupBox)
        self.label_59.setGeometry(QtCore.QRect(360, 60, 41, 25))
        self.label_59.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.label_59.setObjectName("label_59")
        self.label_60 = QtWidgets.QLabel(self.YaxisGroupBox)
        self.label_60.setGeometry(QtCore.QRect(140, 90, 51, 25))
        self.label_60.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.label_60.setObjectName("label_60")
        self.label_61 = QtWidgets.QLabel(self.YaxisGroupBox)
        self.label_61.setGeometry(QtCore.QRect(20, 90, 71, 25))
        self.label_61.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.label_61.setObjectName("label_61")
        self.YSpeedLabel = QtWidgets.QLabel(self.YaxisGroupBox)
        self.YSpeedLabel.setGeometry(QtCore.QRect(90, 90, 45, 25))
        self.YSpeedLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.YSpeedLabel.setObjectName("YSpeedLabel")
        self.YForceLabel = QtWidgets.QLabel(self.YaxisGroupBox)
        self.YForceLabel.setGeometry(QtCore.QRect(290, 90, 65, 25))
        self.YForceLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.YForceLabel.setObjectName("YForceLabel")
        self.label_64 = QtWidgets.QLabel(self.YaxisGroupBox)
        self.label_64.setGeometry(QtCore.QRect(360, 90, 31, 25))
        self.label_64.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.label_64.setObjectName("label_64")
        self.label_65 = QtWidgets.QLabel(self.YaxisGroupBox)
        self.label_65.setGeometry(QtCore.QRect(210, 90, 75, 25))
        self.label_65.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.label_65.setObjectName("label_65")
        self.YbtnReturnToOrigin = QtWidgets.QPushButton(self.YaxisGroupBox)
        self.YbtnReturnToOrigin.setGeometry(QtCore.QRect(20, 210, 130, 40))
        self.YbtnReturnToOrigin.setObjectName("YbtnReturnToOrigin")
        self.YbtnResetErrors = QtWidgets.QPushButton(self.YaxisGroupBox)
        self.YbtnResetErrors.setGeometry(QtCore.QRect(260, 210, 130, 40))
        self.YbtnResetErrors.setObjectName("YbtnResetErrors")
        self.YpointModeGroupBox = QtWidgets.QGroupBox(self.YaxisGroupBox)
        self.YpointModeGroupBox.setGeometry(QtCore.QRect(10, 130, 230, 70))
        self.YpointModeGroupBox.setObjectName("YpointModeGroupBox")
        self.YpositionComboBox = QtWidgets.QComboBox(self.YpointModeGroupBox)
        self.YpositionComboBox.setGeometry(QtCore.QRect(10, 30, 121, 31))
        self.YpositionComboBox.setObjectName("YpositionComboBox")
        self.YpositionComboBox.addItem("")
        self.YpositionComboBox.addItem("")
        self.YpositionComboBox.addItem("")
        self.YbtnGo = QtWidgets.QPushButton(self.YpointModeGroupBox)
        self.YbtnGo.setGeometry(QtCore.QRect(150, 30, 71, 31))
        self.YbtnGo.setObjectName("YbtnGo")
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1355, 21))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        # Control X axis control area
        self.XservoControlRadioButton.toggled.connect(self.x_servo_on_radio_button_changed)
        self.XbtnResetErrors.pressed.connect(self.x_reset_errors_btn_pressed)
        self.XbtnResetErrors.released.connect(self.x_reset_errors_btn_released)
        self.XbtnReturnToOrigin.pressed.connect(self.x_return_to_origin_btn_pressed)
        self.XbtnReturnToOrigin.released.connect(self.x_return_to_origin_btn_released)
        self.XbtnJogPlus.pressed.connect(self.x_jog_plus_btn_pressed)
        self.XbtnJogPlus.released.connect(self.x_jog_plus_btn_released)
        self.XbtnJogMinus.pressed.connect(self.x_jog_minus_btn_pressed)
        self.XbtnJogMinus.released.connect(self.x_jog_minus_btn_released)
        self.XbtnGo.pressed.connect(self.x_go_btn_pressed)
        self.XbtnGo.released.connect(self.x_go_btn_released)
        self.XpositionComboBox.currentIndexChanged.connect(self.x_position_combo_box_changed)

        # Connect Y axis control area
        self.YservoControlRadioButton.toggled.connect(self.y_servo_on_radio_button_changed)
        self.YbtnResetErrors.pressed.connect(self.y_reset_errors_btn_pressed)
        self.YbtnResetErrors.released.connect(self.y_reset_errors_btn_released)
        self.YbtnReturnToOrigin.pressed.connect(self.y_return_to_origin_btn_pressed)
        self.YbtnReturnToOrigin.released.connect(self.y_return_to_origin_btn_released)
        self.YbtnJogPlus.pressed.connect(self.y_jog_plus_btn_pressed)
        self.YbtnJogPlus.released.connect(self.y_jog_plus_btn_released)
        self.YbtnJogMinus.pressed.connect(self.y_jog_minus_btn_pressed)
        self.YbtnJogMinus.released.connect(self.y_jog_minus_btn_released)
        self.YbtnGo.pressed.connect(self.y_go_btn_pressed)
        self.YbtnGo.released.connect(self.y_go_btn_released)
        self.YpositionComboBox.currentIndexChanged.connect(self.y_position_combo_box_changed)

        # Laser and PLC Control buttons
        self.btnStartPLC.clicked.connect(self.plc_start_btn_clicked)
        self.btnClosePLC.clicked.connect(self.plc_stop_btn_clicked)

        # Create and run a PLC memory read
        self.plc_thread = PLCThread()
        self.plc_thread.value_updated.connect(self.update_labels)  # подключаем сигнал к слоту обновления виджетов
        self.plc_thread.start()

        # Перенаправление вывода в терминале на QTextBrowser
        sys.stdout = TerminalWriter(self.statusBarTextBrowser)
        sys.stderr = TerminalWriter(self.statusBarTextBrowser)

        # TLV connection to Trumark
        self.loop = qasync.QEventLoop()
        asyncio.set_event_loop(self.loop)

        self.tcp_socket = TCPSocket(self.host, self.port)
        self.loop.create_task(self.tcp_socket.start())

        self.tcp_socket.data_received.connect(self.display_received_data)
        self.tcp_socket.connection_status_changed.connect(self.update_connection_status)
        self.btnSendTLVreq.clicked.connect(self.send_data)


    def encode_tlv(self, tag, value):
        try:
            print(f"encode_TLV started")
            print(f"tag: {tag}, {type(tag)}, value: {value}, {type(value)}")

            # tag: str and value: str
            tag = int(tag)
            tag_bytes = tag.to_bytes(4, byteorder='little')

            words = value.split()

            ascii_words = [w.encode('ascii') for w in words]
            format_value = b'\x00'.join(ascii_words) + b'\x00'

            length_bytes = len(format_value).to_bytes(4, byteorder='little')
            return tag_bytes + length_bytes + format_value
        except Exception as e:
            print(f"def encode_tlv exception: {e}")
    def decode_tlv(self, data):
        try:
            tag = int.from_bytes(data[:4], byteorder='little')
            length = int.from_bytes(data[4:8], byteorder='little')
            value = data[8:8 + length]
            return tag, length, value
        except Exception as e:
            print(f"def DEcode_tlv exception: {e}")




    @pyqtSlot()
    def send_data(self):
        try:
            # Clear response area
            self.responseTlvTextEdit.clear()

            tag = self.tagTlvLineEdit.text()
            value = self.valueTlvLineEdit.text()
            if tag and value:
                try:
                    print(f"tag: {tag}")
                    print(f"value: {value}")
                    format_message = self.encode_tlv(tag, value)
                    print(f"Encode data to send: {value}, value(type): {type(value)}")

                    self.responseTlvTextEdit.append("Отправлено: " + self.tagTlvLineEdit.text() + self.valueTlvLineEdit.text())
                    asyncio.run_coroutine_threadsafe(self.tcp_socket.send_data(format_message), self.loop)
                    self.tagTlvLineEdit.clear()
                    self.valueTlvLineEdit.clear()

                except Exception as e:
                    print(f"Send_data 2 EXCEPTION: {e}")

        except Exception as e:
            print(f"Send_data 1 EXCEPTION: {e}")

    @pyqtSlot(str)
    def display_received_data(self, data):
        try:
            tag, length, value = self.decode_tlv(data)
            self.responseTlvTextEdit.append(f"Получено: tag: {tag}, length: {length}, value: {value}")
        except Exception as e:
            print(f"display_received_data EXCEPTION: {e}")

    @pyqtSlot(bool)
    def update_connection_status(self, connected):
        try:
            if connected:
                self.ind_laser_conn.setText("CONN")
                self.ind_laser_conn.setStyleSheet("color: green")
            else:
                self.ind_laser_conn.setText("ERR")
                self.ind_laser_conn.setStyleSheet("color: red")
        except Exception as e:
            print(f"update_connection_status EXCEPTION: {e}")

    def closeEvent(self, event):
        try:
            if self.tcp_socket.connected:
                self.loop.create_task(self.tcp_socket.writer.close())
            self.loop.close()
            event.accept()
        except Exception as e:
            print(f"closeEvent EXCEPTION: {e}")


    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Bluechips Microhouse Co., Ltd. - LaserControl version 01.00"))
        self.stateGroupBox.setTitle(_translate("MainWindow", "State"))
        self.txt_plc_con.setText(_translate("MainWindow", "PLC connected"))
        self.txt_plc_state.setText(_translate("MainWindow", "PLC state"))
        self.txt_lsr_con.setText(_translate("MainWindow", "Laser connected"))
        self.txt_lsr_init.setText(_translate("MainWindow", "Laser initialised"))
        self.laserAndPlcControlGroupBox.setTitle(_translate("MainWindow", "Laser and PLC control"))
        self.btnOpenDoor.setText(_translate("MainWindow", "Open door"))
        self.btnStartPLC.setText(_translate("MainWindow", "PLC start"))
        self.btnCloseDoor.setText(_translate("MainWindow", "Close door"))
        self.btnClosePLC.setText(_translate("MainWindow", "PLC stop"))
        self.automaticModeLabel.setText(_translate("MainWindow", "Automatic Mode"))
        self.statusBarTextBrowser.setHtml(_translate("MainWindow", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'MS Shell Dlg 2\'; font-size:12pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:10pt;\">Workflow started</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:10pt;\">Start reading module information.</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:10pt;\">Product: 022-1223414</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:10pt;\">Serialnumber: 123456</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:10pt;\">Module identified</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:10pt;\">Module status OK</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:10pt;\">2 orders found</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:10pt;\">Start marking</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:10pt;\">Starting page B</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:10pt;\">Startinf page A</span></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:10pt;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:10pt;\">Modul passed</span></p></body></html>"))
        self.TLVcontrolGroupBox.setTitle(_translate("MainWindow", "TLV control"))
        self.tagLabel.setText(_translate("MainWindow", "Tag:"))
        self.valueLabel.setText(_translate("MainWindow", "Value:"))
        self.responseLabel.setText(_translate("MainWindow", "Response:"))
        self.btnSendTLVreq.setText(_translate("MainWindow", "SEND"))
        self.servoDriveControlGroupBox.setTitle(_translate("MainWindow", "Servo drive control:"))
        self.XaxisGroupBox.setTitle(_translate("MainWindow", "X axis:"))
        self.label_11.setText(_translate("MainWindow", "Error status:"))
        self.XservoControlRadioButton.setText(_translate("MainWindow", "Servo On / Off"))
        self.XbtnReturnToOrigin.setText(_translate("MainWindow", "Return to origin"))
        self.XbtnResetErrors.setText(_translate("MainWindow", "Reset errors"))
        self.XjogModeGroupBox.setTitle(_translate("MainWindow", "Jog mode:"))
        self.XbtnJogMinus.setText(_translate("MainWindow", "<"))
        self.XbtnJogPlus.setText(_translate("MainWindow", ">"))
        self.label_6.setText(_translate("MainWindow", "Position:"))
        self.XPositionLabel.setText(_translate("MainWindow", "n/f"))
        self.label_8.setText(_translate("MainWindow", "Point:"))
        self.XPointLabel.setText(_translate("MainWindow", "n/f"))
        self.label_10.setText(_translate("MainWindow", "mm"))
        self.label_12.setText(_translate("MainWindow", "mm/s"))
        self.label_13.setText(_translate("MainWindow", "Speed:"))
        self.XSpeedLabel.setText(_translate("MainWindow", "n/f"))
        self.XForceLabel.setText(_translate("MainWindow", "n/f"))
        self.label_16.setText(_translate("MainWindow", "%"))
        self.label_17.setText(_translate("MainWindow", "Force:"))
        self.XpointModeGroupBox.setTitle(_translate("MainWindow", "Point mode:"))
        self.XpositionComboBox.setItemText(0, _translate("MainWindow", "Position 1"))
        self.XpositionComboBox.setItemText(1, _translate("MainWindow", "Position 2"))
        self.XpositionComboBox.setItemText(2, _translate("MainWindow", "Position 3"))
        self.XbtnGo.setText(_translate("MainWindow", "Go"))
        self.YaxisGroupBox.setTitle(_translate("MainWindow", "Y axis:"))
        self.label_54.setText(_translate("MainWindow", "Error status:"))
        self.YservoControlRadioButton.setText(_translate("MainWindow", "Servo On / Off"))
        self.YjogModeGroupBox.setTitle(_translate("MainWindow", "Jog mode:"))
        self.YbtnJogMinus.setText(_translate("MainWindow", "<"))
        self.YbtnJogPlus.setText(_translate("MainWindow", ">"))
        self.label_55.setText(_translate("MainWindow", "Position:"))
        self.YPositionLabel.setText(_translate("MainWindow", "n/f"))
        self.label_57.setText(_translate("MainWindow", "Point:"))
        self.YPointLabel.setText(_translate("MainWindow", "n/f"))
        self.label_59.setText(_translate("MainWindow", "mm"))
        self.label_60.setText(_translate("MainWindow", "mm/s"))
        self.label_61.setText(_translate("MainWindow", "Speed:"))
        self.YSpeedLabel.setText(_translate("MainWindow", "n/f"))
        self.YForceLabel.setText(_translate("MainWindow", "n/f"))
        self.label_64.setText(_translate("MainWindow", "%"))
        self.label_65.setText(_translate("MainWindow", "Force:"))
        self.YbtnReturnToOrigin.setText(_translate("MainWindow", "Return to origin"))
        self.YbtnResetErrors.setText(_translate("MainWindow", "Reset errors"))
        self.YpointModeGroupBox.setTitle(_translate("MainWindow", "Point mode:"))
        self.YpositionComboBox.setItemText(0, _translate("MainWindow", "Position 1"))
        self.YpositionComboBox.setItemText(1, _translate("MainWindow", "Position 2"))
        self.YpositionComboBox.setItemText(2, _translate("MainWindow", "Position 3"))
        self.YbtnGo.setText(_translate("MainWindow", "Go"))

    def update_labels(self):

        # PLC connection error
        if plc_dict['conn_status']:
            self.ind_plc_conn.setStyleSheet("background-color: green")
        else:
            self.ind_plc_conn.setStyleSheet("background-color: red")

        # PLC state
        if plc_dict['state'] == 'S7CpuStatusRun':
            self.ind_plc_state.setStyleSheet("background-color: green")
            self.ind_plc_state.setText("RUN")
            self.ind_plc_state.setAlignment(Qt.AlignCenter)
        elif plc_dict['state'] == 'S7CpuStatusStop':
            self.ind_plc_state.setStyleSheet("background-color: yellow")
            self.ind_plc_state.setText("STOP")
            self.ind_plc_state.setAlignment(Qt.AlignCenter)
        else:
            self.ind_plc_state.setStyleSheet("background-color: red")
            self.ind_plc_state.setText("ERR")
            self.ind_plc_state.setAlignment(Qt.AlignCenter)

        # Handle X axis Error status ind
        if x_srv_dict['error']:
            self.XerrorStatusIndicator.setStyleSheet("background-color: red")
        else:
            self.XerrorStatusIndicator.setStyleSheet("background-color: green")

        self.XPositionLabel.setText(str(x_srv_dict["position"]))
        self.XForceLabel.setText(str(x_srv_dict["force"]))
        self.XSpeedLabel.setText(str(x_srv_dict["speed"]))
        self.XPointLabel.setText(str(x_srv_dict['point_num']))

        # Handle Y axis Error status ind
        if y_srv_dict['error']:
            self.YerrorStatusIndicator.setStyleSheet("background-color: red")
        else:
            self.YerrorStatusIndicator.setStyleSheet("background-color: green")

        self.YSpeedLabel.setText(str(y_srv_dict['speed']))
        self.YPointLabel.setText(str(y_srv_dict['point_num']))
        self.YPositionLabel.setText(str(y_srv_dict['position']))
        self.YForceLabel.setText(str(y_srv_dict['force']))
        self.YPointLabel.setText(str(y_srv_dict['step_data_out']))

    def x_go_btn_pressed(self):

        global x_srv_dict
        x_srv_dict['drive'] = True

    def x_go_btn_released(self):

        global x_srv_dict
        x_srv_dict['drive'] = False

    def x_jog_plus_btn_pressed(self):

        global x_srv_dict
        x_srv_dict['jog_plus_btn'] = True

    def x_jog_plus_btn_released(self):

        global x_srv_dict
        x_srv_dict['jog_plus_btn'] = False

    def x_jog_minus_btn_pressed(self):

        global x_srv_dict
        x_srv_dict['jog_minus_btn'] = True

    def x_jog_minus_btn_released(self):

        global x_srv_dict
        x_srv_dict['jog_minus_btn'] = False

    def x_return_to_origin_btn_pressed(self):

        global x_srv_dict
        x_srv_dict['return_btn'] = True

    def x_return_to_origin_btn_released(self):

        global x_srv_dict
        x_srv_dict['return_btn'] = False

    def x_reset_errors_btn_pressed(self):

        global x_srv_dict
        x_srv_dict['reset_err_btn'] = True

    def x_reset_errors_btn_released(self):

        global x_srv_dict
        x_srv_dict['reset_err_btn'] = False

    def x_position_combo_box_changed(self):

        global x_srv_dict
        x_srv_dict['step_position'] = self.XpositionComboBox.currentIndex()

    def x_servo_on_radio_button_changed(self, checked):

        global x_srv_dict
        if checked:
            x_srv_dict['servo_on'] = True
        else:
            x_srv_dict['servo_on'] = False

    # Y-axis control
    def y_go_btn_pressed(self):

        global y_srv_dict
        y_srv_dict['drive'] = True

    def y_go_btn_released(self):

        global y_srv_dict
        y_srv_dict['drive'] = False

    def y_jog_plus_btn_pressed(self):

        global y_srv_dict
        y_srv_dict['jog_plus_btn'] = True

    def y_jog_plus_btn_released(self):

        global y_srv_dict
        y_srv_dict['jog_plus_btn'] = False

    def y_jog_minus_btn_pressed(self):

        global y_srv_dict
        y_srv_dict['jog_minus_btn'] = True

    def y_jog_minus_btn_released(self):

        global y_srv_dict
        y_srv_dict['jog_minus_btn'] = False

    def y_return_to_origin_btn_pressed(self):

        global y_srv_dict
        y_srv_dict['return_btn'] = True

    def y_return_to_origin_btn_released(self):

        global y_srv_dict
        y_srv_dict['return_btn'] = False

    def y_reset_errors_btn_pressed(self):

        global y_srv_dict
        y_srv_dict['reset_err_btn'] = True

    def y_reset_errors_btn_released(self):

        global y_srv_dict
        y_srv_dict['reset_err_btn'] = False

    def y_position_combo_box_changed(self):

        global y_srv_dict
        y_srv_dict['step_position'] = self.YpositionComboBox.currentIndex()

    def y_servo_on_radio_button_changed(self, checked):

        global y_srv_dict
        if checked:
            y_srv_dict['servo_on'] = True
        else:
            y_srv_dict['servo_on'] = False

    def plc_start_btn_clicked(self):

        global plc, ip_address, rack, slot

        print(f"PLC start button clicked")

        plc = connect_to_plc(ip_address, rack, slot)

        if plc.get_connected():
            print(f"PLC connect SUCCESSFUL")
            self.plc_thread.start()
        else:
            print(f"PLC connection ERROR")

    def plc_stop_btn_clicked(self):

        global plc, ip_address, rack, slot

        print(f"PLC stop button clicked")
        plc.disconnect()

        if not plc.get_connected():
            print(f"PLC DISCONNECTED")
        else:
            print(f"PLC disconnection ERROR")


if __name__ == "__main__":

    ip_address = '192.168.0.1'
    rack = 0
    slot = 1

    x_srv_dict = {'servo_on': False,
                  'error_sts': False,
                  'point_num': 0,
                  'position': 0.0,
                  'speed': 0,
                  'force': 0,
                  'error': False,
                  'return_btn': False,
                  'reset_err_btn': False,
                  'jog_minus_btn': False,
                  'jog_plus_btn': False,
                  'drive': False,
                  'step_position': 0,
                  'step_data_out': 0}
    y_srv_dict = {'servo_on': False,
                  'error_sts': False,
                  'point_num': 0,
                  'position': 0.0,
                  'speed': 0,
                  'force': 0,
                  'error': False,
                  'return_btn': False,
                  'reset_err_btn': False,
                  'jog_minus_btn': False,
                  'jog_plus_btn': False,
                  'drive': False,
                  'step_position': 0,
                  'step_data_out': 0}
    plc_dict = {'conn_status': False,
                'state': '0'}

    # Connection to PLC
    plc = connect_to_plc(ip_address, rack, slot)


    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
