import pandas as pd
import json
import os
import numpy as np

def parse_line(line):
    try:
        return json.loads(line)
    except:
        return {}
def to_local_time_str(ts_val):
    try:
        dt = pd.to_datetime(ts_val)
        if dt.tzinfo is None:
            dt = dt.tz_localize('UTC')
        return dt.tz_convert('America/Sao_Paulo').strftime('%Y-%m-%d %H:%M')
    except:
        return np.nan

def standardize_ruckus(raw_path, output_path):
    print(f"Processando logs brutos da Ruckus de: {raw_path}")
    if not os.path.exists(raw_path):
        print(f"Erro: Arquivo bruto Ruckus não encontrado em {raw_path}")
        return False
        
    df = pd.read_csv(raw_path)
    # Normalizar o JSON na coluna 'Line'
    parsed = pd.json_normalize(df['Line'].apply(parse_line))
    
    telemetria_rows = []
    
    for _, row in parsed.iterrows():
        # Telemetria no Ruckus SmartZone é identificada pela presença de station_mac_verify ou tx_bytes
        is_telemetry = pd.notna(row.get('station_mac_verify')) or pd.notna(row.get('tx_bytes'))
        
        if is_telemetry:
            ts_val = row.get('time', row.get('ts', ''))
            if not ts_val:
                continue
            ts = to_local_time_str(ts_val)
            
            ap_mac = str(row.get('ap_mac', '')).lower().strip()
            client_mac = str(row.get('mac', '')).lower().strip()
            wlan = str(row.get('wlan', ''))
            
            signal = float(row.get('signal_rssi', -100)) if pd.notna(row.get('signal_rssi')) else -100
            if signal == 0 or signal <= -100:
                signal = np.nan
                rssi = np.nan
                noise = np.nan
            else:
                snr = float(row.get('snr', 0)) if pd.notna(row.get('snr')) else 0
                noise = signal - snr
                rssi = signal # RSSI no Ruckus é a potência do sinal em dBm
            
            canal = row.get('channel', np.nan)
            
            # Volume de tráfego (bytes para MB)
            tx_bytes_tot = float(row.get('tx_bytes', 0)) if pd.notna(row.get('tx_bytes')) else 0
            rx_bytes_tot = float(row.get('rx_bytes', 0)) if pd.notna(row.get('rx_bytes')) else 0
            
            volume_tx_mb = tx_bytes_tot / (1024 * 1024)
            volume_rx_mb = rx_bytes_tot / (1024 * 1024)
            volume_total_mb = volume_tx_mb + volume_rx_mb
            
            # Cálculo de uptime para obter Throughput médio
            uptime_str = str(row.get('uptime', '0:0:0:1.00'))
            uptime_sec = 1
            try:
                parts = uptime_str.split('.')[0].split(':')
                if len(parts) == 4:
                    uptime_sec = int(parts[0])*86400 + int(parts[1])*3600 + int(parts[2])*60 + int(parts[3])
                elif len(parts) == 3:
                    uptime_sec = int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
            except:
                pass
            if uptime_sec <= 0:
                uptime_sec = 1
                
            throughput_tx_mbps = (tx_bytes_tot * 8 / uptime_sec) / 1000000
            throughput_rx_mbps = (rx_bytes_tot * 8 / uptime_sec) / 1000000
            throughput_total_mbps = throughput_tx_mbps + throughput_rx_mbps
            
            # Retransmissões (tx_retries / (tx_packets + tx_retries)) * 100
            retries_count = float(row.get('tx_retries', 0)) if pd.notna(row.get('tx_retries')) else 0
            tx_packets = float(row.get('tx_packets', 0)) if pd.notna(row.get('tx_packets')) else 0
            total_attempts = tx_packets + retries_count
            
            if total_attempts > 0:
                retransmissoes_pct = (retries_count / total_attempts) * 100
            else:
                retransmissoes_pct = 0.0
                
            # Extração de Link Speed a partir de 'throughput_rate' (Kbps para Mbps)
            thr_rate = row.get('throughput_rate')
            try:
                thr_rate_val = float(thr_rate)
                if thr_rate_val > 0 and thr_rate_val < 4000000000:
                    link_speed_tx_mbps = thr_rate_val / 1000
                else:
                    link_speed_tx_mbps = np.nan
            except:
                link_speed_tx_mbps = np.nan
            
            link_speed_rx_mbps = np.nan # Ruckus não fornece taxa RX separada nos logs de cliente
            
            # Padrão de rádio e Banda
            band_id = str(row.get('radio_band_id', ''))
            if band_id == '5':
                padrao = '5 GHz'
                banda = '5 GHz'
            elif band_id == '3':
                padrao = '2.4 GHz'
                banda = '2.4 GHz'
            else:
                padrao = band_id
                try:
                    ch = int(canal)
                    banda = '2.4 GHz' if ch <= 14 else '5 GHz'
                except:
                    banda = 'Desconhecida'
                
            telemetria_rows.append({
                'timestamp': ts,
                'AP': ap_mac,
                'cliente (MAC)': client_mac,
                'equipamento': 'Ruckus',
                'rede (wlan)': wlan,
                'RSSI': rssi,
                'signal': signal if signal != -100 else np.nan,
                'noise': noise,
                'canal': canal,
                'banda': banda,
                'throughput_tx_mbps': throughput_tx_mbps,
                'throughput_rx_mbps': throughput_rx_mbps,
                'throughput_total_mbps': throughput_total_mbps,
                'link_speed_tx_mbps': link_speed_tx_mbps,
                'link_speed_rx_mbps': link_speed_rx_mbps,
                'retransmissoes_pct': retransmissoes_pct,
                'volume_tx_mb': volume_tx_mb,
                'volume_rx_mb': volume_rx_mb,
                'volume_total_mb': volume_total_mb,
                'tempo_sessao_seg': uptime_sec,
                'padrão': padrao
            })
            
    df_out = pd.DataFrame(telemetria_rows)
    if not df_out.empty:
        df_out.to_csv(output_path, index=False)
        print(f"Salvo {len(df_out)} registros padronizados do Ruckus em: {output_path}")
        return True
    else:
        print("Aviso: Nenhum registro de telemetria Ruckus encontrado!")
        return False

