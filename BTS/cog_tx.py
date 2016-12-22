#!/usr/bin/env python

from gnuradio import gr, digital
from gnuradio import eng_notation
from gnuradio.eng_option import eng_option
from optparse import OptionParser

# from current dir
from receive_path  import receive_path
from transmit_path import transmit_path
from uhd_interface import uhd_transmitter
from uhd_interface import uhd_receiver
from uhd_interface import uhd_interface
from sbs_class import *
from sbs_ import *
from main_bar import *
from usrp_uhd import *



import os, sys
import random, time, struct
import socket
import threading
import subprocess
import sqlite3
import random
import inspect
import traceback

IFF_TUN		= 0x0001   
IFF_TAP		= 0x0002   
IFF_NO_PI	= 0x1000   
IFF_ONE_QUEUE = 0x2000
IFF_VNET_HDR = 0x4000   
IFF_MULTI_QUEUE =0x0100

def open_tun_interface(tun_device_filename):
    from fcntl import ioctl
    
    mode = IFF_TAP | IFF_NO_PI
    TUNSETIFF = 0x400454ca
    
    
     # Open control device and request interface
    tun = os.open(tun_device_filename, os.O_RDWR)
    ifs = ioctl(tun, TUNSETIFF, struct.pack("16sH", "gr%d", mode))
    
    # Retreive real interface name from control device
    ifname = ifs[:16].strip("\x00")   
    return (tun, ifname)
    
#                     the flow graph


class my_top_block(gr.top_block):

    def __init__(self, mod_class, demod_class,
                 rx_callback, options):

        gr.top_block.__init__(self)

        
        args = mod_class.extract_kwargs_from_options(options)
        symbol_rate = options.bitrate / mod_class(**args).bits_per_symbol()

        self.source = uhd_receiver(options.args, symbol_rate,
                                   options.samples_per_symbol,
                                   options.rx_freq, options.rx_gain,
                                   options.spec, options.antenna,
                                   options.verbose)
        
        self.sink = uhd_transmitter(options.args, symbol_rate,
                                    options.samples_per_symbol,
                                    options.tx_freq, options.tx_gain,
                                    options.spec, options.antenna,
                                    options.verbose)
        
        options.samples_per_symbol = self.source._sps
        
        

        self.txpath = transmit_path(mod_class, options)
        self.rxpath = receive_path(demod_class, rx_callback, options)
        self.sense_rxpath = sbs_class(self.source)
        self.connect(self.txpath, self.sink)
        self.connect(self.source, self.rxpath)
        self.connect(self.source, self.sense_rxpath)

    def send_pkt(self, payload='', eof=False):
        return self.txpath.send_pkt(payload, eof)

    def carrier_sensed(self):
        """
        Return True if the receive path thinks there's carrier
        """
        return self.rxpath.carrier_sensed()

    def set_freq(self, target_freq):
        """
        Set the center frequency we're interested in.
        """

        self.sink.set_freq(target_freq)
        self.source.set_freq(target_freq)
        
        
    def set_freq_source(self, target_freq):
    
        return self.source.set_freq(target_freq)
        
        
    def set_freq_sink(self, target_freq):
    
        
        return self.sink.set_freq(target_freq)
        
        
    def sense_busy(self,target_freq):
    
        return self.sense_rxpath.sense_busy(target_freq)
        
        


#                           Carrier Sense MAC


