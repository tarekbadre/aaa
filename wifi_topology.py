from mn_wifi.net import Mininet_wifi
from mn_wifi.node import OVSKernelAP
from mn_wifi.cli import CLI
from mn_wifi.link import wmediumd
from mn_wifi.wmediumdConnector import interference
from mininet.log import setLogLevel

def topology():
    net = Mininet_wifi(
        controller=None,
        accessPoint=OVSKernelAP,
        link=wmediumd,
        wmediumd_mode=interference
    )

    print("*** Creating nodes")

    sta1 = net.addStation(
        'sta1',
        position='10,30,0'
    )

    ap1 = net.addAccessPoint(
        'ap1',
        ssid='Network_1',
        channel='1',
        position='20,30,0',
        range=30
    )

    ap2 = net.addAccessPoint(
        'ap2',
        ssid='Network_2',
        channel='6',
        position='70,30,0',
        range=30
    )

    print("*** Configuring wifi nodes")
    net.configureWifiNodes()

    print("*** Plotting graph")
    net.plotGraph(max_x=100, max_y=100)

    print("*** Starting network")
    net.start()

    print("*** Starting mobility")
    net.startMobility(time=0)
    net.mobility(sta1, 'start', time=1, position='10,30,0')
    net.mobility(sta1, 'stop', time=20, position='90,30,0')
    net.stopMobility(time=21)

    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    topology()
