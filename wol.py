from microdot import Microdot
from utotp import totp
import network, time, socket, ntptime
from machine import WDT
from _thread import start_new_thread

WIFI_SSID = "xxx"
WIFI_PASSWORD = "xxx"

TARGET_MAC = "xxx"
BROADCAST_IP = "xxx"
WOL_PORT = 9
TOTP_SECRET = "xxx"
wlan = network.WLAN(network.STA_IF)


def connect_wifi():
    wlan.active(True)

    if wlan.isconnected():
        print("wifi ok:", wlan.ifconfig()[0])
        return

    try:
        wlan.disconnect()
    except:
        pass

    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    for _ in range(30):
        if wlan.isconnected():
            print("wifi ok:", wlan.ifconfig()[0])
            return
        time.sleep(0.5)

    print("wifi failed: beep boop reboot")
    machine.reset()

def ensure_wifi():
    if not wlan.isconnected():
        print("wifi lost, reconnect")
        connect_wifi()

def sync_time():
    try:
        ntptime.settime()
        start_time = time.time()
        print("time synced")
    except:
        print("NTP failed")

def daily_reboot():
    #after 24h reboot
    if time.time() - start_time >= 86400:
        machine.reset()

def maintenance_loop():
    last_sync_ms = time.ticks_ms()

    while True:
        ensure_wifi()
        daily_reboot()

        #once per hour
        if time.ticks_diff(time.ticks_ms(), last_sync_ms) > 3600000:
            sync_time()
            last_sync_ms = time.ticks_ms()

        time.sleep(10)


def send_wol_packet():
    mac_bytes = bytes.fromhex(TARGET_MAC.replace(':', ''))
    magic_packet = b'\xff' * 6 + mac_bytes * 16

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(magic_packet, (BROADCAST_IP, WOL_PORT))
    finally:
        sock.close()


connect_wifi()
sync_time()
start_time = time.time()

start_new_thread(maintenance_loop,())


app = Microdot()

@app.route('/<int:in_totp>')
async def index(request, in_totp):
    ensure_wifi()
    if in_totp == int(totp(time.time(), TOTP_SECRET)[0]):
        send_wol_packet()
        return 'awesome, enjoy ur pc'
    return 'sorry but ur auth code stinks, try again?'

app.run(port=80)

