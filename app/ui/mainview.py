# -*- coding: utf-8 -*-
"""
@File    : mainview.py
@Author  : Shuaikang Zhou
@Time    : 2022/12/13 15:07
@IDE     : Pycharm
@Version : Python3.10
@comment : 主窗口
"""
import json
import os.path
import traceback

from PyQt5.QtCore import pyqtSignal, QThread, QSize
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtWidgets import QMainWindow, QLabel, QMessageBox

from app.DataBase import misc_db, micro_msg_db, close_db
from app.ui.Icon import Icon
from . import mainwindow
# 不能删，删了会出错
from .chat import ChatWindow
from .contact import ContactWindow
from app.ui.tool.tool_window import ToolWindow
from .menu.export import ExportDialog
from ..DataBase.output_pc import Output
from ..components.QCursorGif import QCursorGif
from ..log import logger
from ..person import Me

try:
    from app.ui.menu.about_dialog import AboutDialog, version, UpdateThread
except ModuleNotFoundError:
    logger.error(f'Python版本错误:Python>=3.10,仅支持3.10、3.11、3.12')
    raise ValueError('Python版本错误:Python>=3.10,仅支持3.10、3.11、3.12')
# 美化样式表
Stylesheet = """
QWidget{
    background: rgb(238,244,249);
}
/*去掉item虚线边框*/
QListWidget, QListView, QTreeWidget, QTreeView {
    outline: 0px;
}
QMenu::item:selected {
      color: black;
      background: rgb(230, 235, 240);
}
/*设置左侧选项的最小最大宽度,文字颜色和背景颜色*/
QListWidget {
    min-width: 120px;
    max-width: 380px;
    color: black;
    border:none;
}
QListWidget::item{
    min-width: 80px;
    max-width: 380px;
    min-height: 60px;
    max-height: 60px;
}
QListWidget::item:hover {
    background: rgb(230, 235, 240);
}
/*被选中时的背景颜色和左边框颜色*/
QListWidget::item:selected {
    background: rgb(230, 235, 240);
    border-left: 2px solid rgb(62, 62, 62);
    color: black;
    font-weight: bold;
}
/*鼠标悬停颜色*/
HistoryPanel::item:hover {
    background: rgb(52, 52, 52);
}

QCheckBox::indicator {
    background: rgb(255, 255, 255);
    Width:20px;
    Height:20px;
    border-radius: 10px
}
QCheckBox::indicator:unchecked{
    Width:20px;
    Height:20px;
    image: url(:/icons/icons/unselect.svg);
}
QCheckBox::indicator:checked{
    Width:20px;
    Height:20px;
    image: url(:/icons/icons/select.svg);
}
QScrollBar:vertical {
    border-width: 0px;
    border: none;
    background:rgba(133, 135, 138, 0);
    width:4px;
    margin: 0px 0px 0px 0px;
}
QScrollBar::handle:vertical {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
    stop: 0 rgb(133, 135, 138), stop: 0.5 rgb(133, 135, 138), stop:1 rgb(133, 135, 138));
    min-height: 20px;
    max-height: 20px;
    margin: 0 0px 0 0px;
    border-radius: 2px;
}
QScrollBar::add-line:vertical {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
    stop: 0 rgba(133, 135, 138, 0), stop: 0.5 rgba(133, 135, 138, 0),  stop:1 rgba(133, 135, 138, 0));
    height: 0px;
    border: none;
    subcontrol-position: bottom;
    subcontrol-origin: margin;
}
QScrollBar::sub-line:vertical {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
    stop: 0  rgba(133, 135, 138, 0), stop: 0.5 rgba(133, 135, 138, 0),  stop:1 rgba(133, 135, 138, 0));
    height: 0 px;
    border: none;
    subcontrol-position: top;
    subcontrol-origin: margin;
}
QScrollBar::sub-page:vertical {
    background: rgba(133, 135, 138, 0);
}

QScrollBar::add-page:vertical {
    background: rgba(133, 135, 138, 0);
}
"""


