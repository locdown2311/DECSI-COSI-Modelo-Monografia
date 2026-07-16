import requests
import urllib3
import json
import time
import os
import sys
import logging
from datetime import datetime, timezone, timedelta

# =============================================================================
# CONFIGURAÇÃO DE CAMINHOS (Essencial para o Cron)
# =============================================================================
# Define o diretório base como a pasta onde este script está salvo
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Arquivos de saída
COOKIE_FILE = os.path.join(BASE_DIR, "cookies.txt")
JSON_FILE = os.path.join(BASE_DIR, "dados_unifi.json")
LOKI_LOG_FILE = os.path.join(BASE_DIR, "loki_unifi.log")
LOG_FILE = os.path.join(BASE_DIR, "coletor_unifi.log")

# =============================================================================
# CONFIGURAÇÃO DO UNIFI
# =============================================================================

BASE_URL = "https://IPMAQUINA:8443"
SITE = "default"
LOGIN_URL = f"{BASE_URL}/api/login"

# Endpoints coletados A CADA CICLO (dados dinâmicos)
ENDPOINTS_PERIODICOS = {
    "clientes_ativos":  f"/api/s/{SITE}/stat/sta",
    "dispositivos_ap":  f"/api/s/{SITE}/stat/device",
    "saude_rede":       f"/api/s/{SITE}/stat/health",
    "sysinfo":          f"/api/s/{SITE}/stat/sysinfo",
}

# Endpoints com parâmetros de tempo
ENDPOINT_SESSOES = f"/api/s/{SITE}/stat/session"
ENDPOINT_EVENTOS = f"/api/s/{SITE}/stat/event"

# Endpoints coletados UMA VEZ ao iniciar (configuração estática)
ENDPOINTS_CONFIG = {
    "config_wlan":        f"/api/s/{SITE}/rest/wlanconf",
    "config_rede":        f"/api/s/{SITE}/rest/networkconf",
    "canais_disponiveis": f"/api/s/{SITE}/stat/current-channel",
    "grupos_usuario":     f"/api/s/{SITE}/rest/usergroup",
}

CREDENTIALS = {
    "username": "USUARIO",
    "password": "SENHA.",
    "strict": True
}

# Fuso horário de Brasília (UTC-3)
FUSO_BRASILIA = timezone(timedelta(hours=-3))

# Desativa avisos de SSL (certificado auto-assinado)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =============================================================================
# LOGGING
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# =============================================================================
# FUNÇÕES DE REDE (LOGIN / COLETA)
# =============================================================================

def fazer_login(session: requests.Session) -> bool:
    try:
        response = session.post(LOGIN_URL, json=CREDENTIALS, verify=False, timeout=60)
        if response.status_code == 200:
            salvar_cookies(session)
            logger.info("Login realizado com sucesso.")
            return True
        else:
            logger.error(f"Falha no login. Status: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Erro no login: {e}")
        return False

def salvar_cookies(session: requests.Session):
    try:
        with open(COOKIE_FILE, "w", encoding="utf-8") as f:
            f.write("# Netscape HTTP Cookie File\n")
            f.write(f"# Gerado em: {agora_formatado()}\n\n")
            for cookie in session.cookies:
                secure = "TRUE" if cookie.secure else "FALSE"
                expires = str(cookie.expires) if cookie.expires else "0"
                f.write(
                    f"{cookie.domain}\tTRUE\t{cookie.path}\t{secure}\t"
                    f"{expires}\t{cookie.name}\t{cookie.value}\n"
                )
    except Exception as e:
        logger.error(f"Erro ao salvar cookies: {e}")

def coletar_endpoint(session: requests.Session, nome: str, path: str, params: dict = None, timeout: int = None) -> dict | None:
    url = f"{BASE_URL}{path}"
    req_timeout = timeout or 30
    try:
        response = session.get(url, verify=False, timeout=req_timeout, params=params)
        if response.status_code == 200:
            dados = response.json()
            logger.info(f"  [{nome}] OK — {len(dados.get('data', []))} registros.")
            return dados
        else:
            logger.warning(f"  [{nome}] Erro HTTP {response.status_code}.")
            return None
    except Exception as e:
        logger.error(f"  [{nome}] Erro inesperado: {e}")
        return None

