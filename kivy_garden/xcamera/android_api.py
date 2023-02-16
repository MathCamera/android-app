from kivy.logger import Logger

from jnius import JavaException, PythonJavaClass, autoclass, java_method

Camera = autoclass('android.hardware.Camera')
AndroidActivityInfo = autoclass('android.content.pm.ActivityInfo')
AndroidPythonActivity = autoclass('org.kivy.android.PythonActivity')
AndroidPackageManager = autoclass('android.content.pm.PackageManager')
PORTRAIT = AndroidActivityInfo.SCREEN_ORIENTATION_PORTRAIT
LANDSCAPE = AndroidActivityInfo.SCREEN_ORIENTATION_LANDSCAPE

class ShutterCallback(PythonJavaClass):
    __javainterfaces__ = ('android.hardware.Camera$ShutterCallback', )

    @java_method('()V')
    def onShutter(self):
        # apparently, it is enough to have an empty shutter callback to play
        # the standard shutter sound. If you pass None instead of shutter_cb
        # below, the standard sound doesn't play O_o
        pass


class PictureCallback(PythonJavaClass):
    __javainterfaces__ = ('android.hardware.Camera$PictureCallback', )

    def __init__(self, filename, on_success):
        super(PictureCallback, self).__init__()
        self.filename = filename
        self.on_success = on_success

    @java_method('([BLandroid/hardware/Camera;)V')
    def onPictureTaken(self, data, camera):
        s = data.tostring()
        with open(self.filename, 'wb') as f:
            f.write(s)
        Logger.info('xcamera: picture saved to %s', self.filename)
        #Logger.info('enable_flashlight: %s',FlashLight.enable_flashlight)
        camera.startPreview()
        self.on_success(self.filename)


class AutoFocusCallback(PythonJavaClass):
    __javainterfaces__ = ('android.hardware.Camera$AutoFocusCallback', )

    def __init__(self, filename, on_success):
        super(AutoFocusCallback, self).__init__()
        self.filename = filename
        self.on_success = on_success

    @java_method('(ZLandroid/hardware/Camera;)V')
    def onAutoFocus(self, success, camera):
        if success:
            Logger.info('xcamera: autofocus succeeded, taking picture...')
            shutter_cb = ShutterCallback()
            picture_cb = PictureCallback(self.filename, self.on_success)
            camera.takePicture(shutter_cb, None, picture_cb)
        else:
            Logger.info('xcamera: autofocus failed')


def take_picture(camera_widget, filename, on_success):
    # to call the android API, we need access to the underlying
    # android.hardware.Camera instance. However, there is no official way to
    # retrieve it from the camera widget, so we need to dig into internal
    # attributes :-( This works at least on kivy 1.9.1, but it might break any
    # time soon.
    camera = camera_widget._camera._android_camera
    params = camera.getParameters()
    params.setFocusMode("auto")
    camera.setParameters(params)
    cb = AutoFocusCallback(filename, on_success)
    Logger.info('xcamera: starting autofocus...')
    try:
        camera.autoFocus(cb)
    except JavaException as e:
        Logger.info('Error when calling autofocus: {}'.format(e))

def check_flashlight_permission():
    pm = AndroidPythonActivity.mActivity.getPackageManager()
    flash_available = pm.hasSystemFeature(AndroidPackageManager.FEATURE_CAMERA_FLASH)
    return flash_available

def toggle_flashlight(camera_widget,state):
    Logger.info('set flashlight')
    if check_flashlight_permission() == True:
        Logger.info('set flashlight permission: True')
        try:
            CameraParameters = autoclass('android.hardware.Camera$Parameters')
            camera = camera_widget._camera._android_camera
            params = camera.getParameters()
            if state == "auto":
                params.setFlashMode(CameraParameters.FLASH_MODE_AUTO)
            if state == "on":
                params.setFlashMode(CameraParameters.FLASH_MODE_ON)
            if state == "off":
                params.setFlashMode(CameraParameters.FLASH_MODE_OFF)
            Logger.info('set flashlight state : %s',state)

            camera.setParameters(params)

        except Exception as e:
            Logger.info('set flashlight error : %s',e)

def set_orientation(value):
    previous = get_orientation()
    AndroidPythonActivity.mActivity.setRequestedOrientation(value)
    return previous

def get_orientation():
    return AndroidPythonActivity.mActivity.getRequestedOrientation()
