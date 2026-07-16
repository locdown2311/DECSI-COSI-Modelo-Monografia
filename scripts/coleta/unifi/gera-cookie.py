import requests
import urllib3

# Desativa avisos de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

base_url = "https://200.239.152.81:8443"
login_url = f"{base_url}/api/login"

payload = {
    "username": "igortcc",
    "password": "Igorcg23.",
    "strict": True
}

session = requests.Session()

try:
    # Realiza o login
    response = session.post(login_url, json=payload, verify=False)
    
    if response.status_code == 200:
        print("Login bem-sucedido!")
        
        # Salva os cookies no formato que o curl entende
        with open("cookies.txt", "w") as f:
            for cookie in session.cookies:
                # Formato: domain, dot, path, secure, expires, name, value
                # Nota: O UniFi costuma usar o nome 'unifises'
                f.write(f"{cookie.domain}\tTRUE\t{cookie.path}\tFALSE\t{cookie.expires}\t{cookie.name}\t{cookie.value}\n")
        
        print("Arquivo cookies.txt gerado com sucesso.")
    else:
        print(f"Erro no login: {response.status_code}")

except Exception as e:
    print(f"Erro: {e}")