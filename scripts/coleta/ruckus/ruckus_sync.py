import subprocess
import json
from datetime import datetime, UTC

# Configurações
ZD_IP = "IPDAMAQUINA"
COMMUNITY = "COMUNIDADE"

# OID Base oficial da Tabela de Clientes
BASE_OID = ".1.3.6.1.4.1.25053.1.2.2.1.1.3.1.1"

# Mapa definitivo com 100% das colunas descriptografadas
COLUMN_MAP = {
    "1": "station_mac_verify",
    "2": "ap_mac",
    "3": "bssid",
    "4": "wlan",
    "5": "username",
    "6": "radio_band_id",
    "7": "channel",
    "8": "ip",
    "9": "signal_quality",
    "10": "tx_packets",
    "11": "tx_bytes",
    "12": "rx_packets",
    "13": "rx_bytes",
    "14": "tx_retries",
    "15": "uptime",
    "16": "power_save_pkts",
    "17": "throughput_rate",
    "18": "os_type_index",
    "19": "association_time",
    "20": "management_status",
    "21": "snr",
    "22": "radio_stats_22",
    "23": "mcs_index",
    "24": "radio_stats_24",
    "30": "vlan",
    "80": "auth_method",
    "81": "signal_rssi"
}

def main():
    cmd = ["snmpwalk", "-v2c", "-c", COMMUNITY, "-On", "-Oq", ZD_IP, BASE_OID]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=15)
        lines = result.stdout.splitlines()
    except Exception as e:
        print(json.dumps({"error": f"Falha no snmpwalk: {str(e)}", "component": "snmp"}))
        return

    clients = {}
    timestamp = datetime.now(UTC).isoformat()

    for line in lines:
        parts = line.split(" ", 1)
        if len(parts) != 2:
            continue
        
        full_oid = parts[0]
        raw_value = parts[1].strip('"') 
        
        if not full_oid.startswith(BASE_OID + "."):
            continue
            
        suffix = full_oid.replace(BASE_OID + ".", "")
        oid_parts = suffix.split(".")
        
        if len(oid_parts) < 7:
            continue
            
        col = oid_parts[0]
        mac_decimal = oid_parts[-6:]
        
        try:
            mac_hex = ":".join([f"{int(x):02x}" for x in mac_decimal])
        except ValueError:
            continue

        if mac_hex not in clients:
            clients[mac_hex] = {
                "time": timestamp,
                "mac": mac_hex
            }
            
        # Formata strings hexadecimais de MACs (como BSSID e AP MAC) vindas com espaço do SNMP
        if " " in raw_value and len(raw_value.split()) == 6:
            parts_hex = raw_value.split()
            if all(len(x) in (1, 2) for x in parts_hex):
                try:
                    raw_value = ":".join([x.zfill(2) for x in parts_hex]).lower()
                except ValueError:
                    pass

        # Insere o dado com o nome correto mapeado
        if col in COLUMN_MAP:
            field_name = COLUMN_MAP[col]
            clients[mac_hex][field_name] = raw_value

    if not clients:
        print(json.dumps({"time": timestamp, "error": "Nenhum cliente ativo.", "component": "snmp"}))
    else:
        for data in clients.values():
            print(json.dumps(data))

if __name__ == "__main__":
    main()