class MainWinController(QMainWindow, mainwindow.Ui_MainWindow, QCursorGif):
    exitSignal = pyqtSignal(bool)
    okSignal = pyqtSignal(bool)

    # username = ''
    def __init__(self, username, parent=None):
        super(MainWinController, self).__init__(parent)
        self.outputThread0 = None
        self.outputThread = None
        self.setupUi(self)

        # self.setWindowIcon(Icon.MainWindow_Icon)
        pixmap = QPixmap(Icon.logo_ico_path)
        icon = QIcon(pixmap)
        self.setWindowIcon(icon)
        self.setStyleSheet(Stylesheet)
        self.listWidget.clear()
        self.resize(QSize(800, 600))

        self.load_flag = False
        self.load_data()
        self.load_num = 0
        self.label = QLabel(self)
        self.label.setGeometry((self.width() - 300) // 2, (self.height() - 100) // 2, 300, 100)
        self.label.setPixmap(QPixmap(':/icons/icons/loading.svg'))
        self.menu_output.setIcon(Icon.Output)
        self.action_output_CSV.setIcon(Icon.ToCSV)
        self.action_output_CSV.triggered.connect(self.output)
        self.action_output_contacts.setIcon(Icon.Output)
        self.action_output_contacts.triggered.connect(self.output)
        self.action_batch_export.setIcon(Icon.Output)
        self.action_batch_export.triggered.connect(self.output)
        self.action_desc.setIcon(Icon.Help_Icon)

    def load_data(self, flag=True):
        if os.path.exists('./app/data/info.json'):
            with open('./app/data/info.json', 'r', encoding='utf-8') as f:
                dic = json.loads(f.read())
                wxid = dic.get('wxid')
                if wxid:
                    me = Me()
                    me.wxid = dic.get('wxid')
                    me.name = dic.get('name')
                    me.mobile = dic.get('mobile')
                    me.wx_dir = dic.get('wx_dir')
                    self.set_my_info(wxid)
                    self.load_flag = True
        else:
            pass

    def init_ui(self):

        # 设置忙碌光标图片数组
        self.initCursor([':/icons/icons/Cursors/%d.png' %
                         i for i in range(8)])
        self.setCursorTimeout(100)
        self.startBusy()
        self.action_update.triggered.connect(self.update)
        self.about_view = AboutDialog(main_window=self, parent=self)

    def setCurrentIndex(self, row):
        self.stackedWidget.setCurrentIndex(row)
        if row == 2:
            self.stackedWidget.currentWidget().show_contacts()
        if row == 1:
            self.stackedWidget.currentWidget().show_chats()

    def setWindow(self, window):
        try:
            window.load_finish_signal.connect(self.loading)
        except:
            pass
        self.stackedWidget.addWidget(window)

    def set_my_info(self, wxid):
        self.avatar = QPixmap()
        try:
            img_bytes = misc_db.get_avatar_buffer(wxid)
        except:
            close_db()
            logger.error(f'数据库错误:\n{traceback.format_exc()}')
            QMessageBox.critical(self, "数据库错误", "请重启微信后重试")
            import shutil
            shutil.rmtree('./app/Database/Msg')
            return
        if not img_bytes:
            return
        if img_bytes[:4] == b'\x89PNG':
            self.avatar.loadFromData(img_bytes, format='PNG')
        else:
            self.avatar.loadFromData(img_bytes, format='jfif')
        self.avatar.scaled(60, 60)
        contact_info_list = micro_msg_db.get_contact_by_username(wxid)
        me = Me()
        me.set_avatar(img_bytes)
        me.smallHeadImgUrl = contact_info_list[7]
        self.myavatar.setScaledContents(True)
        self.myavatar.setPixmap(self.avatar)

    def stop_loading(self, a0):
        self.label.setVisible(False)
        self.stopBusy()

    def loading(self, a0):
        self.load_num += 1
        if self.load_num == 1:
            self.label.clear()
            self.label.hide()
            self.okSignal.emit(True)
            self.listWidget.setVisible(True)
            self.stackedWidget.setVisible(True)
            self.stopBusy()
            if self.load_flag:
                self.listWidget.setCurrentRow(1)
                self.stackedWidget.setCurrentIndex(1)
            else:
                self.listWidget.setCurrentRow(0)
                self.stackedWidget.setCurrentIndex(0)

    def output(self):
        # self.startBusy()
        if self.sender() == self.action_output_CSV:
            self.outputThread = Output(None, type_=Output.CSV_ALL)
            self.outputThread.startSignal.connect(lambda x: self.startBusy())
            self.outputThread.okSignal.connect(
                lambda x: self.message('聊天记录导出成功'))
            self.outputThread.start()
        elif self.sender() == self.action_output_contacts:
            self.outputThread = Output(None, type_=Output.CONTACT_CSV)
            self.outputThread.startSignal.connect(lambda x: self.startBusy())
            self.outputThread.okSignal.connect(
                lambda x: self.message('联系人导出成功'))
            self.outputThread.start()
        elif self.sender() == self.action_batch_export:
            dialog = ExportDialog(None, title='批量导出聊天记录', parent=self)
            result = dialog.exec_() # 使用exec_()获取用户的操作结果

    def message(self, msg):
        self.stopBusy()
        QMessageBox.about(self, "提醒", msg)

    def update(self):
        self.update_thread = UpdateThread()
        self.update_thread.updateSignal.connect(self.show_update)
        self.update_thread.start()

    def show_update(self, update_info):
        if not update_info.get('update_available'):
            QMessageBox.information(self, '更新通知', "当前已是最新版本")
            return
        detail = f'''
        当前版本:{version},最新版本:{update_info.get('latest_version')}<br>
        更新内容:
        {update_info.get('description')}
        <br><a href='{update_info.get('download_url')}'>点击下载</a>
        '''
        QMessageBox.information(self, '更新通知', detail)

    def about(self):
        """
        关于
        """
        self.about_view.show()

    def decrypt_success(self):
        QMessageBox.about(self, "解密成功", "请重新启动")
        self.close()

    def closeEvent(self, event):
        reply = QMessageBox.question(self, '确认退出', '确定要退出吗？',
                                     QMessageBox.Yes | QMessageBox.No,
                                     QMessageBox.No)

        if reply == QMessageBox.Yes:
            close_db()
            event.accept()
        else:
            event.ignore()

    def close(self) -> bool:
        close_db()
        self.contact_window.close()

        super().close()
        self.exitSignal.emit(True)


class LoadWindowThread(QThread):
    okSignal = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.num = 0

    def loading(self):
        self.num += 1
        print('加载一个了')
        if self.num == 2:
            self.okSignal.emit(True)

    def run(self):
        self.chat_window = ChatWindow()
        self.contact_window = ContactWindow()
        self.contact_window.load_finish_signal.connect(self.loading)
        self.chat_window.load_finish_signal.connect(self.loading)
        print('加载完成')
        self.okSignal.emit(True)
