from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.Console import Console
from Components.ActionMap import ActionMap, NumberActionMap
from Components.Pixmap import Pixmap
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Components.MenuList import MenuList
from Components.config import getConfigListEntry, configfile, ConfigSelection, ConfigSubsection, ConfigText, ConfigLocations
from Components.config import config
from Components.ConfigList import ConfigList, ConfigListScreen
from Components.FileList import MultiFileSelectList
from Plugins.Plugin import PluginDescriptor
from enigma import eTimer, eEnv
from Tools.Directories import *
from os import popen, path, makedirs, listdir, access, stat, rename, remove, W_OK, R_OK
from time import gmtime, strftime, localtime
from datetime import date
config.plugins.ctpanel = ConfigSubsection()
config.plugins.ctpanel.configurationbackup = ConfigSubsection()
config.plugins.ctpanel.configurationbackup.backuplocation = ConfigText(default='/media/hdd/', visible_width=50, fixed_size=False)
config.plugins.ctpanel.configurationbackup.backupdirs = ConfigLocations(default=[eEnv.resolve('${sysconfdir}/enigma2/'),
 '/etc/CCcam.cfg',
 '/etc/network/interfaces',
 '/etc/wpa_supplicant.conf',
 '/etc/resolv.conf',
 '/etc/default_gw',
 '/etc/hostname'])

def getBackupPath():
    backuppath = config.plugins.xtpanel.configurationbackup.backuplocation.value
    if backuppath.endswith('/'):
        return backuppath + 'xtbackup'
    else:
        return backuppath + '/xtbackup'


def getBackupFilename():
    return 'ctsettingsbackup.tar.gz'


class BackupScreen(Screen, ConfigListScreen):

    def __init__(self, session, runBackup = False):
        Screen.__init__(self, session)
        self.session = session
        self.runBackup = runBackup
        self['actions'] = ActionMap(['WizardActions', 'DirectionActions'], {'ok': self.close,
         'back': self.close,
         'cancel': self.close}, -1)
        self.finished_cb = None
        self.backuppath = getBackupPath()
        self.backupfile = getBackupFilename()
        self.fullbackupfilename = self.backuppath + '/' + self.backupfile
        self.list = []
        ConfigListScreen.__init__(self, self.list)
        self.onLayoutFinish.append(self.layoutFinished)
        if self.runBackup:
            self.onShown.append(self.doBackup)

    def layoutFinished(self):
        self.setWindowTitle()

    def setWindowTitle(self):
        self.setTitle(_('Backup is running...'))

    def doBackup(self):
        configfile.save()
        try:
            if path.exists(self.backuppath) == False:
                makedirs(self.backuppath)
            self.backupdirs = ' '.join(config.plugins.ctpanel.configurationbackup.backupdirs.value)
            if path.exists(self.fullbackupfilename):
                dt = str(date.fromtimestamp(stat(self.fullbackupfilename).st_ctime))
                self.newfilename = self.backuppath + '/' + dt + '-' + self.backupfile
                if path.exists(self.newfilename):
                    remove(self.newfilename)
                rename(self.fullbackupfilename, self.newfilename)
            if self.finished_cb:
                self.session.openWithCallback(self.finished_cb, Console, title=_('Backup is running...'), cmdlist=['tar -czvf ' + self.fullbackupfilename + ' ' + self.backupdirs], finishedCallback=self.backupFinishedCB, closeOnSuccess=True)
            else:
                self.session.open(Console, title=_('Backup is running...'), cmdlist=['tar -czvf ' + self.fullbackupfilename + ' ' + self.backupdirs], finishedCallback=self.backupFinishedCB, closeOnSuccess=True)
        except OSError:
            if self.finished_cb:
                self.session.openWithCallback(self.finished_cb, MessageBox, _('Sorry your backup destination is not writeable.\nPlease choose an other one.'), MessageBox.TYPE_INFO, timeout=10)
            else:
                self.session.openWithCallback(self.backupErrorCB, MessageBox, _('Sorry your backup destination is not writeable.\nPlease choose an other one.'), MessageBox.TYPE_INFO, timeout=10)

    def backupFinishedCB(self, retval = None):
        self.close(True)

    def backupErrorCB(self, retval = None):
        self.close(False)

    def runAsync(self, finished_cb):
        self.finished_cb = finished_cb
        self.doBackup()


class BackupSelection(Screen):

    def __init__(self, session):
        Screen.__init__(self, session)
        self['key_red'] = StaticText(_('Cancel'))
        self['key_green'] = StaticText(_('Save'))
        self['key_yellow'] = StaticText()
        self.selectedFiles = config.plugins.ctpanel.configurationbackup.backupdirs.value
        defaultDir = '/'
        inhibitDirs = ['/bin',
         '/boot',
         '/dev',
         '/autofs',
         '/lib',
         '/proc',
         '/sbin',
         '/sys',
         '/hdd',
         '/tmp',
         '/mnt',
         '/media']
        self.filelist = MultiFileSelectList(self.selectedFiles, defaultDir, inhibitDirs=inhibitDirs)
        self['checkList'] = self.filelist
        self['actions'] = ActionMap(['DirectionActions', 'OkCancelActions', 'ShortcutActions'], {'cancel': self.exit,
         'red': self.exit,
         'yellow': self.changeSelectionState,
         'green': self.saveSelection,
         'ok': self.okClicked,
         'left': self.left,
         'right': self.right,
         'down': self.down,
         'up': self.up}, -1)
        if self.selectionChanged not in self['checkList'].onSelectionChanged:
            self['checkList'].onSelectionChanged.append(self.selectionChanged)
        self.onLayoutFinish.append(self.layoutFinished)

    def layoutFinished(self):
        idx = 0
        self['checkList'].moveToIndex(idx)
        self.setWindowTitle()
        self.selectionChanged()

    def setWindowTitle(self):
        self.setTitle(_('Select files/folders to backup'))

    def selectionChanged(self):
        current = self['checkList'].getCurrent()[0]
        if current[2] is True:
            self['key_yellow'].setText(_('Deselect'))
        else:
            self['key_yellow'].setText(_('Select'))

    def up(self):
        self['checkList'].up()

    def down(self):
        self['checkList'].down()

    def left(self):
        self['checkList'].pageUp()

    def right(self):
        self['checkList'].pageDown()

    def changeSelectionState(self):
        self['checkList'].changeSelectionState()
        self.selectedFiles = self['checkList'].getSelectedList()

    def saveSelection(self):
        self.selectedFiles = self['checkList'].getSelectedList()
        config.plugins.ctpanel.configurationbackup.backupdirs.value = self.selectedFiles
        config.plugins.ctpanel.configurationbackup.backupdirs.save()
        config.plugins.ctpanel.configurationbackup.save()
        config.save()
        self.close(None)

    def exit(self):
        self.close(None)

    def okClicked(self):
        if self.filelist.canDescent():
            self.filelist.descent()


