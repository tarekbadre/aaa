import os
import time
import subprocess

def get_sta1_pid():
    # sta1'in süreç numarasını otomatik bulur
    try:
        pid = subprocess.check_output(["pgrep", "-f", "mininet:sta1"]).decode().strip()
        return pid
    except:
        return None

def sdn_beyni():
    print("--- SDN KONTROLCÜSÜ BAŞLATILDI ---")
   
    while True:
        pid = get_sta1_pid()
        if not pid:
            print("[!] sta1 bulunamadı. Terminal 1'i başlatın.")
            time.sleep(2)
            continue

        # 'nsenter' kullanarak doğrudan sürecin ağ dünyasına giriyoruz
        komut = f"sudo nsenter -t {pid} -n iw dev sta1-wlan0 link | grep signal | awk '{{print $2}}'"
       
        try:
            rssi_raw = os.popen(komut).read().strip()
            if rssi_raw:
                rssi = int(rssi_raw)
                print(f"[IZLEME] sta1 RSSI: {rssi} dBm")

                if rssi < -70:
                    print(f"!!! KRİTİK ({rssi}): ap1 Gücü Artırılıyor...")
                    os.system("sudo iw dev ap1-wlan1 set txpower fixed 2000")
                else:
                    os.system("sudo iw dev ap1-wlan1 set txpower fixed 1400")
            else:
                print("[?] Sinyal verisi okunamıyor (Trafik yok mu?)")
        except Exception as e:
            print(f"Hata: {e}")

        time.sleep(1)

if __name__ == "__main__":
    sdn_beyni()
