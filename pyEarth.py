import sys
from math import sin, radians
import pyproj, shapefile, shapely.geometry
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
    
class View(QOpenGLWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        for coord in ('x', 'y', 'z', 'cx', 'cy', 'cz', 'rx', 'ry', 'rz'):
            setattr(self, coord, 50 if coord == 'z' else 0)
      
        self.shapefile = 'C:\\Users\\minto\\Desktop\\pyGISS\\shapefiles\\World countries.shp'
    
    # def rotate(self):
        timer = QTimer(self)
        timer.timeout.connect(self.advanceGears)
        timer.start(20)

    def initializeGL(self):
        glMatrixMode(GL_PROJECTION)
        glFrustum(-1.0, 1.0, -1.0, 1.0, 5.0, 60.0)
        self.create_polygons()
        glEnable(GL_NORMALIZE)
        
    def paintGL(self):
        glColor(255, 255, 255, 0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glEnable(GL_DEPTH_TEST)
        self.quad = gluNewQuadric()
        gluQuadricNormals(self.quad, GLU_SMOOTH)
        glColor(0, 0, 255)
        
        self.sphere = gluSphere(self.quad, 6378137/1000000 - 0.025, 100, 100)

        glColor(0, 255, 0)
        glPushMatrix()
        glRotated(self.rx / 16.0, 1.0, 0.0, 0.0)
        glRotated(self.ry / 16.0, 0.0, 1.0, 0.0)
        glRotated(self.rz / 16.0, 0.0, 0.0, 1.0)
        glCallList(self.polygons)
        glPopMatrix()
        
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(self.x, self.y, self.z, self.cx, self.cy, self.cz, 0, 1, 0)
        
    def mousePressEvent(self, event):
        self.last_position = event.pos()
        
    def wheelEvent(self, event):
        self.z += -2 if event.angleDelta().y() > 0 else 2

    def mouseMoveEvent(self, event):
        dx, dy = event.x() - self.last_position.x(), event.y() - self.last_position.y()
        if event.buttons() == Qt.LeftButton:
            self.rx, self.ry = self.rx + 8 * dy, self.ry + 8 * dx
        elif event.buttons() == Qt.RightButton:
            self.cx, self.cy = self.cx - dx/50, self.cy + dy/50
        self.last_position = event.pos()

    def advanceGears(self):
        self.rx += 8
        self.ry += 8
        self.update()    
        
    def create_polygons(self):
        self.polygons = glGenLists(1)
        glNewList(self.polygons, GL_COMPILE)
        
        for polygon in self.draw_polygons():
            glColor(0, 255, 0)
            glLineWidth(2)
            glBegin(GL_LINE_LOOP)
            for (lon, lat) in polygon:
                glVertex3f(*self.pyproj_LLH_to_ECEF(lat, lon, 1))
            glEnd()
        glEndList()
        
    def draw_polygons(self):
        sf = shapefile.Reader(self.shapefile)       
        polygons = sf.shapes() 
        for polygon in polygons:
            polygon = shapely.geometry.shape(polygon)
            if polygon.geom_type == 'Polygon':
                polygon = [polygon]
            for land in polygon:
                land = str(land)[10:-2].replace(', ', ',').replace(' ', ',')
                coords = land.replace('(', '').replace(')', '').split(',')
                yield [coords for coords in zip(coords[0::2], coords[1::2])]
        
    def LLHtoECEF(self, lat, lon, alt):
        # see http://www.mathworks.de/help/toolbox/aeroblks/llatoecefposition.html
        import numpy as np
        rad = np.float64(6378137.0)
        f = np.float64(1.0/298.257223563)
        np.cosLat = np.cos(lat)
        np.sinLat = np.sin(lat)
        FF     = (1.0-f)**2
        C      = 1/np.sqrt(np.cosLat**2 + FF * np.sinLat**2)
        S      = C * FF
    
        x = (rad * C + alt)*np.cosLat * np.cos(lon)
        y = (rad * C + alt)*np.cosLat * np.sin(lon)
        z = (rad * S + alt)*np.sinLat
        return x/1000000, y/1000000, z/1000000
        
    def pyproj_LLH_to_ECEF(self, lat, lon, alt):
        ecef = pyproj.Proj(proj='geocent', ellps='WGS84', datum='WGS84')
        lla = pyproj.Proj(proj='latlong', ellps='WGS84', datum='WGS84')    
        x, y, z = pyproj.transform(lla, ecef, lon, lat, alt, radians=False)
        return x/1000000, y/1000000, z/1000000

class PyEarth(QMainWindow):
    def __init__(self):        
        super().__init__()
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        menu_bar = self.menuBar()
        import_shapefile = QAction('Import shapefile', self)
        import_shapefile.triggered.connect(self.import_shapefile)
        menu_bar.addAction(import_shapefile)
        self.view = View()
        layout = QGridLayout(central_widget)
        layout.addWidget(self.view, 0, 0)
                
    def import_shapefile(self):
        self.view.shapefile = QFileDialog.getOpenFileName(self, 'Import')[0]
        self.view.redraw_map()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PyEarth()
    window.setWindowTitle('pyGISS: a lightweight GIS software')
    window.setFixedSize(900, 900)
    window.show()
    sys.exit(app.exec_())    