def coletar_todos_endpoints(session: requests.Session, intervalo_minutos: int) -> dict | None:
    resultado = {}
    for nome, path in ENDPOINTS_PERIODICOS.items():
        dados = coletar_endpoint(session, nome, path)
        if dados is None and nome == "clientes_ativos":
            return None
        resultado[nome] = dados

    agora_ts = int(time.time())
    inicio_ts = agora_ts - (intervalo_minutos * 60)
    
    resultado["sessoes"] = coletar_endpoint(
        session, "sessoes", ENDPOINT_SESSOES,
        params={"type": "all", "start": str(inicio_ts), "end": str(agora_ts)}
    )
    resultado["eventos"] = coletar_endpoint(
        session, "eventos", ENDPOINT_EVENTOS,
        params={"_limit": "50"}, timeout=60
    )
    return resultado

def coletar_config_ambiente(session: requests.Session) -> dict:
    config = {}
    for nome, path in ENDPOINTS_CONFIG.items():
        config[nome] = coletar_endpoint(session, nome, path)
    return config

# =============================================================================
# FUNÇÕES AUXILIARES E PROCESSAMENTO JSON/LOKI
# =============================================================================

def agora_formatado() -> str: return datetime.now(FUSO_BRASILIA).strftime("%Y-%m-%d %H:%M:%S %Z")
def agora_unix() -> int: return int(time.time())

def carregar_json_server(caminho: str) -> dict:
    estrutura_vazia = {"coletas": [], "clientes": [], "dispositivos": [], "saude": [], "sysinfo": [], "sessoes": [], "eventos": [], "config_wlan": [], "config_rede": [], "canais": [], "grupos_usuario": []}
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
                if isinstance(dados, dict) and "coletas" in dados: return dados
        except Exception: pass
    return estrutura_vazia

def proximo_id(colecao: list) -> int: return max(item.get("id", 0) for item in colecao) + 1 if colecao else 1

def salvar_json_server(dados_coletados: dict, intervalo_minutos: int, caminho: str, config_ambiente: dict = None):
    try:
        db = carregar_json_server(caminho)
        ts_unix = agora_unix()
        ts_iso = datetime.now(FUSO_BRASILIA).isoformat()
        ts_legivel = datetime.now(FUSO_BRASILIA).strftime("%Y-%m-%d %H:%M:%S (Brasília, UTC-3)")

        dados_sta = dados_coletados.get("clientes_ativos", {})
        estacoes = dados_sta.get("data", []) if dados_sta else []
        redes, aps = {}, set()
        next_id = proximo_id(db["clientes"])

        for sta in estacoes:
            essid = sta.get("essid", "desconhecido")
            redes[essid] = redes.get(essid, 0) + 1
            if sta.get("ap_mac"): aps.add(sta.get("ap_mac"))
            db["clientes"].append({"id": next_id, "timestamp_unix": ts_unix, "timestamp_iso": ts_iso, "mac": sta.get("mac", ""), "hostname": sta.get("hostname", ""), "ip": sta.get("ip", ""), "essid": essid, "bssid": sta.get("bssid", ""), "ap_mac": sta.get("ap_mac", ""), "channel": sta.get("channel", 0), "signal": sta.get("signal", 0), "rx_bytes": sta.get("rx_bytes", 0), "tx_bytes": sta.get("tx_bytes", 0)})
            next_id += 1

        dados_dev = dados_coletados.get("dispositivos_ap", {})
        dispositivos = dados_dev.get("data", []) if dados_dev else []
        next_id = proximo_id(db["dispositivos"])

        for dev in dispositivos:
            db["dispositivos"].append({"id": next_id, "timestamp_unix": ts_unix, "timestamp_iso": ts_iso, "mac": dev.get("mac", ""), "name": dev.get("name", ""), "ip": dev.get("ip", ""), "state": dev.get("state", 0), "num_sta": dev.get("num_sta", 0), "satisfaction": dev.get("satisfaction", 0)})
            next_id += 1

        if config_ambiente:
            for chave_config, chave_db in [("config_wlan", "config_wlan"), ("config_rede", "config_rede"), ("canais_disponiveis", "canais"), ("grupos_usuario", "grupos_usuario")]:
                items = config_ambiente.get(chave_config, {}).get("data", [])
                next_id_cfg = proximo_id(db[chave_db])
                for item in items:
                    item_flat = {"id": next_id_cfg, "timestamp_unix": ts_unix, "timestamp_iso": ts_iso}
                    for k, v in item.items():
                        if k != "_id": item_flat[k.replace("-", "_")] = v
                    db[chave_db].append(item_flat)
                    next_id_cfg += 1

        db["coletas"].append({"id": proximo_id(db["coletas"]), "timestamp_unix": ts_unix, "timestamp_iso": ts_iso, "timestamp_legivel": ts_legivel, "intervalo_minutos": intervalo_minutos, "total_estacoes": len(estacoes), "total_dispositivos": len(dispositivos), "total_aps_ativos": len(aps), "redes": redes})

        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
        logger.info(f"JSON Server salvo em '{caminho}'.")
    except Exception as e:
        logger.error(f"Erro ao salvar JSON Server: {e}")

