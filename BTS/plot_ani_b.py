import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import sqlite3
import os 
import time
import sys
from PyQt4 import QtGui
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas


class Monitor(FigureCanvas):
     def __init__(self):

        self.fig = Figure()
        
        self.ax = self.fig.add_subplot(111)

        FigureCanvas.__init__(self, self.fig)
        
        self.counter = 1
        
        self.width = 0.2
        
        self.ax.set_xlabel('Frequency in MHz')
        
        self.ax.set_ylabel('Power in dBm')
        
        self.create_db()
        
        self.bars = self.ax.bar(self.ctfreq, self.pwdbm, self.width, color='g')
              
        #self.ax.invert_yaxis()
        
        self.fig.canvas.draw()
        
        self.ax.set_ylim(-120,-10,)
        
        
        
        self.timer = self.startTimer(1000)
        
        
        
     def create_db(self):
        db_filename ='spec.db'
        print "create db"
        with sqlite3.connect(db_filename) as conn:
            conn.row_factory = sqlite3.Row
            cursor= conn.cursor()
            cursor.execute("select * from spec")
            datas= cursor.fetchall()
            self.ctfreq=[]
            self.pwdbm=[]
            for row in datas:
   
                self.ctfreq.append(row['ctfreq']/1e6)
                self.pwdbm.append(row['pwdbm'])             
                    
    
     def update_db(self):
        db_filename ='spec.db'
        print "update db"
        with sqlite3.connect(db_filename) as conn:
            conn.row_factory = sqlite3.Row
            cursor= conn.cursor()
            cursor.execute("select * from spec")
            datas= cursor.fetchall()
            del self.pwdbm[:]             
            self.pwdbmb=[]
       
            for row in datas:
                self.pwdbm.append(row['pwdbm'])
                    
                 
         
     def timerEvent(self, evt):
        # update the height of the bars, one liner is easier
        
        self.update_db()
        
        [bar.set_height(self.pwdbm[i]) for i,bar in enumerate(self.bars)]
        
        # force the redraw of the canvas
        
        
        self.fig.canvas.draw()
        
        # update the data row counter
        self.counter += 1

        
if __name__ == '__main__': 
    try:
        app = QtGui.QApplication(sys.argv)
        w = Monitor()
        w.setWindowTitle("Real Time Spectrum Sensing")
        w.show()
        sys.exit(app.exec_())
           
    except KeyboardInterrupt:
    
        pass
