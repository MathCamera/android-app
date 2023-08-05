from kivy.utils import platform
from kivy.clock import mainthread

if platform == 'android':
    from kivy.uix.button import Button
    from kivy.uix.modalview import ModalView
    from kivy.clock import Clock
    from android import api_version, mActivity
    from android.permissions import request_permissions, check_permission, \
        Permission
    
    from jnius import JavaException, PythonJavaClass, autoclass, java_method
    AndroidActivityInfo = autoclass('android.content.pm.ActivityInfo')
    AndroidPythonActivity = autoclass('org.kivy.android.PythonActivity')
    PORTRAIT = AndroidActivityInfo.SCREEN_ORIENTATION_PORTRAIT
else:
    PORTRAIT=None
    
def check_camera_permission():
    if platform == "android":
        permission = Permission.CAMERA
        return check_permission(permission)

def request_camera_permission(callback=None):
    if platform == "android":
        had_permission = check_camera_permission()
        if not had_permission:
            permissions = [Permission.CAMERA]
            request_permissions(permissions, callback)
        return had_permission

def set_orientation(orientation=PORTRAIT):
    if platform == "android":
        AndroidPythonActivity.mActivity.setRequestedOrientation(orientation)