def emitir_logs_loki(dados_coletados: dict, loki_url: str, caminho_log: str):
    # Lógica resumida para push HTTP e salvamento no arquivo (igual ao original)
    try:
        ts_iso = datetime.now(FUSO_BRASILIA).isoformat()
        ts_unix = agora_unix()
        linhas_arquivo = []

        # Como simplificação de leitura no Cron, mantendo apenas o log em arquivo do backup.
        # Caso necessite de manter o push completo pro HTTP Loki, basta inserir a lógica do script antigo aqui.
        estacoes = dados_coletados.get("clientes_ativos", {}).get("data", [])
        for sta in estacoes:
            linhas_arquivo.append(json.dumps({"ts": ts_iso, "timestamp_unix": ts_unix, "tipo": "cliente", "mac": sta.get("mac", ""), "hostname": sta.get("hostname", ""), "essid": sta.get("essid", "")}))

        with open(caminho_log, "a", encoding="utf-8") as f:
            for linha in linhas_arquivo:
                f.write(linha + "\n")
        logger.info(f"Loki log salvo localmente: {len(linhas_arquivo)} linhas em '{caminho_log}'.")
    except Exception as e:
        logger.error(f"Erro ao emitir logs Loki: {e}")

# =============================================================================
# EXECUÇÃO PRINCIPAL (CRON)
# =============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Coletor de dados UniFi Controller (Modo Cron)")
    parser.add_argument("--intervalo", type=int, default=5, help="Intervalo analisado em minutos (padrão: 5)")
    parser.add_argument("--loki-url", type=str, default="http://loki:3100", help="URL do Loki")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("COLETOR UNIFI (Cron) - Iniciando execução única")
    logger.info("=" * 60)

    session = requests.Session()
    if not fazer_login(session):
        logger.error("Abortando execução devido a falha no login.")
        sys.exit(1)

    # Coleta configuração a cada rodada (necessário pois o script "nasce e morre" a cada 5 min no cron)
    config_ambiente = coletar_config_ambiente(session)
    dados_brutos = coletar_todos_endpoints(session, args.intervalo)

    if dados_brutos:
        salvar_json_server(dados_brutos, args.intervalo, JSON_FILE, config_ambiente)
        emitir_logs_loki(dados_brutos, loki_url=args.loki_url, caminho_log=LOKI_LOG_FILE)
    else:
        logger.error("Falha ao coletar dados dos endpoints.")

    logger.info("Execução finalizada.")

if __name__ == "__main__":
    main()