class RestoreMenu(Screen):

    def __init__(self, session, plugin_path):
        Screen.__init__(self, session)
        self.skin_path = plugin_path
        self['key_red'] = StaticText(_('Cancel'))
        self['key_green'] = StaticText(_('Restore'))
        self['key_yellow'] = StaticText(_('Delete'))
        self.sel = []
        self.val = []
        self.entry = False
        self.exe = False
        self.path = ''
        self['actions'] = NumberActionMap(['SetupActions'], {'ok': self.KeyOk,
         'cancel': self.keyCancel}, -1)
        self['shortcuts'] = ActionMap(['ShortcutActions'], {'red': self.keyCancel,
         'green': self.KeyOk,
         'yellow': self.deleteFile})
        self.flist = []
        self['filelist'] = MenuList(self.flist)
        self.fill_list()
        self.onLayoutFinish.append(self.layoutFinished)

    def layoutFinished(self):
        self.setWindowTitle()

    def setWindowTitle(self):
        self.setTitle(_('Restore backups'))

    def fill_list(self):
        self.flist = []
        self.path = getBackupPath()
        if path.exists(self.path) == False:
            makedirs(self.path)
        for file in listdir(self.path):
            if file.endswith('.tar.gz'):
                self.flist.append(file)
                self.entry = True

        self['filelist'].l.setList(self.flist)

    def KeyOk(self):
        if self.exe == False and self.entry == True:
            self.sel = self['filelist'].getCurrent()
            if self.sel:
                self.val = self.path + '/' + self.sel
                self.session.openWithCallback(self.startRestore, MessageBox, _('Are you sure you want to restore\nfollowing backup:\n') + self.sel + _('\nSystem will restart after the restore!'))

    def keyCancel(self):
        self.close()

    def startRestore(self, ret = False):
        if ret == True:
            self.exe = True
            self.session.open(Console, title=_('Restore running'), cmdlist=['tar -xzvf ' + self.path + '/' + self.sel + ' -C /', 'killall -9 enigma2'])

    def deleteFile(self):
        if self.exe == False and self.entry == True:
            self.sel = self['filelist'].getCurrent()
            if self.sel:
                self.val = self.path + '/' + self.sel
                self.session.openWithCallback(self.startDelete, MessageBox, _('Are you sure you want to delete\nfollowing backup:\n') + self.sel)

    def startDelete(self, ret = False):
        if ret == True:
            self.exe = True
            print 'removing:', self.val
            if path.exists(self.val) == True:
                remove(self.val)
            self.exe = False
            self.fill_list()


class RestoreScreen(Screen, ConfigListScreen):

    def __init__(self, session, runRestore = False):
        Screen.__init__(self, session)
        self.session = session
        self.runRestore = runRestore
        self['actions'] = ActionMap(['WizardActions', 'DirectionActions'], {'ok': self.close,
         'back': self.close,
         'cancel': self.close}, -1)
        self.finished_cb = None
        self.backuppath = getBackupPath()
        self.backupfile = getBackupFilename()
        self.fullbackupfilename = self.backuppath + '/' + self.backupfile
        self.list = []
        ConfigListScreen.__init__(self, self.list)
        self.onLayoutFinish.append(self.layoutFinished)
        if self.runRestore:
            self.onShown.append(self.doRestore)

    def layoutFinished(self):
        self.setWindowTitle()

    def setWindowTitle(self):
        self.setTitle(_('Restore is running...'))

    def doRestore(self):
        if path.exists('/proc/stb/vmpeg/0/dst_width'):
            restorecmdlist = ['tar -xzvf ' + self.fullbackupfilename + ' -C /',
             'echo 0 > /proc/stb/vmpeg/0/dst_height',
             'echo 0 > /proc/stb/vmpeg/0/dst_left',
             'echo 0 > /proc/stb/vmpeg/0/dst_top',
             'echo 0 > /proc/stb/vmpeg/0/dst_width',
             'killall -9 enigma2']
        else:
            restorecmdlist = ['tar -xzvf ' + self.fullbackupfilename + ' -C /', 'killall -9 enigma2']
        if self.finished_cb:
            self.session.openWithCallback(self.finished_cb, Console, title=_('Restore is running...'), cmdlist=restorecmdlist)
        else:
            self.session.open(Console, title=_('Restore is running...'), cmdlist=restorecmdlist)

    def backupFinishedCB(self, retval = None):
        self.close(True)

    def backupErrorCB(self, retval = None):
        self.close(False)

    def runAsync(self, finished_cb):
        self.finished_cb = finished_cb
        self.doRestore()