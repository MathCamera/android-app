from kivy.logger import Logger

from jnius import JavaException, PythonJavaClass, autoclass, java_method
from androidstorage4kivy import SharedStorage

AndroidActivityInfo = autoclass('android.content.pm.ActivityInfo')
AndroidPythonActivity = autoclass('org.kivy.android.PythonActivity')
AndroidPackageManager = autoclass('android.content.pm.PackageManager')
Environment = autoclass('android.os.Environment')

#Portrait orientation
AndroidPythonActivity.mActivity.setRequestedOrientation(AndroidActivityInfo.SCREEN_ORIENTATION_PORTRAIT)

def send_to_downloads(filename):
    ss = SharedStorage()
    path = ss.copy_to_shared(filename, collection = Environment.DIRECTORY_DOWNLOADS)
    return path