def standardize_unifi(raw_path, output_path):
    print(f"Processando logs brutos da UniFi de: {raw_path}")
    if not os.path.exists(raw_path):
        print(f"Erro: Arquivo bruto UniFi não encontrado em {raw_path}")
        return False
        
    df = pd.read_csv(raw_path)
    parsed = pd.json_normalize(df['Line'].apply(parse_line))
    
    # Criar dicionário mapeando o MAC do AP para o seu Nome
    ap_map = {}
    if 'tipo' in parsed.columns and 'mac' in parsed.columns and 'name' in parsed.columns:
        ap_df = parsed[parsed['tipo'] == 'ap']
        for _, row in ap_df.iterrows():
            if pd.notna(row['mac']) and pd.notna(row['name']):
                ap_map[str(row['mac']).lower().strip()] = row['name']
                
    telemetria_rows = []
    
    for _, row in parsed.iterrows():
        if row.get('tipo') == 'cliente':
            ts_val = row.get('ts', '')
            if not ts_val:
                continue
            ts = to_local_time_str(ts_val)
            
            ap_mac = str(row.get('ap_mac', '')).lower().strip()
            ap_name = ap_map.get(ap_mac, ap_mac) # Se mapeado, usa o nome do AP
            client_mac = str(row.get('mac', '')).lower().strip()
            
            rssi = float(row.get('rssi', np.nan)) if pd.notna(row.get('rssi')) else np.nan
            signal = float(row.get('signal', np.nan)) if pd.notna(row.get('signal')) else np.nan
            noise = float(row.get('noise', np.nan)) if pd.notna(row.get('noise')) else np.nan
            canal = row.get('channel', np.nan)
            
            # Throughput (calculado a partir de tx_bytes_r/rx_bytes_r em bytes/s)
            tx_bytes_r = float(row.get('tx_bytes_r', 0)) if pd.notna(row.get('tx_bytes_r')) else 0
            rx_bytes_r = float(row.get('rx_bytes_r', 0)) if pd.notna(row.get('rx_bytes_r')) else 0
            
            throughput_tx_mbps = (tx_bytes_r * 8) / 1000000
            throughput_rx_mbps = (rx_bytes_r * 8) / 1000000
            throughput_total_mbps = throughput_tx_mbps + throughput_rx_mbps
            
            # Link Speed (tx_rate/rx_rate em Kbps para Mbps)
            tx_rate_kbps = float(row.get('tx_rate', 0)) if pd.notna(row.get('tx_rate')) else 0
            rx_rate_kbps = float(row.get('rx_rate', 0)) if pd.notna(row.get('rx_rate')) else 0
            link_speed_tx_mbps = tx_rate_kbps / 1000
            link_speed_rx_mbps = rx_rate_kbps / 1000
            
            # Retransmissões (de CCQ: 100 - ccq/10.0)
            ccq = row.get('ccq')
            if pd.notna(ccq):
                try:
                    ccq_val = float(ccq)
                    retransmissoes_pct = max(0.0, 100.0 - (ccq_val / 10.0))
                except:
                    retransmissoes_pct = 0.0
            else:
                retransmissoes_pct = 0.0
                
            # Volume de tráfego estimado: rate (bytes/s) * uptime (s) / (1024 * 1024)
            uptime = float(row.get('uptime', 1)) if pd.notna(row.get('uptime')) else 1
            if uptime <= 0:
                uptime = 1
                
            volume_tx_mb = (tx_bytes_r * uptime) / (1024 * 1024)
            volume_rx_mb = (rx_bytes_r * uptime) / (1024 * 1024)
            volume_total_mb = volume_tx_mb + volume_rx_mb
            
            # Padrão e Banda
            proto = row.get('radio_proto', '')
            padrao = {'ng': '802.11n', 'ac': '802.11ac', 'ax': '802.11ax', 'g': '802.11g'}.get(proto, proto)
            
            try:
                ch = int(canal)
                banda = '2.4 GHz' if ch <= 14 else '5 GHz'
            except:
                banda = 'Desconhecida'
            
            telemetria_rows.append({
                'timestamp': ts,
                'AP': ap_name,
                'cliente (MAC)': client_mac,
                'equipamento': 'UniFi',
                'rede (wlan)': 'N/A', # UniFi telemetry client log does not directly specify wlan name in this list
                'RSSI': rssi,
                'signal': signal,
                'noise': noise,
                'canal': canal,
                'banda': banda,
                'throughput_tx_mbps': throughput_tx_mbps,
                'throughput_rx_mbps': throughput_rx_mbps,
                'throughput_total_mbps': throughput_total_mbps,
                'link_speed_tx_mbps': link_speed_tx_mbps,
                'link_speed_rx_mbps': link_speed_rx_mbps,
                'retransmissoes_pct': retransmissoes_pct,
                'volume_tx_mb': volume_tx_mb,
                'volume_rx_mb': volume_rx_mb,
                'volume_total_mb': volume_total_mb,
                'tempo_sessao_seg': uptime,
                'padrão': padrao
            })
            
    df_out = pd.DataFrame(telemetria_rows)
    if not df_out.empty:
        df_out.to_csv(output_path, index=False)
        print(f"Salvo {len(df_out)} registros padronizados da UniFi em: {output_path}")
        return True
    else:
        print("Aviso: Nenhum registro de telemetria UniFi encontrado!")
        return False

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    ruckus_raw = os.path.join(base_dir, 'ruckus', 'log-ruckus-23-06.csv')
    ruckus_out = os.path.join(base_dir, 'ruckus_standardized.csv')
    standardize_ruckus(ruckus_raw, ruckus_out)
    
    unifi_raw = os.path.join(base_dir, 'unifi', 'log-unifi-23-06.csv')
    unifi_out = os.path.join(base_dir, 'unifi_standardized.csv')
    standardize_unifi(unifi_raw, unifi_out)
