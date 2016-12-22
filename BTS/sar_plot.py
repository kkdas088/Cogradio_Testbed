import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import sqlite3
import os 
import time


class Main_Data(object):

    def __init__(self):
                  
        self.plt = self.setup_backend()
        self.fig = self.plt.figure(figsize=(25,15))
        win = self.fig.canvas.manager.window
        win.after(1, self.animate())
        self.plt.ion()
        self.plt.show()
        while True:
            win.after(1, self.animate())
            
        
    def setup_backend(self,backend='TkAgg'):
        import sys
        del sys.modules['matplotlib.backends']
        del sys.modules['matplotlib.pyplot']
        import matplotlib as mpl
        mpl.use(backend)  # do this before importing pyplot
        import matplotlib.pyplot as plt
        return plt

    
    def animate(self):

        global counter
        if counter == 0:
            isolationlevels= 'IMMEDIATE'
            db_filename ='spec.db'
           
            with sqlite3.connect(db_filename) as conn:
                conn.row_factory = sqlite3.Row
                cursor= conn.cursor()
                cursor.execute("select * from spec")
                datas= cursor.fetchall()
                self.ctfreqb=[]
                self.pwdbmb=[]
                self.ctfreqa=[]
                self.pwdbma=[]
                for row in datas:
                
                    if row['status']=='Busy':
                        self.ctfreqb.append(row['ctfreq']/1e6)
                        self.pwdbmb.append(115+row['pwdbm'])
                        
                    else:
                        self.ctfreqa.append(row['ctfreq']/1e6)
                        self.pwdbma.append(115+row['pwdbm'])   
            self.bar_width =0.2
            self.opacity=0.4
            self.error_config = {'ecolor': '1'}
            self.plt.xlim(870,920)
            self.plt.ylim(-115,-60)
            self.rects1 = self.plt.bar(self.ctfreqb, self.pwdbmb, self.bar_width,bottom=-115,
                     alpha=self.opacity,
                     color='r',
                     
                     label='Busy channel')
            self.rects2 = self.plt.bar(self.ctfreqa, self.pwdbma, self.bar_width,bottom =-115,
                     alpha=self.opacity,
                     color='g',
                     
                     label='Available channel')
                 
            #self.plt.gca().invert_yaxis()  
            self.plt.legend()
            counter +=1
            self.fig.canvas.draw()
            
        else:
            
            db_filename ='spec.db'
           
            with sqlite3.connect(db_filename) as conn:
                conn.row_factory = sqlite3.Row
                cursor= conn.cursor()
                cursor.execute("select * from spec")
                datas= cursor.fetchall()
                del self.pwdbmb[:]
                del self.pwdbma[:]
                del self.ctfreqb[:]
                del self.ctfreqa[:]               
                self.pwdbmb=[]
                self.pwdbma=[]
                self.ctfreqb=[]
                self.ctfreqa=[]
                
                for row in datas:
                
                    if row['status']=='Busy':
                        self.ctfreqb.append(row['ctfreq']/1e6)
                        self.pwdbmb.append(115+row['pwdbm'])
                        
                    else:
                        self.ctfreqa.append(row['ctfreq']/1e6)
                        self.pwdbma.append(115+row['pwdbm'])
                        
            '''print "coming here"           
            [bar.set_height(self.pwdbmb[i]) for i,bar in enumerate(self.rects1)]
            
            [bar.set_height(self.pwdbmb[i]) for i,bar in enumerate(self.rects2)]'''
            self.plt.clf()
            self.plt.xlabel('Frequency in MHz')
            self.plt.ylabel('Power in dBm')
            self.plt.xlim(870,920)
            self.plt.ylim(-115,-60)
            self.rects1 = self.plt.bar(self.ctfreqb, self.pwdbmb, self.bar_width,bottom=-115,
                     alpha=self.opacity,
                     color='r',
                     
                     label='Busy channel')
            self.rects2 = self.plt.bar(self.ctfreqa, self.pwdbma,self.bar_width,bottom =-115,
                     alpha=self.opacity,
                     color='g',
                     
                     label='Available channel')
                     
            #self.plt.gca().invert_yaxis()  
            self.plt.legend()
            
            self.fig.canvas.draw()       
                

            
if __name__ == '__main__': 
    try:
        global counter
        counter=0
        k=  Main_Data()
     
           
    except KeyboardInterrupt:
    
        pass
