from kivy.logger import Logger

from jnius import JavaException, PythonJavaClass, autoclass, java_method
from androidstorage4kivy import SharedStorage

AndroidActivityInfo = autoclass('android.content.pm.ActivityInfo')
AndroidPythonActivity = autoclass('org.kivy.android.PythonActivity')
AndroidPackageManager = autoclass('android.content.pm.PackageManager')
Environment = autoclass('android.os.Environment')

#Portrait orientation
AndroidPythonActivity.mActivity.setRequestedOrientation(AndroidActivityInfo.SCREEN_ORIENTATION_PORTRAIT)

class StorageManager:
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ss = SharedStorage()

    def send_to_downloads(self,filename):
        path = self.ss.copy_to_shared(filename, collection = Environment.DIRECTORY_DOWNLOADS)
        return path