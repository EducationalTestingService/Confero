### NOTE: THIS DOES NOT WORK BECAUSE OF THE VERSION OF PYQT INSTALLED.
### WHEN I CAN PROVIDE A QT 5 VERSION. IT WILL. THE ONLY ISSUE RIGHT NOW
### IS THAT THE CURRENT QT VERSION SUPPORTS AN OTHER WEBSOCKET STANDARD
### THAN WHAT CONFERO USES.

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import *

# Create an application
app = QApplication([])

# And a window
win = QWidget()
win.setWindowTitle('Confero View')

# And give it a layout
layout = QVBoxLayout()
win.setLayout(layout)

# Create and fill a QWebView
view = QWebView()
view.load(QUrl("http://192.168.1.11:8888"))

# Add the QWebView and button to the layout
layout.addWidget(view)

# Show the window and run the app
win.show()
app.exec_()
