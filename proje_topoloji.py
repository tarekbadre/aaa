#!/usr/bin/env python

from mininet.log import setLogLevel, info
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi

def topology():
    "Hatadan arindirilmis ve gorsellestirilmis mobilite kodu."
    net = Mininet_wifi()

    info("*** Dugumler Olusturuluyor\n")
    # Ikon hatasi almamak icin standart istasyonlar
    sta1 = net.addStation('sta1', mac='00:00:00:00:00:02', ip='10.0.0.2/8')
    sta2 = net.addStation('sta2', mac='00:00:00:00:00:03', ip='10.0.0.3/8')
   
    # AP ve kapsama alani (range=50)
    ap1 = net.addAccessPoint('ap1', ssid='new-ssid', mode='g', channel='1',
                             position='100,100,0', range='50')
   
    c1 = net.addController('c1')

    info("*** Yapilandirma\n")
    net.configureNodes()

    # Grafigi ac ve kapsama alanlarini goster
    # showConnectivity yerine 'show_stations' ve 'show_isans' parametrelerini plotGraph icinde deneyelim
    net.plotGraph(max_x=200, max_y=200)

    info("*** Surekli Hareket Modeli (Random Walk)\n")
    net.setMobilityModel(time=0, model='RandomWalk',
                         max_x=160, max_y=160, min_x=40, min_y=40)

    info("*** Ag Baslatiliyor\n")
    net.build()
    c1.start()
    ap1.start([c1])

    info("*** CLI Hazir. Noktalar hareket ederken baglantiyi kontrol edebilirsiniz.\n")
    CLI(net)

    info("*** Durduruluyor\n")
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    topology()
