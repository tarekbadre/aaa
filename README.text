#!/usr/bin/env python

"Node'ların konumlarını ayarlama ve hareket (mobility) modelleri sağlama"

import sys
import time
import threading
import math
import re

from mininet.node import Node
from mininet.log import setLogLevel, info
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi


# ✅ Fix: منع تداخل Node.cmd بين Threads (يشمل Threads المكتبة نفسها)
_GLOBAL_CMD_LOCK = threading.RLock()
_ORIG_NODE_CMD = Node.cmd

def _locked_node_cmd(self, *args, **kwargs):
    with _GLOBAL_CMD_LOCK:
        return _ORIG_NODE_CMD(self, *args, **kwargs)

Node.cmd = _locked_node_cmd


def topology(args):
    "Bir ağ oluşturur."
    net = Mininet_wifi()

    info("*** Node'lar oluşturuluyor\n")

    STA_RANGE = 35

    sta1 = net.addStation(
        'sta1', mac='00:00:00:00:00:02', ip='10.0.0.2/8',
        min_x=10, max_x=30, min_y=50, max_y=70, min_v=5, max_v=10
    )
    sta2 = net.addStation(
        'sta2', mac='00:00:00:00:00:03', ip='10.0.0.3/8',
        min_x=60, max_x=70, min_y=10, max_y=20, min_v=1, max_v=5
    )

    AP_RANGE = 40

    if '-m' in args:
        ap1 = net.addAccessPoint(
            'ap1', wlans=2, ssid='ssid1,ssid2', mode='g',
            channel='1', failMode="standalone",
            position='50,50,0',
            range=AP_RANGE
        )
    else:
        ap1 = net.addAccessPoint(
            'ap1', ssid='new-ssid', mode='g', channel='1',
            failMode="standalone", position='50,50,0',
            range=AP_RANGE
        )

    info("*** Node'lar yapılandırılıyor\n")
    net.configureNodes()

    sta1.setRange(STA_RANGE)
    sta2.setRange(STA_RANGE)

    # ✅ RSSI'nin gerçekçi olması için Mininet-WiFi propagation model seç (opsiyonel ama önerilir)
    # Bu model RSSI değerlerini kendisi üretir.
    try:
        net.setPropagationModel(model="logDistance", exp=3.0)
        info("📐 PropagationModel: logDistance (exp=3.0)\n")
    except Exception as e:
        info(f"⚠️ setPropagationModel uygulanamadı: {e}\n")

    if '-p' not in args:
        net.plotGraph()

    net.setMobilityModel(
        time=0, model='RandomDirection',
        max_x=100, max_y=100, seed=20
    )

    info("*** Ağ başlatılıyor\n")
    net.build()
    ap1.start([])

    # ---- TxPower değişikliğini thread'den main thread'e taşımak için istek kutusu
    tx_lock = threading.Lock()
    tx_request = {"new_power": None}

    # ✅ Lock لمنع تداخل أوامر cmd بين Threads (يحل AssertionError)
    cmd_lock = threading.Lock()

    # ✅ Lock لكل Station (اختياري لكنه أقوى)
    sta_cmd_locks = {}

    # ✅✅✅ GERÇEK RSSI OKUMA
    def get_real_rssi(sta):
        # 0) جهّز lock خاص للمحطة
        if sta.name not in sta_cmd_locks:
            sta_cmd_locks[sta.name] = threading.Lock()

        # 1) Mininet-WiFi'nin güncel tuttuğu RSSI
        try:
            r = getattr(sta.wintfs[0], "rssi", None)

            # ✅ لو disconnected بعض الإصدارات ترجع 0
            assoc = getattr(sta.wintfs[0], "associatedTo", None)
            if (assoc is None) and (r == 0):
                return None

            if r is not None:
                return int(r)
        except Exception:
            pass

        # 2) iw çıktısından okumayı dene (arayüz içinde) + locks
        try:
            iface = sta.wintfs[0].name
            with cmd_lock:
                with sta_cmd_locks[sta.name]:
                    out = sta.cmd(f"iw dev {iface} link 2>/dev/null")

            if "Not connected" in out or "not connected" in out:
                return None

            m = re.search(r"signal:\s*(-?\d+)\s*dBm", out)
            if m:
                return int(m.group(1))
        except Exception:
            pass

        return None

    # ✅✅✅ PING LOSS (10 ping) + Parsing + locks
    def get_ping_loss_percent(src_sta, dst_ip, count=10, timeout=1):
        """
        src_sta: محطة (sta)
        dst_ip: ip الهدف (مثلا sta2)
        يرجع loss% كـ float (0..100)
        """
        try:
            if src_sta.name not in sta_cmd_locks:
                sta_cmd_locks[src_sta.name] = threading.Lock()

            with cmd_lock:
                with sta_cmd_locks[src_sta.name]:
                    out = src_sta.cmd(f"ping -c {count} -W {timeout} {dst_ip} 2>/dev/null")

            m = re.search(r"(\d+(?:\.\d+)?)%\s*packet loss", out)
            if m:
                return float(m.group(1))
        except Exception:
            pass
        return 100.0

    def mbm_from_dbm(dbm_val):
        # mBm = dBm * 100
        try:
            return int(float(dbm_val) * 100)
        except Exception:
            return None

    def format_rssi(rssi_val):
        if rssi_val is None:
            return "N/A"
        return f"{rssi_val} dBm"

    def status_from_rssi(rssi_val):
        if rssi_val is None:
            return "RSSI yok (bağlı değil/menzil dışı)"
        return "OK"

    def request_txpower_increase(ap, step=5, max_txpower=30):
        with tx_lock:
            current = ap.wintfs[0].txpower
            new_power = current + step
            if new_power > max_txpower:
                new_power = max_txpower
            tx_request["new_power"] = new_power

    def apply_txpower_if_requested(ap):
        with tx_lock:
            new_power = tx_request["new_power"]
            tx_request["new_power"] = None

        if new_power is not None:
            ap.setTxPower(new_power, intf=ap.wintfs[0].name)
            info(f"🔧 {ap.name} TxPower güncellendi → {new_power} dBm\n")

    # ✅ تطبيق TxPower بشكل دوري أثناء التشغيل (بدون انتظار خروج CLI)
    def txpower_worker(ap, interval=0.5):
        while True:
            try:
                apply_txpower_if_requested(ap)
            except Exception:
                pass
            time.sleep(interval)

    t_tx = threading.Thread(
        target=txpower_worker,
        args=(ap1,),
        daemon=True
    )
    t_tx.start()

    def monitor_ap_range_and_rssi(ap, stations, interval=0.5):
        ap_range = ap.wintfs[0].range

        RSSI_CRIT = -70
        RSSI_WEAK = -80

        POWER_STEP = 5
        MAX_TXPOWER = 30

        status = {s.name: None for s in stations}
        weak_state = {s.name: False for s in stations}

        while True:
            for s in stations:
                dist = s.get_distance_to(ap)
                inside = (dist <= ap_range)

                if status[s.name] is None:
                    status[s.name] = inside
                else:
                    if inside and not status[s.name]:
                        info(f"✅ {s.name}, {ap.name} kapsama alanına GİRDİ\n")
                        status[s.name] = True
                        weak_state[s.name] = False
                    elif (not inside) and status[s.name]:
                        info(f"📴 {s.name}, {ap.name} kapsama alanından ÇIKTI → SİNYAL KOPTU\n")
                        status[s.name] = False
                        weak_state[s.name] = False

                if not inside:
                    continue

                # ✅ هنا بدل التخمين: نقرأ RSSI الحقيقي
                rssi_val = get_real_rssi(s)
                if rssi_val is None:
                    info(f"❔ {s.name} RSSI okunamadı (mesafe={dist:.2f}m)\n")
                    continue

                if rssi_val <= RSSI_CRIT and not weak_state[s.name]:
                    info(f"⚠️ {s.name} sinyali ZAYIFLADI (RSSI(GERÇEK)={rssi_val} dBm ≤ {RSSI_CRIT}) → TxPower artırma isteği gönderildi\n")
                    weak_state[s.name] = True
                    request_txpower_increase(ap, step=POWER_STEP, max_txpower=MAX_TXPOWER)

                if rssi_val > RSSI_CRIT and weak_state[s.name]:
                    info(f"📶 {s.name} sinyali tekrar GÜÇLÜ/İYİ (RSSI(GERÇEK)={rssi_val} dBm > {RSSI_CRIT})\n")
                    weak_state[s.name] = False

                if rssi_val <= RSSI_WEAK:
                    info(f"🚨 {s.name} sinyali ÇOK ZAYIF (RSSI(GERÇEK)={rssi_val} dBm)\n")

            time.sleep(interval)

    def rssi_measurement(ap, stations, interval=0.5):
        while True:
            for s in stations:
                dist = s.get_distance_to(ap)
                rssi_val = get_real_rssi(s)
                if rssi_val is None:
                    info(f"📡 {s.name} | mesafe={dist:.2f}m | RSSI(GERÇEK)=NA\n")
                else:
                    info(f"📡 {s.name} | mesafe={dist:.2f}m | RSSI(GERÇEK)={rssi_val} dBm\n")
            time.sleep(interval)

    # ✅✅✅ OUTPUT مثل الذي طلبته (IZLEME / OZET / AKSIYON)
    def monitor_like_output(ap, stations, interval=2.0):
        RSSI_CRIT = -70
        POWER_STEP = 5
        MAX_TXPOWER = 30

        ip_map = {}
        for s in stations:
            if s.name == "sta1":
                ip_map[s.name] = "10.0.0.3"
            elif s.name == "sta2":
                ip_map[s.name] = "10.0.0.2"
            else:
                ip_map[s.name] = None

        while True:
            lines = []
            rssi_values = []
            loss_values = []

            try:
                tx_dbm = ap.wintfs[0].txpower
            except Exception:
                tx_dbm = None

            tx_mbm = mbm_from_dbm(tx_dbm) if tx_dbm is not None else None

            for s in stations:
                rssi_val = get_real_rssi(s)

                dst_ip = ip_map.get(s.name)
                if dst_ip:
                    loss = get_ping_loss_percent(s, dst_ip, count=10, timeout=1)
                else:
                    loss = 100.0

                durum = status_from_rssi(rssi_val)

                if rssi_val is not None:
                    rssi_values.append(rssi_val)
                loss_values.append(loss)

                if tx_mbm is not None and rssi_val is not None:
                    lines.append(f"[IZLEME] {s.name}: RSSI={format_rssi(rssi_val)} | Loss={loss:.1f}% | Durum={durum} | TX: {tx_mbm} mBm")
                else:
                    lines.append(f"[IZLEME] {s.name}: RSSI={format_rssi(rssi_val)} | Loss={loss:.1f}% | Durum={durum}")

            if len(rssi_values) > 0:
                worst_rssi = min(rssi_values)
                worst_rssi_str = f"{worst_rssi} dBm"
            else:
                worst_rssi = None
                worst_rssi_str = "N/A"

            worst_loss = max(loss_values) if len(loss_values) > 0 else 100.0

            action = "Stabil (değişiklik yok)"
            if worst_rssi is not None and worst_rssi <= RSSI_CRIT:
                action = "TX artırıldı"
                request_txpower_increase(ap, step=POWER_STEP, max_txpower=MAX_TXPOWER)

            info("---------------------------------------------\n")
            for ln in lines:
                info(ln + "\n")
            info(f"[OZET] Worst RSSI: {worst_rssi_str} | Worst Loss: {worst_loss:.1f}%\n")

            if action == "TX artırıldı":
                try:
                    cur = ap.wintfs[0].txpower
                    newp = cur + POWER_STEP
                    if newp > MAX_TXPOWER:
                        newp = MAX_TXPOWER
                    info(f"-> [AKSIYON] {action}: {mbm_from_dbm(newp)} mBm\n")
                except Exception:
                    info(f"-> [AKSIYON] {action}\n")
            else:
                info(f"-> [AKSIYON] {action}\n")

            time.sleep(interval)

    t1 = threading.Thread(
        target=monitor_ap_range_and_rssi,
        args=(ap1, [sta1, sta2]),
        daemon=True
    )
    t1.start()

    t2 = threading.Thread(
        target=rssi_measurement,
        args=(ap1, [sta1, sta2]),
        daemon=True
    )
    t2.start()

    t3 = threading.Thread(
        target=monitor_like_output,
        args=(ap1, [sta1, sta2]),
        daemon=True
    )
    t3.start()

    info("*** CLI çalıştırılıyor\n")
    CLI(net)

    apply_txpower_if_requested(ap1)

    info("*** Ağ durduruluyor\n")
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    topology(sys.argv)