class cs_mac(object):
    """
    Prototype carrier sense MAC

    Reads packets from the TUN/TAP interface, and sends them to the
    PHY. Receives packets from the PHY via phy_rx_callback, and sends
    them into the TUN/TAP interface.

    Of course, we're not restricted to getting packets via TUN/TAP,
    this is just an example.
    """

    def __init__(self,tun_fd, verbose=False):
        self.tun_fd = tun_fd       
        self.verbose = verbose
        self.tb = None             # top block (access to PHY)
               

    def set_top_block(self, tb):
        self.tb = tb

    def phy_rx_callback(self, ok, payload):
        """
        Invoked by thread associated with PHY to pass received packet up.

        @param ok: bool indicating whether payload CRC was OK
        @param payload: contents of the packet (string)
        """
        global final_freq,e, change_count,ACK_string,pd,k,oldfreq
        
        if self.verbose:
            print "Rx: ok = %r  len(payload) = %4d" % (ok, len(payload))
            
        if ok:
            os.write(self.tun_fd, payload)
            print " writing to os"
            if (len(payload)==30 and pd==payload):
                #e1.set()
                final_freq = int(payload,2)
                '''ACK = 12345678
                ACK_string = bin(ACK)[2:]
                payload = '%s' %  ACK_string
                print "Sent ACK = ", len(payload)
                self.tb.send_pkt(payload)
                time.sleep(0.0012)'''
                ofreq = self.tb.sink._freq
                self.tb.sink._freq = self.tb.set_freq_sink(final_freq)
                if ofreq == self.tb.sink._freq:
                    self.rt_ch(self.tb.sink._freq,oldfreq)
                else:
                    self.rt_ch(self.tb.sink._freq,ofreq)
                change_count += 1
                print "No. of Changes = ", change_count
                e.set()
                print "e is set" 
            else:
                pass   

    def best_freq(self,freq):
        db_filename ='spec.db'
        with sqlite3.connect(db_filename) as conn:
            cursor= conn.cursor()
            extractbestchannel="""select ctfreq from spec where status like 'Av%' and ctfreq not in (?) order by pwdbm asc"""
            cursor.execute(extractbestchannel,(freq,))
            
            for row in cursor.fetchmany(1):
                pass
                
        return row[0]
        
        
        
    def rt_ch(self,freq,oldfreq=0):
        db_filename ='chsel.db'
        isolationlevels= 'IMMEDIATE'
        with sqlite3.connect(db_filename,isolation_level = isolationlevels) as conn1:
            insertchosen ="""update chsel set sel='Yes' where centfreq=?"""
            conn1.execute(insertchosen,(freq,))
            if oldfreq==0:
                pass
                
            else:
                print "break down solved"
                insertchosen ="""update chsel set sel='No' where centfreq=?"""
                conn1.execute(insertchosen,(oldfreq,))
        return
                
        
       
      

     
    def main_loop(self):
        
        """
        Main loop for MAC.
        Only returns if we get an error reading from TUN.

        FIXME: may want to check for EINTR and EAGAIN and reissue read
        """
        min_delay = 0.001             
       
        while 1 :
        
            
            
            global e,t,bsyn,bsynack,oldfreq,pd,counter
            
            if counter ==0:
                self.rt_ch(self.tb.sink._freq)
                counter +=1
                
            #if sense_busy():
            if (self.tb.sense_busy(self.tb.sink._freq)):
                oldfreq=self.tb.sink._freq
                nxtfreq = self.best_freq(self.tb.sink._freq)
                string = bin(nxtfreq)[2:]
                payload = '%s' %  string
                pd=payload
                final_freq = int(payload,2)
                self.tb.send_pkt(payload)
                print "Sent SYN = ", len(payload)
                e.wait(0.8)
                while not e.isSet():
                    self.tb.sink._freq = self.tb.set_freq_sink(final_freq)
                    self.tb.send_pkt(payload)
                    print "Tx:TX len(payload) = %4d newfreq" % (len(payload),)
                    bsynack +=1
                    time.sleep(0.8)
                    if not e.isSet():
                        if (self.tb.sink._freq !=oldfreq):
                            self.tb.sink._freq = self.tb.set_freq_sink(oldfreq)    
                        self.tb.send_pkt(payload)
                        print "Tx:TX len(payload) = %4d oldfreq" % (len(payload),)
                        bsyn +=1
                        time.sleep(1.5)
                    
                        
                       
                print "bsyn= %d and bsynack=%d"%(bsyn,bsynack)
                print "after set"
                payload = os.read(self.tun_fd, 10*1024)
                self.tb.send_pkt(payload)
                if self.verbose:
                    print "Tx:TX len(payload) = %4d" % (len(payload),)
                payload = os.read(self.tun_fd, 10*1024)
                self.tb.send_pkt(payload)
                if self.verbose:
                    print "Tx:TX len(payload) = %4d" % (len(payload),)
                payload = os.read(self.tun_fd, 10*1024)
                self.tb.send_pkt(payload)
                if self.verbose:
                    print "Tx:TX len(payload) = %4d" % (len(payload),)
                payload = os.read(self.tun_fd, 10*1024)
                self.tb.send_pkt(payload)
                if self.verbose:
                    print "Tx:TX len(payload) = %4d" % (len(payload),)
                
                e.clear()  
            else:
            
                print "In os section"
                payload = os.read(self.tun_fd, 10*1024)
                self.tb.send_pkt(payload)
                if self.verbose:
                    print "Tx:TX len(payload) = %4d" % (len(payload),)
                payload = os.read(self.tun_fd, 10*1024)
                self.tb.send_pkt(payload)
                print "send the payload" 
                if self.verbose:
                    print "Tx: len(payload) = %4d" % (len(payload),)
                payload = os.read(self.tun_fd, 10*1024)
                self.tb.send_pkt(payload)
                if self.verbose:
                    print "Tx:TX len(payload) = %4d" % (len(payload),)
                payload = os.read(self.tun_fd, 10*1024)
                self.tb.send_pkt(payload)
                if self.verbose:
                    print "Tx:TX len(payload) = %4d" % (len(payload),)
               
                if not payload:
                    self.tb.send_pkt(eof=True)
                    break
                         
       

