#!/usr/bin/env python
#
# Copyright 2005,2007,2011 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# channel detection time is 2 seconds
# squelch threshold is to be kept at 9db
# Mininum power level to -107dBm for wireless signals
# MAC frame can be of 10 ms or  for gsm standard for 4.516ms
# Receiver Sensitivity  = -174+ 10 log(Bandwidth)+Noise Figure+ Req SNR
  

from gnuradio import gr, eng_notation
from gnuradio import blocks
from gnuradio import audio
from gnuradio import filter
from gnuradio import fft
from gnuradio import uhd
from gnuradio.eng_option import eng_option
from optparse import OptionParser
import sys
import math
import struct
import threading
from datetime import datetime
import logging
import time
import subprocess
import sqlite3
import os 
import inspect

class tune(gr.feval_dd):
    """
    This class allows C++ code to callback into python.
    """
    def __init__(self, sbs):
        
        gr.feval_dd.__init__(self)
        self.sbs = sbs

    def eval(self, ignore):
        """
        This method is called from blocks.bin_statistics_f when it wants
        to change the center frequency.  This method tunes the front
        end to the new center frequency, and returns the new frequency
        as its result.
        """
        
        try:
            # We use this try block so that if something goes wrong
            # from here down, at least we'll have a prayer of knowing
            # what went wrong.  Without this, you get a very
            # mysterious:
            #
            #   terminate called after throwing an instance of
            #   'Swig::DirectorMethodException' Aborted
            #
            # message on stderr.  Not exactly helpful ;)
            #print "bfor call for set freq"
            #print "no. of msg in q are %d"%self.sbs.msgq.count()
            new_freq = self.sbs.set_next_freq()
           
            '''
            # wait until msgq is empty before continuing
            while(self.sbs.msgq.full_p()):
                print "msgq full, holding.."
                time.sleep(.1)'''
              
          
            return new_freq
            
            
        except Exception, e:
            print "tune: Exception: ", e

class parse_msg(object):
    def __init__(self, msg):
        
        #print "collect ct and data"
        self.center_freq = msg.arg1()
        self.vlen = int(msg.arg2())
        assert(msg.length() == self.vlen * gr.sizeof_float)

        # FIXME consider using NumPy array
        t = msg.to_string()
        self.raw_data = t
        self.data = struct.unpack('%df' % (self.vlen,), t)
       
        
        
