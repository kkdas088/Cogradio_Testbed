import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import sqlite3
import os 
import time

class Main_Data(object):

    def __init__(self):
        
       
        self.plt = self.setup_backend()
        self.fig = self.plt.figure(num =1,figsize=(25,15))
        self.win = self.fig.canvas.manager.window
        self.win.after(1, self.animate()) 
        self.plt.ion()
        self.plt.show()
        while True:
            self.win.after(1, self.animate())        
               
        
       
    def setup_backend(self,backend='TkAgg'):
        import sys
        del sys.modules['matplotlib.backends']
        del sys.modules['matplotlib.pyplot']
        import matplotlib as mpl
        mpl.use(backend)  # do this before importing pyplot
        import matplotlib.pyplot as plt
        return plt

    
    def animate(self):
        global counter,freq
        db_filename ='chsel.db'
        db_flname ='spec.db'
        with sqlite3.connect(db_filename) as conn:
            conn.row_factory = sqlite3.Row
            cursor= conn.cursor()
            cursor.execute("select * from chsel")
            datas= cursor.fetchall()
            if counter !=0:
                self.plt.clf()
                del self.pwdbm[:]
                del self.centfreq[:]
            
            self.centfreq=[]
            self.pwdbm =[]
            
            for row in datas:
                
                self.centfreq.append(row['centfreq']/1e6)
                if row['sel'] =='Yes':
                    freq=row['centfreq']
                    print "freq is %d" %freq
                    with sqlite3.connect(db_flname) as conn1:
                        #conn1.row_factory = sqlite3.Row
                        cursr= conn1.cursor()
                        extractpwrchannel="""select pwdbm from spec where ctfreq =?"""
                        cursr.execute(extractpwrchannel,(freq,))
                        
                        for pwr in cursr.fetchmany(1):
                            print "power =%f"%pwr
                            self.pwdbm.append(115+pwr[0])
                
                else:
                    self.pwdbm.append(-115)   
            self.plt.xlabel('Frequency in MHz')
            self.plt.ylabel('Power in dBm')        
            self.bar_width =0.7
            self.opacity=0.4
            self.error_config = {'ecolor': '1'}
            self.plt.ylim(-115,-90)
            self.plt.xlim(840,960)
            #if counter==0:
            self.rects= self.plt.bar(self.centfreq, self.pwdbm, self.bar_width,bottom=-115,
                     alpha=self.opacity,
                     color='g',
                     label='Channel utilised is %f MHz  '%((freq)/1e6))
                     
            '''else:
                
                [bar.set_height(self.pwdbm[i-1]) for i,bar in enumerate(self.rects)]'''
               
            self.plt.legend()
            counter +=1
            self.fig.canvas.draw()
           

if __name__ == '__main__': 
    try:
        global counter,freq
        counter=0
        freq=0
        k=  Main_Data()
     
           
    except KeyboardInterrupt:
    
        pass            
       
