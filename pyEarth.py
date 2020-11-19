import pyproj
import numpy as np
import shapefile
import shapely.geometry
import sys
import math
from math import cos, pi, sin
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (QAction, QApplication, QFileDialog, QGridLayout, 
                                    QMainWindow, QWidget, QOpenGLWidget)
    
class View(QOpenGLWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        for coord in ('x', 'y', 'z', 'cx', 'cy', 'cz', 'rx', 'ry', 'rz'):
            setattr(self, coord, 50 if coord == 'z' else 0)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)

    def initializeGL(self):
        glMatrixMode(GL_PROJECTION)
        self.create_polygons()
        glFrustum(-1, 1, -1, 1, 5, 1000)

    def paintGL(self):
        glColor(0, 0, 255)
        glEnable(GL_DEPTH_TEST)
        glBegin(GL_POLYGON)
        for vertex in range(0, 100):
            angle, radius = float(vertex)*2.0*pi/100, 6.370997
            glVertex3f(cos(angle)*radius, sin(angle)*radius, 0.0)
        glEnd()
        if hasattr(self, 'polygons'):
            glPushMatrix()
            glRotated(self.rx/16, 1, 0, 0)
            glRotated(self.ry/16, 0, 1, 0)
            glRotated(self.rz/16, 0, 0, 1)
            glCallList(self.polygons)
            glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(self.x, self.y, self.z, self.cx, self.cy, self.cz, 0, 1, 0)
        self.update()
        
    def mousePressEvent(self, event):
        self.last_pos = event.pos()
        
    def wheelEvent(self, event):
        self.z += -2 if event.angleDelta().y() > 0 else 2

    def mouseMoveEvent(self, event):
        dx, dy = event.x() - self.last_pos.x(), event.y() - self.last_pos.y()
        if event.buttons() == Qt.LeftButton:
            self.rx, self.ry = self.rx + 8*dy, self.ry + 8*dx
        elif event.buttons() == Qt.RightButton:
            self.cx, self.cy = self.cx - dx/50, self.cy + dy/50
        self.last_pos = event.pos()
         
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            if self.timer.isActive():
                self.timer.stop()
            else:
                self.timer.start()
            
    def rotate(self):  
        self.rx, self.ry = self.rx + 6, self.ry + 6
            
    def create_polygons(self):
        self.polygons = glGenLists(1)
        glNewList(self.polygons, GL_COMPILE)
        for polygon in self.extract_polygons():
            glLineWidth(2)
            glBegin(GL_LINE_LOOP)
            glColor(0, 0, 0)
            for lon, lat in polygon.exterior.coords:
                glVertex3f(*self.LLH_to_ECEF(lat, lon, 1))
            glEnd()
            glColor(0, 255, 0)
            glBegin(GL_TRIANGLES)
            for vertex in self.polygon_tesselator(polygon):
                glVertex(*vertex)
            glEnd()
        glEndList()
        
    def polygon_tesselator(self, polygon):    
        vertices, tess = [], gluNewTess()
        gluTessCallback(tess, GLU_TESS_EDGE_FLAG_DATA, lambda *args: None)
        gluTessCallback(tess, GLU_TESS_VERTEX, lambda v: vertices.append(v))
        gluTessCallback(tess, GLU_TESS_COMBINE, lambda v, *args: v)
        gluTessCallback(tess, GLU_TESS_END, lambda: None)
        
        gluTessBeginPolygon(tess, 0)
        gluTessBeginContour(tess)
        for lon, lat in polygon.exterior.coords:
            point = self.LLH_to_ECEF(lat, lon, 0)
            gluTessVertex(tess, point, point)
        gluTessEndContour(tess)
        gluTessEndPolygon(tess)
        gluDeleteTess(tess)
        return vertices
        
    def extract_polygons(self):
        if not hasattr(self, 'shapefile'):
            return
        sf = shapefile.Reader(self.shapefile)       
        polygons = sf.shapes() 
        for polygon in polygons:
            polygon = shapely.geometry.shape(polygon)
            yield from [polygon] if polygon.geom_type == 'Polygon' else polygon
        
    def LLH_to_ECEF(self, lat, lon, alt):

        
        rad_lat = lat * (math.pi / 180.0)
        rad_lon = lon * (math.pi / 180.0)

        a = 6378137.0
        finv = 298.257223563
        f = 1 / finv
        e2 = 1 - (1 - f) * (1 - f)
        v = a / math.sqrt(1 - e2 * math.sin(rad_lat) * math.sin(rad_lat))

        x = (v + alt) * math.cos(rad_lat) * math.cos(rad_lon)
        y = (v + alt) * math.cos(rad_lat) * math.sin(rad_lon)
        z = (v * (1 - e2) + alt) * math.sin(rad_lat)
        #ecef, llh = pyproj.Proj(proj='geocent'), pyproj.Proj(proj='latlong')
        #x, y, z = pyproj.transformer.Transformer(llh, ecef, lon, lat, alt, radians=False)
        
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
        self.view.setFocusPolicy(Qt.StrongFocus)
        layout = QGridLayout(central_widget)
        layout.addWidget(self.view, 0, 0)
                
    def import_shapefile(self):
        self.view.shapefile = QFileDialog.getOpenFileName(self, 'Import')[0]
        self.view.create_polygons()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PyEarth()
    window.setWindowTitle('pyEarth: a lightweight 3D visualization of the earth')
    window.setFixedSize(900, 900)
    window.show()
    sys.exit(app.exec_())    
