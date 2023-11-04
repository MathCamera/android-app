from kivy.utils import platform

if platform == 'android':
    from androidstorage4kivy import Chooser,SharedStorage
    from kvdroid.tools import change_statusbar_color,toast,navbar_color
    from kvdroid.tools.darkmode import dark_mode

    from android import api_version, mActivity
    from android.permissions import request_permissions, check_permission, Permission
    
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

def change_statusbar_color(bg_color,text_color):
    if platform == "android":
        change_statusbar_color(bg_color,text_color)

def navbar_color(bg_color):
    if platform == "android":
        navbar_color(bg_color)
    
def toast(text):
    if platform == "android":
        toast(text)
    else:
        print(text)

def dark_mode():
    if platform == "android":
        return dark_mode()
    else:
        return False