def main():
    global e,y, change_count,bsyn,e1,bsynack,oldfreq,pd,counter,k
    change_count = 0
    counter =0
    bsyn=0
    bsynack=0
    payload=0
    k=''
    e = threading.Event()
    e1= threading.Event()
    mods = digital.modulation_utils.type_1_mods()
    print "Select modulation from: %s [default=%%default]" % (', '.join(mods.keys()),)
                           
    demods = digital.modulation_utils.type_1_demods()

    parser = OptionParser (option_class=eng_option, conflict_handler="resolve")
    expert_grp = parser.add_option_group("Expert")
    parser.add_option("-m", "--modulation", type="choice", choices=mods.keys(),
                      default='gmsk',
                      help="Select modulation from: %s [default=%%default]"
                            % (', '.join(mods.keys()),))

    parser.add_option("-s", "--size", type="eng_float", default=1500,
                      help="set packet size [default=%default]")
    parser.add_option("-v","--verbose", action="store_true", default=False)
    expert_grp.add_option("-c", "--carrier-threshold", type="eng_float", default=30,
                          help="set carrier detect threshold (dB) [default=%default]")
    expert_grp.add_option("","--tun-device-filename", default="/dev/net/tun",
                          help="path to tun device file [default=%default]")

    transmit_path.add_options(parser, expert_grp)
    receive_path.add_options(parser, expert_grp)
    uhd_receiver.add_options(parser)
    uhd_transmitter.add_options(parser)

    for mod in mods.values():
        mod.add_options(expert_grp)

    for demod in demods.values():
        demod.add_options(expert_grp)

    (options, args) = parser.parse_args ()
    if len(args) != 0:
        parser.print_help(sys.stderr)
        sys.exit(1)

    
    (tun_fd, tun_ifname) = open_tun_interface(options.tun_device_filename)

    # Attempt to enable realtime scheduling
    r = gr.enable_realtime_scheduling()
    if r == gr.RT_OK:
        realtime = True
        print "real time enabled"
    else:
        realtime = False
        print "Note: failed to enable realtime scheduling"

    # instantiate the MAC
    mac = cs_mac(tun_fd, verbose=True)

    # build the graph (PHY)
    global tb
    tb = my_top_block(mods[options.modulation],
                      demods[options.modulation],
                      mac.phy_rx_callback,
                      options)

    mac.set_top_block(tb)    # give the MAC a handle for the PHY

    if tb.txpath.bitrate() != tb.rxpath.bitrate():
        print "WARNING: Transmit bitrate = %sb/sec, Receive bitrate = %sb/sec" % (
            eng_notation.num_to_str(tb.txpath.bitrate()),
            eng_notation.num_to_str(tb.rxpath.bitrate()))
           
    print "modulation:     %s"   % (options.modulation,)
    print "freq:           %s"      % (eng_notation.num_to_str(options.tx_freq))
    print "bitrate:        %sb/sec" % (eng_notation.num_to_str(tb.txpath.bitrate()),)
    print "samples/symbol: %3d" % (tb.txpath.samples_per_symbol(),)

    tb.rxpath.set_carrier_threshold(options.carrier_threshold)
    print "Carrier sense threshold:", options.carrier_threshold, "dB"
    
    print
    print "Allocated virtual ethernet interface: %s" % (tun_ifname,)
    print "You must now use ifconfig to set its IP address. E.g.,"
    print
    print "  $ sudo ifconfig %s 192.168.200.1" % (tun_ifname,)
    print
    print "Be sure to use a different address in the same subnet for each machine."
    print

    
    tb.start()    # Start executing the flow graph (runs in separate threads)

    mac.main_loop()    # don't expect this to return...
    
    tb.stop()     # but if it does, tell flow graph to stop.
    tb.wait()     # wait for it to finish
                

if __name__ == '__main__':
    try:
        
        main()
    except KeyboardInterrupt:
        pass