class sbs_class(gr.hier_block2):

    def __init__(self,link):
        gr.hier_block2.__init__(self, "sense_receive_path",
				gr.io_signature(1, 1, gr.sizeof_gr_complex),
				gr.io_signature(0, 0, 0))
        
       
        self.it=0
        self.channel_bandwidth = 200000
        self.min_center_freq = 0
        self.max_center_freq = 0
        self.link = link
        self.next_freq= 0
        self.freq_step = 0
        self.usrp_rate =900e3
        self.fft_size = 64
        self.lo_offset =0
        self.squelch_threshold =7
        
        
        
        self.s2v = blocks.stream_to_vector(gr.sizeof_gr_complex, self.fft_size)

        mywindow = filter.window.blackmanharris(self.fft_size)
        self.ffter = fft.fft_vcc(self.fft_size, True, mywindow, True)
        power = 0
        for tap in mywindow:
            power += tap*tap

        self.c2mag = blocks.complex_to_mag_squared(self.fft_size)
        td = 0.2
        dd = 0.1
        
        tune_delay  = max(0, int(round(td * self.usrp_rate / self.fft_size)))  # in fft_frames
        dwell_delay = max(1, int(round(dd * self.usrp_rate / self.fft_size))) # in fft_frames

        self.msgq = gr.msg_queue(1)
        self._tune_callback = tune(self)        # hang on to this to keep it from being GC'd
        self.stats = blocks.bin_statistics_f(self.fft_size, self.msgq,
                                        self._tune_callback, tune_delay,
                                        dwell_delay)
        
        self.connect(self, self.s2v, self.ffter, self.c2mag,self.stats) 
        
    
    def set_next_freq(self):
      
        if (self.min_center_freq!=0):
            target_freq = self.next_freq
            self.next_freq = self.next_freq + self.freq_step
            if self.next_freq >= self.max_center_freq:
                self.next_freq = self.min_center_freq
            
            if not self.set_freq(target_freq):
                print "Failed to set frequency to", target_freq
                sys.exit(1)
            
           
            return target_freq
            
        else:
            if self.it==0:
                self.set_freq(self.link._freq)
                self.it =1
                return self.link._freq
            else:
                return self.link._freq
            

    def set_freq(self, target_freq):
        """
        Set the center frequency we're interested in.

        Args:
            target_freq: frequency in Hz
        @rypte: bool
        """
       
        r = self.link.u.set_center_freq(uhd.tune_request(target_freq, rf_freq=(target_freq + self.lo_offset),rf_freq_policy=uhd.tune_request.POLICY_MANUAL))
        if r:
           
           return True
 
        return False 
        
    def nearest_freq(self, freq, channel_bandwidth):
        nrfreq = round(freq / channel_bandwidth, 0) * channel_bandwidth
        return nrfreq
        
        
    def sense_busy(self,ctfreq):
    
        
        try:
            
            print("")
            print"entering to sense_busy"
            td=0.2
            dd=0.1
            
            self.next_freq = ctfreq
            self.min_freq  = ctfreq - 100000
            self.max_freq =  ctfreq + 100000
            self.usrp_rate= 900e3
            self.freq_step = self.nearest_freq((0.75 * self.usrp_rate), self.channel_bandwidth)
            self.min_center_freq = self.min_freq + (self.freq_step/2) 
            steps = math.ceil((self.max_freq - self.min_freq) / self.freq_step)
            self.nsteps = steps
            self.max_center_freq = self.min_center_freq + (self.nsteps * self.freq_step)
            
            self.lo_offset = 0
            
            
            def bin_freq(i_bin, center_freq):
                
                freq = center_freq
                
                return freq
            
            bin_start = int(self.fft_size * ((1 - 0.75) / 2))
            bin_stop = int(self.fft_size - bin_start)
            m = parse_msg(self.msgq.delete_head())
            
            while m.center_freq!=ctfreq:
                 m = parse_msg(self.msgq.delete_head())
            else:
                pass
          
            print "center frequency",m.center_freq
            
            
            
            F = 0
            T = 0
           
            for i_bin in range(bin_start, bin_stop):
                
               
                center_freq = m.center_freq
                freq = bin_freq(i_bin, center_freq)
                #print "freq is %d"%freq
                #print "center frequecny", center_freq
                #noise_floor_db = -174 + 10*math.log10(tb.channel_bandwidth)print
                noise_floor_db = 10*math.log10(min(m.data)/self.usrp_rate)
                #noise_floor_db= -174+10*math.log10(self.channel_bandwidth)+5
                #print "Noise_Floor = ", noise_floor_db
                power_db = 10*math.log10(m.data[i_bin]/self.usrp_rate) - noise_floor_db
                Absolute_Power = 10*math.log10(m.data[i_bin]/self.usrp_rate)
                #print "Absolute_Power",Absolute_Power
                #print"noise floor",noise_floor_dba
                #print "power - noise = ",power_db
                if (power_db > self.squelch_threshold) and (freq >= self.min_freq) and (freq <= self.max_freq):
               
                   
                    T = T+1
                else:
                    F = F+1
            td=0
            dd=0
            print "False = ", F
            print "True = ", T
            self.it=0 
            self.msgq.delete_head()
            self.min_center_freq = 0
            self.link.u.set_center_freq(self.link._freq)     
            
           
            
            
            if F > 9*T:
                print "dont change the frequency"
                return False
            print "change the frequency"
            return True
            
               
            '''if 10*T >F:
                print "change the frequency"
                 
                return True
                
            print "dont change the frequency"
           
            return False'''
            
        except Exception,e:
            print e
            
       
        
 
                

